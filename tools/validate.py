"""Validation des solveurs sur un ensemble de fichiers DIMACS (Question 2.3).

    python tools/validate.py [chemins...] [--solvers dpll1,dpll2] [--timeout 60]
                             [--jobs 4] [--seeds 0] [--csv sortie.csv]

Chaque chemin est un fichier .cnf ou un dossier (parcouru récursivement) ;
par défaut : instances/. Pour chaque instance et chaque solveur :
    - le statut est comparé au statut attendu (instances/expected.csv,
      calculé par tools/oracle.py) ; pour une instance inconnue du CSV,
      on vérifie au moins que tous les solveurs sont d'accord ;
    - pour une réponse SAT, le modèle est vérifié contre toutes les
      clauses (fait par bench/runner.py) ;
    - un dépassement du délai est compté à part (ni juste, ni faux).
Le code de retour vaut 1 si au moins une réponse est fausse.

Quand les fichiers des enseignants seront disponibles :
    python tools/oracle.py instances/enseignants      (si python-sat installé)
    python tools/validate.py instances/enseignants
"""

import argparse
import csv
import glob
import os
import re
import sys

RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, RACINE)
from bench.common import run_all  # noqa: E402


def charger_attendus():
    chemin = os.path.join(RACINE, "instances", "expected.csv")
    if not os.path.exists(chemin):
        return {}
    with open(chemin, encoding="utf-8") as f:
        return {r["path"]: r["status"] for r in csv.DictReader(f)}


def lister(chemins):
    fichiers = []
    for c in chemins:
        if os.path.isdir(c):
            fichiers += sorted(glob.glob(os.path.join(c, "**", "*.cnf"), recursive=True))
        else:
            fichiers.append(c)
    return [os.path.relpath(f, RACINE).replace(os.sep, "/") for f in fichiers]


def famille(chemin):
    """Nom de famille d'une instance : son nom sans le numéro final."""
    nom = os.path.splitext(os.path.basename(chemin))[0]
    nom = re.sub(r"(_s|-|_)?\d+$", "", nom)
    return re.sub(r"\d+$", "", nom) if nom.startswith(("hole", "dubois")) else nom


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("chemins", nargs="*", default=[os.path.join(RACINE, "instances")])
    ap.add_argument("--solvers", default="dpll1,dpll2")
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--seeds", default="0", help="graines, séparées par des virgules")
    ap.add_argument("--csv", help="fichier CSV des résultats détaillés")
    args = ap.parse_args(argv)

    attendus = charger_attendus()
    fichiers = lister(args.chemins)
    solveurs = args.solvers.split(",")
    graines = [int(g) for g in args.seeds.split(",")]
    taches = [(f, s, g) for f in fichiers for s in solveurs for g in graines]
    print(f"{len(fichiers)} instances x {len(solveurs)} solveurs x {len(graines)} graines, "
          f"délai {args.timeout:g} s, {args.jobs} en parallèle", file=sys.stderr)

    resultats = run_all([(s, os.path.join(RACINE, f), g) for (f, s, g) in taches],
                        delai=args.timeout, jobs=args.jobs)

    lignes, faux = [], []
    for (f, s, g), r in zip(taches, resultats):
        attendu = attendus.get(f)
        st = r["status"]
        if st in ("SAT", "UNSAT"):
            ok = (attendu is None or st == attendu) and r.get("model_ok") is not False
            verdict = "ok" if ok else "FAUX"
        else:
            verdict = st
        if verdict in ("FAUX", "ERROR"):
            faux.append((f, s, g, st, attendu, r))
        lignes.append({"instance": f, "famille": famille(f), "solveur": s, "graine": g,
                       "attendu": attendu or "?", "statut": st, "verdict": verdict,
                       "temps": r.get("time"), "modele_ok": r.get("model_ok")})

    # instances sans statut attendu : les solveurs doivent au moins s'accorder
    par_instance = {}
    for l in lignes:
        if l["attendu"] == "?" and l["statut"] in ("SAT", "UNSAT"):
            par_instance.setdefault(l["instance"], set()).add(l["statut"])
    for f, st in par_instance.items():
        if len(st) > 1:
            faux.append((f, "*", "*", st, None, "désaccord entre solveurs"))

    # résumé par famille et solveur
    resume = {}
    for l in lignes:
        cle = (l["famille"], l["solveur"])
        d = resume.setdefault(cle, {"n": 0, "ok": 0, "TIMEOUT": 0, "FAUX": 0, "ERROR": 0,
                                    "temps": 0.0, "attendu": set()})
        d["n"] += 1
        d[l["verdict"]] += 1
        d["attendu"].add(l["attendu"])
        if l["verdict"] == "ok":
            d["temps"] += l["temps"]
    print(f"\n| famille | statut | solveur | instances | justes | délai dépassé | faux | "
          f"temps moyen (s) |")
    print("|---|---|---|---|---|---|---|---|")
    for (fam, s), d in sorted(resume.items()):
        moy = d["temps"] / d["ok"] if d["ok"] else float("nan")
        print(f"| {fam} | {'/'.join(sorted(d['attendu']))} | {s} | {d['n']} | {d['ok']} | "
              f"{d['TIMEOUT']} | {d['FAUX'] + d['ERROR']} | {moy:.3f} |")

    if args.csv:
        os.makedirs(os.path.dirname(os.path.abspath(args.csv)), exist_ok=True)
        with open(args.csv, "w", encoding="utf-8", newline="") as fcsv:
            w = csv.DictWriter(fcsv, fieldnames=list(lignes[0]))
            w.writeheader()
            w.writerows(lignes)

    total = sum(1 for l in lignes if l["verdict"] == "ok")
    print(f"\n{total}/{len(lignes)} justes, "
          f"{sum(1 for l in lignes if l['verdict'] == 'TIMEOUT')} délais dépassés, "
          f"{len(faux)} erreurs", file=sys.stderr)
    for e in faux:
        print("  ERREUR :", e, file=sys.stderr)
    sys.exit(1 if faux else 0)


if __name__ == "__main__":
    main()
