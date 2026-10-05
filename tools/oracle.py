"""Statut attendu des instances, calculé par un solveur de référence.

    python tools/oracle.py [dossier ...]        (défaut : instances/)

Écrit instances/expected.csv : chemin, statut (SAT/UNSAT), nb de variables,
nb de clauses, origine du statut.

Pourquoi un oracle externe ? Pour valider nos solveurs sur des instances
trop grandes pour la force brute, il faut connaître la bonne réponse
indépendamment de notre code. On utilise MiniSat 2.2 via le paquet
python-sat (pip install python-sat), uniquement comme OUTIL DE
DÉVELOPPEMENT : nos solveurs n'en dépendent pas, et le fichier CSV
produit est versionné, de sorte que la validation (tools/validate.py)
fonctionne sans python-sat.

Le statut est de plus confronté aux informations de la source quand elles
existent (SATLIB : « uf » = satisfiable, « uuf » = insatisfiable, mention
« Not satisfiable » / « satisfiable » en commentaire) : toute discordance
arrête le script.
"""

import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from solver.dimacs import read_dimacs  # noqa: E402

RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SORTIE = os.path.join(RACINE, "instances", "expected.csv")


def statut_annonce(chemin):
    """Statut indiqué par la source de l'instance, ou None."""
    nom = os.path.basename(chemin)
    if nom.startswith("uuf"):
        return "UNSAT"
    if nom.startswith("uf"):
        return "SAT"
    with open(chemin, encoding="utf-8", errors="replace") as f:
        entete = "".join(l for l in f if l.startswith("c")).lower()
    if re.search(r"not satisfiable|unsatisfiable|\(unsat\)", entete):
        return "UNSAT"
    if re.search(r"\bsatisfiable\b|yes", entete) and "aim" in nom and "yes" in nom:
        return "SAT"
    if "aim" in nom and "-no-" in nom:
        return "UNSAT"
    return None


def main(dossiers):
    from pysat.solvers import Minisat22

    lignes = []
    for d in dossiers:
        for chemin in sorted(glob.glob(os.path.join(d, "**", "*.cnf"), recursive=True)):
            n, clauses = read_dimacs(chemin)
            with Minisat22(bootstrap_with=[list(c) for c in clauses]) as s:
                sat = s.solve()
                if sat:   # on vérifie même le modèle de l'oracle
                    m = set(s.get_model())
                    assert all(any(l in m for l in c) for c in clauses), chemin
            statut = "SAT" if sat else "UNSAT"
            annonce = statut_annonce(chemin)
            if annonce is not None and annonce != statut:
                sys.exit(f"DISCORDANCE {chemin} : source {annonce}, MiniSat {statut}")
            rel = os.path.relpath(chemin, RACINE).replace(os.sep, "/")
            lignes.append((rel, statut, n, len(clauses),
                           "minisat22" + ("+source" if annonce else "")))

    # fusion avec un CSV existant (on peut relancer sur un seul dossier)
    anciennes = {}
    if os.path.exists(SORTIE):
        with open(SORTIE, encoding="utf-8") as f:
            anciennes = {r[0]: r for r in csv.reader(f)}
        anciennes.pop("path", None)
    for l in lignes:
        anciennes[l[0]] = l
    with open(SORTIE, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(("path", "status", "vars", "clauses", "origin"))
        for k in sorted(anciennes):
            w.writerow(anciennes[k])
    nb = {s: sum(1 for l in lignes if l[1] == s) for s in ("SAT", "UNSAT")}
    print(f"{len(lignes)} instances : {nb['SAT']} SAT, {nb['UNSAT']} UNSAT -> {SORTIE}",
          file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:] or [os.path.join(RACINE, "instances")])
