"""Mesures de performance des algorithmes 1 et 2 (Question 2.4).

    python bench/bench_q2.py [phase|taille|graines|structurees|tout] [--timeout 60]

Expériences (résultats CSV dans bench/results/q2_<experience>.csv) :
  phase       3-SAT aléatoire, n = 30 variables, ratio m/n de 2 à 7,
              30 formules par ratio : proportion SAT et temps (transition
              de phase « facile - difficile - facile ») ;
  taille      3-SAT aléatoire au ratio 4,26, n de 10 à 80, 20 formules par
              taille : croissance du temps avec n, SAT et UNSAT séparés,
              algorithmes 1 et 2 ;
  graines     une même instance résolue avec 20 graines : variabilité due
              au choix aléatoire du branchement ;
  structurees tiroirs (holeN), dubois, Meowdoku N = 4..14.
Les instances aléatoires sont générées (graines fixes) dans bench/work/,
qui n'est pas versionné : le script les recrée à l'identique.
"""

import argparse
import csv
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from bench.common import RACINE, run_all  # noqa: E402
from solver.dimacs import write_dimacs  # noqa: E402
from tools.gen_cnf import random_ksat  # noqa: E402
from meowdoku.generate import generate  # noqa: E402
from meowdoku.encode import encode  # noqa: E402

WORK = os.path.join(RACINE, "bench", "work", "q2")
RESULTS = os.path.join(RACINE, "bench", "results")


def instance_aleatoire(n, ratio, i):
    m = round(ratio * n)
    chemin = os.path.join(WORK, f"r3_n{n}_r{ratio:.2f}_{i}.cnf")
    if not os.path.exists(chemin):
        rng = random.Random(f"{n}-{ratio:.2f}-{i}")
        write_dimacs(chemin, n, random_ksat(n, m, 3, rng), [f"3-SAT n={n} m={m} i={i}"])
    return chemin


def instance_meowdoku(n, graine):
    chemin = os.path.join(WORK, f"meow_{n}_s{graine}.cnf")
    if not os.path.exists(chemin):
        g, _ = generate(n, seed=graine)
        nv, cl, _ = encode(g)
        write_dimacs(chemin, nv, cl)
    return chemin


def ecrire(nom, lignes):
    os.makedirs(RESULTS, exist_ok=True)
    chemin = os.path.join(RESULTS, f"q2_{nom}.csv")
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    print(f"-> {chemin}", file=sys.stderr)


def mesurer(taches, meta, delai):
    """taches : (solveur, chemin, graine) ; meta : dictionnaires de colonnes associées."""
    res = run_all(taches, delai=delai)
    lignes = []
    for (s, chemin, g), m, r in zip(taches, meta, res):
        if r.get("model_ok") is False:
            raise SystemExit(f"modèle faux : {s} {chemin}")
        lignes.append({**m, "solveur": s, "graine": g, "statut": r["status"],
                       "temps": r.get("time", "")})
    return lignes


def exp_phase(delai):
    taches, meta = [], []
    for ratio in [2.0, 2.5, 3.0, 3.5, 4.0, 4.26, 4.5, 5.0, 5.5, 6.0, 7.0]:
        for i in range(30):
            taches.append(("dpll2", instance_aleatoire(30, ratio, i), 0))
            meta.append({"n": 30, "ratio": ratio, "i": i})
    ecrire("phase", mesurer(taches, meta, delai))


def exp_taille(delai):
    taches, meta = [], []
    for n in [10, 20, 30, 40, 50, 60, 70, 80]:
        for i in range(20):
            for s in ("dpll1", "dpll2"):
                taches.append((s, instance_aleatoire(n, 4.26, i), 0))
                meta.append({"n": n, "i": i})
    ecrire("taille", mesurer(taches, meta, delai))


def exp_graines(delai):
    inst = {"uf50-01": "instances/satlib/uf50-01.cnf",
            "uuf50-01": "instances/satlib/uuf50-01.cnf",
            "flat30-1": "instances/satlib/flat30-1.cnf",
            "meow10": instance_meowdoku(10, 1)}
    taches, meta = [], []
    for nom, chemin in inst.items():
        for g in range(20):
            taches.append(("dpll2", os.path.join(RACINE, chemin), g))
            meta.append({"instance": nom})
    ecrire("graines", mesurer(taches, meta, delai))


def exp_structurees(delai):
    inst = [(f"hole{k}", f"instances/satlib/hole{k}.cnf") for k in range(6, 11)]
    inst += [(f"dubois{k}", f"instances/satlib/dubois{k}.cnf") for k in (20, 22, 24, 26, 28, 30)]
    inst += [(f"meow{n}_s{g}", instance_meowdoku(n, g)) for n in range(4, 15) for g in (1, 2, 3)]
    taches, meta = [], []
    for nom, chemin in inst:
        for g in (0, 1, 2):
            taches.append(("dpll2", os.path.join(RACINE, chemin), g))
            meta.append({"instance": nom})
    ecrire("structurees", mesurer(taches, meta, delai))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("experience", nargs="?", default="tout",
                    choices=["phase", "taille", "graines", "structurees", "tout"])
    ap.add_argument("--timeout", type=float, default=60)
    args = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    for nom, f in [("phase", exp_phase), ("taille", exp_taille),
                   ("graines", exp_graines), ("structurees", exp_structurees)]:
        if args.experience in (nom, "tout"):
            print(f"== {nom}", file=sys.stderr)
            f(args.timeout)
