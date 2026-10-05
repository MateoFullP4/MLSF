"""Exécute UN solveur sur UNE instance et affiche le résultat en JSON.

    python bench/runner.py SOLVEUR instance.cnf [--seed S]

Ce script est lancé dans un sous-processus par tools/validate.py et par
les scripts de mesure : un sous-processus peut être interrompu proprement
à l'expiration du délai (les solveurs récursifs n'ont pas de point
d'arrêt), et chaque mesure part d'un interpréteur « neuf » (pas d'effet
de cache ou de ramasse-miettes d'une instance à l'autre).

Le temps mesuré est celui de la RÉSOLUTION seule (lecture du fichier
exclue, mesurée à part) :
    time : temps écoulé (time.perf_counter, résolution < 1 µs) ;
    cpu  : temps processeur (time.process_time ; sous Windows sa
           résolution n'est que de 15,6 ms, d'où l'usage principal de time).
Le modèle renvoyé est systématiquement vérifié contre TOUTES les clauses.

Solveurs disponibles : voir SOLVEURS ci-dessous.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from solver.dimacs import read_dimacs  # noqa: E402
from solver import dpll  # noqa: E402


def _dpll(version):
    def resoudre(nb_vars, clauses, seed):
        sat, modele = dpll.solve(nb_vars, clauses, version=version, seed=seed)
        return sat, modele, {}
    return resoudre


SOLVEURS = {
    "dpll1": _dpll(1),          # algorithme 1 (statut seul)
    "dpll2": _dpll(2),          # algorithme 2 (statut + valuation)
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("solveur", choices=sorted(SOLVEURS))
    ap.add_argument("instance")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    nb_vars, clauses = read_dimacs(args.instance)
    t_lecture = time.perf_counter() - t0

    c0, t0 = time.process_time(), time.perf_counter()
    sat, modele, stats = SOLVEURS[args.solveur](nb_vars, clauses, args.seed)
    t, c = time.perf_counter() - t0, time.process_time() - c0

    modele_ok = None
    if sat and modele is not None:
        m = set(modele)
        modele_ok = (len(modele) == nb_vars
                     and all(abs(l) == k for k, l in enumerate(modele, start=1))
                     and all(any(l in m for l in cl) for cl in clauses))
    print(json.dumps({"status": "SAT" if sat else "UNSAT", "time": t, "cpu": c,
                      "parse": t_lecture, "model_ok": modele_ok, "stats": stats}))


if __name__ == "__main__":
    main()
