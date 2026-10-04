"""Génération de grilles Meowdoku ayant au moins une solution (Question 1).

    python meowdoku/generate.py N [M K] [--seed S] [-o grille.txt]
    python meowdoku/generate.py N [M K] --count C --dir DOSSIER [--seed S] [--cnf]

Méthode : « solution plantée »
------------------------------
1. On choisit d'abord une configuration de K chats VALIDE (au plus un par
   ligne, au plus un par colonne, pas deux chats 8-adjacents) :
     - K lignes distinctes tirées au hasard (toutes si K = N), triées ;
     - une colonne par ligne choisie par retour arrière (backtracking) en
       ordre aléatoire, avec deux contraintes : colonne pas encore utilisée,
       et écart de colonne ≥ 2 avec le chat de la ligne précédente si elle
       est adjacente (sinon les deux chats se toucheraient en diagonale).
     Deux chats de lignes non consécutives ne peuvent pas être adjacents,
     donc ces contraintes suffisent.
2. Chaque chat devient le « germe » d'une région, puis les régions
   grandissent simultanément par croissance aléatoire (modèle d'Eden) :
   on tire au hasard une case libre voisine (4-voisinage) d'une région et
   on la lui rattache, jusqu'à ce que toutes les cases soient prises.
3. Les régions sont nommées A, B, C, ... dans l'ordre de lecture de leur
   première case (comme dans la figure 1), puis AA, AB, ... au-delà de 26.

Pourquoi la grille a-t-elle une solution ? Chaque région contient
exactement un germe, et les germes vérifient les règles 1, 2 et 4 : la
configuration des germes est donc une solution, par construction.
Propriétés supplémentaires :
    - les régions forment une partition (chaque case est rattachée à
      exactement une région, chaque région contient au moins son germe) ;
    - chaque région est connexe (4-connexité), comme dans le jeu réel.

Le cas général N × M avec K ≤ min(N, M) régions est traité ; le cas
N = M = K est celui du jeu usuel. Pour N = M = K ∈ {2, 3}, aucune
configuration valide n'existe (deux chats de lignes consécutives devraient
être à distance ≥ 2 en colonne) : le générateur le signale.
La grille produite n'a pas forcément une solution UNIQUE (voir l'option
--unique ajoutée à la Question 3).
"""

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from meowdoku.grid_io import Grid, write_grid  # noqa: E402


class GenerationError(Exception):
    pass


def zone_names(k):
    """A, B, ..., Z, AA, AB, ... (comme les colonnes d'un tableur)."""
    noms = []
    for r in range(k):
        nom, q = "", r + 1
        while q:
            q, reste = divmod(q - 1, 26)
            nom = chr(ord("A") + reste) + nom
        noms.append(nom)
    return noms


def _columns_for(lignes, m, rng):
    """Backtracking : une colonne par ligne (lignes triées), ou None."""
    cols = []
    utilisees = set()

    def etendre(r):
        if r == len(lignes):
            return True
        candidates = [j for j in range(1, m + 1) if j not in utilisees]
        rng.shuffle(candidates)
        for j in candidates:
            if r > 0 and lignes[r] - lignes[r - 1] == 1 and abs(j - cols[-1]) < 2:
                continue                         # contact diagonal avec le chat du dessus
            cols.append(j)
            utilisees.add(j)
            if etendre(r + 1):
                return True
            cols.pop()
            utilisees.discard(j)
        return False

    return cols if etendre(0) else None


def place_cats(n, m, k, rng, essais=200):
    """Configuration valide de k chats sur une grille n × m : liste de (i, j)."""
    if not 1 <= k <= min(n, m):
        raise GenerationError(f"K = {k} impossible : il faut 1 ≤ K ≤ min(N, M) = {min(n, m)}")
    for _ in range(essais):
        lignes = sorted(rng.sample(range(1, n + 1), k))
        cols = _columns_for(lignes, m, rng)
        if cols is not None:
            return list(zip(lignes, cols))
        if k == n:                     # toutes les lignes sont imposées : la
            break                      # recherche était exhaustive, inutile de réessayer
    raise GenerationError(f"aucune configuration valide de {k} chats en {n}x{m}")


