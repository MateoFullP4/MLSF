"""Tests de la Question 1 (modélisation Meowdoku).  Lancer depuis la racine :

    python tests/test_meowdoku.py

Stratégie de validation de l'encodage :
  1. la solution donnée par l'énoncé (figure 2) satisfait la CNF de la
     grille de la figure 1 ;
  2. équivalence EXHAUSTIVE sur de petites grilles : pour chacune des
     2^(N*M) valuations, la CNF est satisfaite si et seulement si la
     configuration de chats correspondante est valide selon verify.py
     (qui applique les règles du jeu sans logique propositionnelle).
     C'est une preuve, sur ces grilles, que l'encodage est à la fois
     correct (tout modèle est une solution) et complet (toute solution
     est un modèle) ;
  3. le générateur produit des partitions en régions connexes dont la
     solution plantée est valide, pour de nombreuses tailles et graines ;
  4. les fichiers mal formés sont refusés.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from meowdoku.grid_io import (Grid, GridError, parse_grid, read_grid,   # noqa: E402
                              format_grid)
from meowdoku.encode import encode, var, cell_of, decode               # noqa: E402
from meowdoku.verify import violations                                 # noqa: E402
from meowdoku.generate import (generate, grow_regions, place_cats,     # noqa: E402
                               zone_names, GenerationError)

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GRILLE1 = os.path.join(RACINE, "instances", "meowdoku", "grille1.txt")
SOLUTION_ENONCE = {"A": (3, 2), "B": (2, 5), "C": (1, 3),
                   "D": (5, 6), "E": (4, 4), "F": (6, 1)}


def satisfait(clauses, modele):
    m = set(modele)
    return all(any(l in m for l in c) for c in clauses)


def modele_de(positions, grid):
    """Configuration de chats -> valuation complète (liste de littéraux)."""
    vraies = {var(i, j, grid.m) for (i, j) in positions}
    return [v if v in vraies else -v for v in range(1, grid.n * grid.m + 1)]


def test_lecture_figure1():
    g = read_grid(GRILLE1)
    assert (g.n, g.m, g.k) == (6, 6, 6)
    assert g.regions[3][3] == "E" and g.regions[5][0] == "F"
    assert g.cells_of()["E"] == [(4, 4)]
    # relecture de ce qu'on écrit : format_grid et parse_grid sont inverses
    g2 = parse_grid(format_grid(g))
    assert (g2.n, g2.m, g2.zones, g2.regions) == (g.n, g.m, g.zones, g.regions)


def test_numerotation():
    for m in (1, 3, 7):
        for i in range(1, 5):
            for j in range(1, m + 1):
                assert cell_of(var(i, j, m), m) == (i, j)
    assert var(1, 1, 6) == 1 and var(6, 6, 6) == 36


def test_solution_enonce():
    g = read_grid(GRILLE1)
    nb_vars, clauses, _ = encode(g)
    positions = set(SOLUTION_ENONCE.values())
    assert violations(g, positions) == []
    assert satisfait(clauses, modele_de(positions, g))
    assert decode(modele_de(positions, g), g) == SOLUTION_ENONCE
    # déplacer un seul chat d'une case doit casser la CNF
    faux = (positions - {(3, 2)}) | {(3, 1)}
    assert not satisfait(clauses, modele_de(faux, g))


def _grille_aleatoire(n, m, k, rng):
    """Partition aléatoire en k régions connexes, SANS garantie de solution
    (germes quelconques) : on veut aussi tester des grilles insolubles."""
    germes = rng.sample([(i, j) for i in range(1, n + 1) for j in range(1, m + 1)], k)
    idx = grow_regions(n, m, germes, rng)
    noms = zone_names(k)
    return Grid(n, m, noms, [[noms[r] for r in ligne] for ligne in idx], [])


def _equivalence_exhaustive(grid, extra):
    """Compare CNF et règles du jeu sur les 2^(n*m) valuations.

    Chaque clause est codée par deux masques de bits (littéraux positifs,
    littéraux négatifs) ; une valuation est un entier dont le bit v-1 vaut 1
    si x_v est vraie. La clause est satisfaite si l'un de ses littéraux
    positifs est vrai ou l'un de ses négatifs est faux.
    """
    nb, clauses, _ = encode(grid, extra=extra)
    masques = []
    for c in clauses:
        pos = sum(1 << (l - 1) for l in c if l > 0)
        neg = sum(1 << (-l - 1) for l in c if l < 0)
        masques.append((pos, neg))
    tout = (1 << nb) - 1
    nb_solutions = 0
    for a in range(1 << nb):
        cnf = all((a & p) or (~a & tout & q) for p, q in masques)
        positions = {cell_of(v, grid.m) for v in range(1, nb + 1) if a >> (v - 1) & 1}
        jeu = not violations(grid, positions)
        assert cnf == jeu, (format_grid(grid), sorted(positions), cnf, jeu)
        nb_solutions += jeu
    return nb_solutions


def test_equivalence_exhaustive():
    rng = random.Random(7)
    tailles = [(2, 2), (2, 3), (3, 3), (3, 4), (4, 3), (2, 6), (4, 4)]
    total = {True: 0, False: 0}
    for (n, m) in tailles:
        nb_grilles = 3 if n * m == 16 else 12
        for _ in range(nb_grilles):
            k = rng.randint(1, min(n, m))
            g = _grille_aleatoire(n, m, k, rng)
            for extra in (False, True):
                nb_sol = _equivalence_exhaustive(g, extra)
            total[nb_sol > 0] += 1
    print(f"    grilles testées : {total[True]} avec solution, {total[False]} sans")
    assert total[True] > 0 and total[False] > 0     # les deux cas sont couverts


def _connexe(grid, z):
    cases = set(grid.cells_of()[z])
    depart = next(iter(cases))
    vus, pile = {depart}, [depart]
    while pile:
        i, j = pile.pop()
        for c in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
            if c in cases and c not in vus:
                vus.add(c)
                pile.append(c)
    return vus == cases


def test_generateur():
    nb = 0
    for (n, m, k) in [(1, 1, 1), (4, 4, 4), (5, 5, 5), (6, 6, 6), (8, 8, 8),
                      (12, 12, 12), (20, 20, 20), (5, 7, 4), (9, 4, 3), (6, 6, 2)]:
        for graine in range(10):
            g, plantee = generate(n, m, k, seed=graine)
            assert (g.n, g.m, g.k) == (n, m, k)
            cases = g.cells_of()
            assert sum(len(c) for c in cases.values()) == n * m       # partition
            assert all(cases[z] and _connexe(g, z) for z in g.zones)  # non vides, connexes
            assert all(g.regions[i - 1][j - 1] == z for z, (i, j) in plantee.items())
            assert violations(g, set(plantee.values())) == []
            _, clauses, _ = encode(g)
            assert satisfait(clauses, modele_de(set(plantee.values()), g))
            nb += 1
    # reproductibilité : même graine, même grille
    assert generate(10, seed=42)[0].regions == generate(10, seed=42)[0].regions
    print(f"    {nb} grilles générées et vérifiées")


def test_generateur_cas_impossibles():
    for (n, m, k) in [(2, 2, 2), (3, 3, 3), (4, 4, 5)]:
        try:
            place_cats(n, m, k, random.Random(0))
        except GenerationError:
            continue
        raise AssertionError(f"{n}x{m} avec {k} chats aurait dû être refusé")


def test_fichiers_invalides():
    mauvais = [
        "",                                              # vide
        "GRID 2 2\nA B\nA B\n",                          # pas de ZONES
        "GRID 2 2\nZONES A B\nA B\n",                    # ligne manquante
        "GRID 2 2\nZONES A B\nA B\nA C\n",               # région non déclarée
        "GRID 2 2\nZONES A B C\nA B\nA B\n",             # région C vide
        "GRID 2 2\nZONES A A\nA A\nA A\n",               # nom en double
        "GRID 2 2\nZONES A B\nA B B\nA B\n",             # mauvaise largeur
    ]
    for texte in mauvais:
        try:
            parse_grid(texte)
        except GridError:
            continue
        raise AssertionError(f"aurait dû être refusé : {texte!r}")
    # tolérances documentées : commentaires, région « C » en début de
    # ligne (pas un commentaire), lignes sans espaces
    g = parse_grid("c commentaire\nGRID 2 3\nZONES C D\n\nC D D\nCCD\n")
    assert g.regions == [["C", "D", "D"], ["C", "C", "D"]]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"[..] {t.__name__}")
        t()
        print(f"[ok] {t.__name__}")
    print(f"\nTous les tests passent ({len(tests)}).")
