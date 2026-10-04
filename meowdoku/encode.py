"""Encodage d'une grille Meowdoku en formule CNF / fichier DIMACS (Question 1).

    python meowdoku/encode.py grille.txt [-o grille.cnf] [--extra]

Variables
---------
Une variable x_{i,j} par case, (i, j) ∈ {1..N} × {1..M}, vraie si et
seulement si un chat est placé sur la case (i, j). Numérotation DIMACS
ligne par ligne :
        x_{i,j}  ->  (i - 1) * M + j          (de 1 à N*M)
Aucune variable auxiliaire : une valuation témoin se lit directement
comme une configuration de chats (c'est ce que demande l'énoncé).

Clauses (une famille par règle du jeu)
--------------------------------------
« au plus un » sur un ensemble de cases S est encodé par l'encodage
binomial (ou « par paires ») : pour toute paire {a, b} ⊆ S, ¬a ∨ ¬b.
    R1  au plus un chat par ligne        : ¬x_{i,j} ∨ ¬x_{i,j'}      (j < j')
    R2  au plus un chat par colonne      : ¬x_{i,j} ∨ ¬x_{i',j}      (i < i')
    R3a au moins un chat par région R    : ∨_{(i,j) ∈ R} x_{i,j}
    R3b au plus un chat par région R     : ¬x_c ∨ ¬x_c'              (c ≠ c' ∈ R)
    R4  pas deux chats 8-adjacents       : ¬x_{i,j} ∨ ¬x_{i',j'}
                                           (|i-i'| ≤ 1, |j-j'| ≤ 1, (i,j) ≠ (i',j'))
Chaque règle est engendrée telle quelle, puis les clauses identiques sont
fusionnées : par exemple une adjacence horizontale (R4) est déjà une
clause de R1, et deux cases d'une même ligne et d'une même région donnent
la même clause dans R1 et R3b. Les compteurs avant/après fusion sont
écrits en commentaire du fichier DIMACS.

Clauses redondantes optionnelles (--extra)
------------------------------------------
    R5  au moins un chat par ligne       si K = N
    R6  au moins un chat par colonne     si K = M
Elles sont des CONSÉQUENCES des règles : R3 impose exactement K chats
(un par région, les régions étant disjointes) et R1 au plus un par ligne ;
si K = N, les N lignes contiennent donc chacune exactement un chat (même
raisonnement pour les colonnes). Elles ne changent pas l'ensemble des
solutions mais peuvent aider DPLL (plus de propagations unitaires) ; leur
effet est mesuré à la Question 5.
"""

import argparse
import os
import sys
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from meowdoku.grid_io import read_grid  # noqa: E402
from solver.dimacs import write_dimacs  # noqa: E402


def var(i, j, m):
    """Numéro DIMACS de x_{i,j} (indices à partir de 1) dans une grille à m colonnes."""
    return (i - 1) * m + j


def cell_of(v, m):
    """Inverse de var : numéro de variable -> case (i, j)."""
    return (v - 1) // m + 1, (v - 1) % m + 1


def _at_most_one(variables):
    """Encodage binomial de « au plus une variable vraie parmi `variables` »."""
    return [frozenset((-a, -b)) for a, b in combinations(variables, 2)]


