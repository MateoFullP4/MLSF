"""Tests de la Question 3 (résolution de grilles).  Lancer depuis la racine :

    python tests/test_solve_grid.py

Stratégie :
  1. la grille de l'énoncé donne exactement le fichier de la figure 2 ;
  2. de nombreuses grilles générées sont résolues, et chaque fichier
     solution est revérifié depuis son texte ;
  3. le nombre de solutions trouvé par énumération SAT (clauses de blocage)
     est comparé à une énumération directe sans SAT : avec N = M = K, une
     solution est une permutation lignes -> colonnes, on les teste toutes ;
  4. une grille insoluble est reconnue comme telle ;
  5. le vérificateur détecte un fichier solution falsifié.
"""

import os
import subprocess
import sys
from itertools import permutations

RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, RACINE)
from meowdoku.grid_io import read_grid, parse_grid, format_solution  # noqa: E402
from meowdoku.generate import generate, generate_unique  # noqa: E402
from meowdoku.solve_grid import solve_grid, count_solutions  # noqa: E402
from meowdoku.verify import violations, check_solution_text  # noqa: E402

GRILLE1 = os.path.join(RACINE, "instances", "meowdoku", "grille1.txt")
FIGURE2_FIN = """A 3 2
B 2 5
C 1 3
D 5 6
E 4 4
F 6 1

. . * . . .
. . . . * .
. * . . . .
. . . * . .
. . . . . *
* . . . . .
"""


def solutions_directes(grid):
    """Toutes les solutions d'une grille carrée N = M = K, sans SAT."""
    assert grid.n == grid.m == grid.k
    res = []
    for perm in permutations(range(1, grid.n + 1)):
        pos = {(i, perm[i - 1]) for i in range(1, grid.n + 1)}
        if not violations(grid, pos):
            res.append(pos)
    return res


def test_figure2():
    p = subprocess.run([sys.executable, os.path.join(RACINE, "meowdoku", "solve_grid.py"),
                        GRILLE1], capture_output=True, text=True, check=True)
    with open(GRILLE1, encoding="utf-8") as f:
        entree = f.read()
    assert p.stdout.startswith(entree.rstrip("\n"))      # le fichier d'entrée est recopié
    assert p.stdout.endswith(FIGURE2_FIN)                # puis la solution de la figure 2
    assert check_solution_text(p.stdout) == []


def test_grilles_generees():
    nb = 0
    for (n, m, k) in [(4, 4, 4), (5, 5, 5), (6, 6, 6), (7, 7, 7), (8, 8, 8),
                      (9, 9, 9), (5, 7, 4), (8, 6, 5)]:
        for graine in range(5):
            g, _ = generate(n, m, k, seed=graine)
            chats = solve_grid(g, seed=graine)
            assert chats is not None
            assert check_solution_text(format_solution(g, chats)) == []
            nb += 1
    print(f"    {nb} grilles résolues et vérifiées")


def test_comptage_solutions():
    for n in (4, 5, 6):
        for graine in range(6):
            g, _ = generate(n, seed=graine)
            directes = solutions_directes(g)
            sat = count_solutions(g, limite=len(directes) + 1)
            assert len(sat) == len(directes)
            assert {frozenset(s.values()) for s in sat} == {frozenset(s) for s in directes}


def test_solution_unique():
    for n in (5, 6, 7):
        for graine in range(3):
            g, plantee = generate_unique(n, seed=graine)
            assert solutions_directes(g) == [set(plantee.values())]


def test_grille_insoluble():
    # 4x4, 4 régions, mais la région D (2 cases) touche la région C (2 cases)
    # de telle sorte qu'aucun placement n'existe : vérifié par énumération
    g = parse_grid("GRID 4 4\nZONES A B C D\nA A B B\nA A B B\nA C C B\nA D D B\n")
    assert solutions_directes(g) == []
    assert solve_grid(g) is None


def test_fichier_falsifie():
    g = read_grid(GRILLE1)
    chats = solve_grid(g)
    texte = format_solution(g, chats)
    assert check_solution_text(texte.replace("A 3 2", "A 3 1")) != []  # dico ≠ carte
    faux = texte.replace(". * . . . .", "* . . . . .").replace("A 3 2", "A 3 1")
    assert check_solution_text(faux) != []                             # adjacence avec F


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"[..] {t.__name__}")
        t()
        print(f"[ok] {t.__name__}")
    print(f"\nTous les tests passent ({len(tests)}).")