def grow_regions(n, m, germes, rng):
    """Croissance aléatoire simultanée des régions à partir des germes.

    Renvoie une matrice n × m d'indices de région (0..k-1), le germe r
    étant dans la région r.
    """
    region = [[None] * m for _ in range(n)]

    def voisins(i, j):
        for a, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
            if 1 <= a <= n and 1 <= b <= m:
                yield a, b

    frontiere = []                     # couples (région, case candidate)
    for r, (i, j) in enumerate(germes):
        region[i - 1][j - 1] = r
    for r, (i, j) in enumerate(germes):
        frontiere += [(r, c) for c in voisins(i, j)]

    while frontiere:
        # tirage uniforme dans la frontière (échange avec le dernier puis pop : O(1))
        t = rng.randrange(len(frontiere))
        frontiere[t], frontiere[-1] = frontiere[-1], frontiere[t]
        r, (i, j) = frontiere.pop()
        if region[i - 1][j - 1] is None:
            region[i - 1][j - 1] = r
            frontiere += [(r, c) for c in voisins(i, j) if region[c[0] - 1][c[1] - 1] is None]
    return region


def generate(n, m=None, k=None, rng=None, seed=None):
    """Grille aléatoire ayant au moins une solution.

    Renvoie (grid, solution_plantee) où solution_plantee est un
    dictionnaire région -> (i, j).
    """
    m = n if m is None else m
    k = n if k is None else k
    rng = rng or random.Random(seed)
    germes = place_cats(n, m, k, rng)
    indices = grow_regions(n, m, germes, rng)

    # Renommage dans l'ordre de lecture de la première case de chaque région
    noms = zone_names(k)
    ordre = {}
    for ligne in indices:
        for r in ligne:
            if r not in ordre:
                ordre[r] = noms[len(ordre)]
    regions = [[ordre[r] for r in ligne] for ligne in indices]
    plantee = {ordre[r]: germes[r] for r in range(k)}

    commentaires = [f"grille generee : N={n} M={m} K={k}"
                    + (f" graine={seed}" if seed is not None else "")]
    return Grid(n, m, noms, regions, commentaires), plantee


def main(argv=None):
    ap = argparse.ArgumentParser(description="Générateur de grilles Meowdoku (solution plantée)")
    ap.add_argument("dims", type=int, nargs="+", metavar="N [M K]",
                    help="N seul (N = M = K) ou N M K")
    ap.add_argument("--seed", type=int, default=None, help="graine (reproductibilité)")
    ap.add_argument("-o", "--output", help="fichier de sortie (une seule grille)")
    ap.add_argument("--count", type=int, default=1, help="nombre de grilles à produire")
    ap.add_argument("--dir", default=".", help="dossier de sortie pour --count")
    ap.add_argument("--cnf", action="store_true", help="écrire aussi l'encodage DIMACS")
    args = ap.parse_args(argv)

    if len(args.dims) == 1:
        n = m = k = args.dims[0]
    elif len(args.dims) == 3:
        n, m, k = args.dims
    else:
        ap.error("donner N, ou N M K")

    graine0 = args.seed if args.seed is not None else random.randrange(10 ** 6)
    for t in range(args.count):
        graine = graine0 + t
        try:
            grid, _ = generate(n, m, k, seed=graine)
        except GenerationError as e:
            sys.exit(f"erreur : {e}")
        if args.output and args.count == 1:
            chemin = args.output
        else:
            os.makedirs(args.dir, exist_ok=True)
            chemin = os.path.join(args.dir, f"meow_{n}x{m}_k{k}_s{graine}.txt")
        write_grid(chemin, grid)
        if args.cnf:
            from meowdoku.encode import encode, dimacs_comments
            from solver.dimacs import write_dimacs
            nb_vars, clauses, compteurs = encode(grid)
            write_dimacs(os.path.splitext(chemin)[0] + ".cnf", nb_vars, clauses,
                         dimacs_comments(grid, len(clauses), compteurs, os.path.basename(chemin)))
        print(chemin, file=sys.stderr)


if __name__ == "__main__":
    main()