def encode(grid, extra=False):
    """Encode la grille ; renvoie (nb_vars, clauses, compteurs).

    clauses   : liste de frozenset de littéraux (même représentation que
                solver.dimacs), sans doublons, dans l'ordre de génération ;
    compteurs : dictionnaire règle -> nombre de clauses engendrées par cette
                règle avant fusion des doublons (pour le rapport).
    """
    n, m = grid.n, grid.m
    x = lambda i, j: var(i, j, m)               # noqa: E731
    familles = {}

    familles["R1 ligne<=1"] = [
        c for i in range(1, n + 1)
        for c in _at_most_one([x(i, j) for j in range(1, m + 1)])]

    familles["R2 colonne<=1"] = [
        c for j in range(1, m + 1)
        for c in _at_most_one([x(i, j) for i in range(1, n + 1)])]

    cases = grid.cells_of()
    familles["R3a region>=1"] = [
        frozenset(x(i, j) for (i, j) in cases[z]) for z in grid.zones]
    familles["R3b region<=1"] = [
        c for z in grid.zones
        for c in _at_most_one([x(i, j) for (i, j) in cases[z]])]

    # Chaque paire de cases voisines n'est produite qu'une fois : on ne
    # regarde que les voisins « après » (i, j) dans l'ordre de lecture.
    adj = []
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            for di, dj in ((0, 1), (1, -1), (1, 0), (1, 1)):
                a, b = i + di, j + dj
                if 1 <= a <= n and 1 <= b <= m:
                    adj.append(frozenset((-x(i, j), -x(a, b))))
    familles["R4 adjacence"] = adj

    if extra:
        if grid.k == n:
            familles["R5 ligne>=1"] = [
                frozenset(x(i, j) for j in range(1, m + 1)) for i in range(1, n + 1)]
        if grid.k == m:
            familles["R6 colonne>=1"] = [
                frozenset(x(i, j) for i in range(1, n + 1)) for j in range(1, m + 1)]

    # Fusion des doublons en gardant l'ordre de première apparition
    # (dict conserve l'ordre d'insertion), pour un fichier reproductible.
    vues = {}
    for clauses in familles.values():
        for c in clauses:
            vues.setdefault(c, None)
    compteurs = {nom: len(cl) for nom, cl in familles.items()}
    return n * m, list(vues), compteurs


def decode(model, grid):
    """Valuation -> dictionnaire région -> (i, j).

    model : itérable de littéraux (seuls les positifs comptent).
    Lève ValueError si une région n'a pas exactement un chat (ce qui ne
    peut arriver que si le modèle ne satisfait pas la CNF).
    """
    chats = {}
    for lit in model:
        if 0 < lit <= grid.n * grid.m:
            i, j = cell_of(lit, grid.m)
            z = grid.regions[i - 1][j - 1]
            if z in chats:
                raise ValueError(f"deux chats dans la région {z}")
            chats[z] = (i, j)
    manquantes = [z for z in grid.zones if z not in chats]
    if manquantes:
        raise ValueError(f"régions sans chat : {' '.join(manquantes)}")
    return chats


def dimacs_comments(grid, nb_clauses, compteurs, source=None):
    """Commentaires DIMACS documentant l'encodage (traçabilité)."""
    com = []
    if source:
        com.append(f"Meowdoku : encodage de {source}")
    com += [f"grille {grid.n}x{grid.m}, {grid.k} regions : {' '.join(grid.zones)}",
            f"variable x(i,j) = (i-1)*{grid.m} + j  (chat en ligne i, colonne j)"]
    for nom, nb in compteurs.items():
        com.append(f"  {nom:15s} : {nb} clauses engendrees")
    com.append(f"  total apres fusion des doublons : {nb_clauses} clauses")
    return com


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grille Meowdoku -> fichier DIMACS CNF")
    ap.add_argument("grille")
    ap.add_argument("-o", "--output", help="fichier .cnf (défaut : même nom, extension .cnf)")
    ap.add_argument("--extra", action="store_true",
                    help="ajouter les clauses redondantes R5/R6 (au moins un par ligne/colonne)")
    args = ap.parse_args(argv)

    grid = read_grid(args.grille)
    nb_vars, clauses, compteurs = encode(grid, extra=args.extra)
    sortie = args.output or os.path.splitext(args.grille)[0] + ".cnf"
    write_dimacs(sortie, nb_vars, clauses,
                 dimacs_comments(grid, len(clauses), compteurs, os.path.basename(args.grille)))
    print(f"{sortie} : {nb_vars} variables, {len(clauses)} clauses", file=sys.stderr)


if __name__ == "__main__":
    main()
