"""Génération d'instances CNF de test (en attendant les fichiers des enseignants).

    python tools/gen_cnf.py

Produit dans instances/ :
  - des formules 3-SAT aléatoires au ratio clauses/variables ≈ 4,26
    (zone de transition : environ une sur deux est satisfiable, et ce sont
    les instances les plus difficiles pour DPLL) ;
  - des formules des tiroirs (pigeonhole) php_n : n+1 pigeons dans n trous,
    toujours UNSAT, et notoirement difficiles pour DPLL.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from solver.dimacs import write_dimacs  # noqa: E402


def random_ksat(nb_vars, nb_clauses, k=3, rng=random):
    """Clauses de k variables distinctes, chacune de signe aléatoire."""
    clauses = []
    for _ in range(nb_clauses):
        vs = rng.sample(range(1, nb_vars + 1), k)
        clauses.append(frozenset(v if rng.random() < 0.5 else -v for v in vs))
    return clauses


def pigeonhole(n):
    """n+1 pigeons, n trous. Variable p(i, j) : le pigeon i est dans le trou j."""
    def var(i, j):                     # i dans 0..n, j dans 0..n-1
        return i * n + j + 1
    clauses = []
    for i in range(n + 1):             # chaque pigeon est dans au moins un trou
        clauses.append(frozenset(var(i, j) for j in range(n)))
    for j in range(n):                 # deux pigeons ne partagent pas un trou
        for i1 in range(n + 1):
            for i2 in range(i1 + 1, n + 1):
                clauses.append(frozenset((-var(i1, j), -var(i2, j))))
    return (n + 1) * n, clauses


if __name__ == "__main__":
    dossier = os.path.join(os.path.dirname(__file__), "..", "instances")
    rng = random.Random(2026)
    for n in (20, 50, 75):
        m = round(4.26 * n)
        for k in range(1, 4):
            cls = random_ksat(n, m, rng=rng)
            write_dimacs(os.path.join(dossier, f"rand3sat_{n}_{m}_{k}.cnf"), n, cls,
                         [f"3-SAT aleatoire, {n} variables, {m} clauses, graine 2026"])
    for n in (3, 4, 5, 6):
        nv, cls = pigeonhole(n)
        write_dimacs(os.path.join(dossier, f"php_{n}.cnf"), nv, cls,
                     [f"Tiroirs : {n + 1} pigeons, {n} trous (UNSAT)"])
    print("instances générées dans", os.path.abspath(dossier))
