"""Vérification directe d'une configuration de chats (Questions 1 et 3).

Ce module ne passe PAS par la logique propositionnelle : il applique les
quatre règles du jeu telles qu'écrites dans l'énoncé. Il sert donc
d'oracle indépendant pour
    - tester l'encodage CNF (Question 1) : une valuation satisfait la CNF
      si et seulement si la configuration associée est valide ici ;
    - contrôler systématiquement chaque solution produite (Question 3).

    python meowdoku/verify.py solution.txt     # vérifie un fichier solution
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from meowdoku.grid_io import parse_solution  # noqa: E402


def violations(grid, positions):
    """Liste des règles violées par l'ensemble de cases `positions`.

    positions : ensemble de couples (i, j), indices à partir de 1.
    Renvoie une liste de messages ; une liste vide signifie « valide ».
    """
    erreurs = []
    positions = set(positions)

    for (i, j) in positions:
        if not (1 <= i <= grid.n and 1 <= j <= grid.m):
            erreurs.append(f"case ({i},{j}) hors de la grille")
    if erreurs:
        return erreurs

    # Règle 1 : au plus un chat par ligne
    for i in range(1, grid.n + 1):
        nb = sum(1 for (a, _) in positions if a == i)
        if nb > 1:
            erreurs.append(f"ligne {i} : {nb} chats")

    # Règle 2 : au plus un chat par colonne
    for j in range(1, grid.m + 1):
        nb = sum(1 for (_, b) in positions if b == j)
        if nb > 1:
            erreurs.append(f"colonne {j} : {nb} chats")

    # Règle 3 : exactement un chat par région
    par_region = {z: 0 for z in grid.zones}
    for (i, j) in positions:
        par_region[grid.regions[i - 1][j - 1]] += 1
    for z, nb in par_region.items():
        if nb != 1:
            erreurs.append(f"région {z} : {nb} chats")

    # Règle 4 : pas deux chats adjacents (8-voisinage)
    for (i, j) in positions:
        for (a, b) in positions:
            if (i, j) < (a, b) and abs(i - a) <= 1 and abs(j - b) <= 1:
                erreurs.append(f"chats adjacents en ({i},{j}) et ({a},{b})")

    return erreurs


def check_solution_text(text):
    """Vérifie un fichier solution complet (format de la figure 2).

    En plus des règles du jeu, on contrôle que le dictionnaire et la carte
    décrivent la même configuration, et que chaque chat annoncé pour une
    région est bien dans cette région.
    """
    grid, chats, carte = parse_solution(text)
    erreurs = []
    if set(chats) != set(grid.zones):
        erreurs.append("toutes les régions n'ont pas de chat dans le dictionnaire")
    if set(chats.values()) != carte:
        erreurs.append("le dictionnaire et la carte ne concordent pas")
    for z, (i, j) in chats.items():
        if 1 <= i <= grid.n and 1 <= j <= grid.m and grid.regions[i - 1][j - 1] != z:
            erreurs.append(f"le chat de {z} en ({i},{j}) est dans la région "
                           f"{grid.regions[i - 1][j - 1]}")
    erreurs += violations(grid, carte)
    return erreurs


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage : python meowdoku/verify.py solution.txt")
    with open(sys.argv[1], encoding="utf-8") as f:
        erreurs = check_solution_text(f.read())
    if erreurs:
        print("solution INVALIDE :")
        for e in erreurs:
            print("  -", e)
        sys.exit(1)
    print("solution valide")
