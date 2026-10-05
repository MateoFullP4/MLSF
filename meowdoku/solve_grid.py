"""Résolution d'une grille Meowdoku par le solveur SAT (Question 3).

    python meowdoku/solve_grid.py grille.txt [-o solution.txt] [--solver dpll]
                                  [--cnf grille.cnf] [--extra] [--seed S]

Chaîne de traitement (la recherche est entièrement déléguée au solveur SAT) :
    1. lecture et contrôle de la grille            (grid_io.read_grid)
    2. encodage CNF et écriture d'un fichier DIMACS (encode.encode)
    3. relecture du fichier DIMACS et résolution    (solver.dimacs + solveur)
    4. décodage du modèle : région -> (i, j)        (encode.decode)
    5. vérification de la solution par les règles du jeu, puis du fichier
       produit lui-même, relu depuis le texte       (verify)
    6. écriture du fichier résultat (figure 2) : copie du fichier d'entrée,
       dictionnaire région -> position, carte en « * ».

Le passage par un vrai fichier DIMACS (étape 2-3) n'est pas indispensable
techniquement (on pourrait passer les clauses en mémoire), mais c'est ce
que demande l'énoncé, et cela teste au passage l'écriture et la relecture
du format. Sans --cnf, le fichier est temporaire.

Si la formule est insatisfiable (grille licite mais sans solution, ce qui
ne peut pas arriver pour une grille du générateur), le programme le dit
et renvoie le code 2.
"""

import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from meowdoku.grid_io import parse_grid, format_solution  # noqa: E402
from meowdoku.encode import encode, decode, dimacs_comments  # noqa: E402
from meowdoku.verify import violations, check_solution_text  # noqa: E402
from solver.dimacs import read_dimacs, write_dimacs  # noqa: E402
from solver import dpll  # noqa: E402
from solver.dpllh import solve_h  # noqa: E402
from solver.heuristics import NOMS as HEURISTIQUES  # noqa: E402


def _dpll2(nb_vars, clauses, seed):
    return dpll.solve(nb_vars, clauses, version=2, seed=seed)


def _dpllh(nom):
    return lambda nb_vars, clauses, seed: solve_h(nb_vars, clauses, nom, seed)[:2]


# Solveurs disponibles : nom -> fonction (nb_vars, clauses, graine) -> (sat, modèle)
# « dpll » : algorithme 2 ; H0..H7d : DPLL_H avec l'heuristique correspondante.
SOLVEURS = {"dpll": _dpll2}
SOLVEURS.update({h: _dpllh(h) for h in HEURISTIQUES})


class SolveError(Exception):
    pass


def solve_cnf(nb_vars, clauses, solveur="dpll", seed=0):
    sat, modele = SOLVEURS[solveur](nb_vars, clauses, seed)
    if sat and not dpll.check_model(clauses, modele):        # garde-fou
        raise SolveError("le solveur a renvoyé un modèle qui ne satisfait pas la CNF")
    return sat, modele


def solve_grid(grid, solveur="dpll", seed=0, extra=False, chemin_cnf=None, source=None):
    """Résout la grille ; renvoie le dictionnaire région -> (i, j), ou None si UNSAT."""
    nb_vars, clauses, compteurs = encode(grid, extra=extra)
    temporaire = chemin_cnf is None
    if temporaire:
        fd, chemin_cnf = tempfile.mkstemp(suffix=".cnf")
        os.close(fd)
    try:
        write_dimacs(chemin_cnf, nb_vars, clauses,
                     dimacs_comments(grid, len(clauses), compteurs, source))
        nb_vars, clauses = read_dimacs(chemin_cnf)
    finally:
        if temporaire:
            os.remove(chemin_cnf)

    sat, modele = solve_cnf(nb_vars, clauses, solveur, seed)
    if not sat:
        return None
    chats = decode(modele, grid)
    erreurs = violations(grid, set(chats.values()))
    if erreurs:                                               # ne doit jamais arriver
        raise SolveError("solution invalide : " + "; ".join(erreurs))
    return chats


def count_solutions(grid, limite=2, solveur="dpll", seed=0):
    """Énumère jusqu'à `limite` solutions distinctes de la grille.

    Après chaque solution S trouvée, on ajoute la clause de blocage
    ∨_{(i,j) ∈ S} ¬x_{i,j}, qui interdit exactement la configuration S
    (toute autre configuration a au moins une case de S sans chat).
    Renvoie la liste des solutions (dictionnaires région -> case).
    """
    from meowdoku.encode import var
    nb_vars, clauses, _ = encode(grid)
    solutions = []
    while len(solutions) < limite:
        sat, modele = solve_cnf(nb_vars, clauses, solveur, seed)
        if not sat:
            break
        chats = decode(modele, grid)
        solutions.append(chats)
        clauses = clauses + [frozenset(-var(i, j, grid.m) for (i, j) in chats.values())]
    return solutions


def main(argv=None):
    ap = argparse.ArgumentParser(description="Résout une grille Meowdoku avec le solveur SAT")
    ap.add_argument("grille")
    ap.add_argument("-o", "--output", help="fichier solution (défaut : sortie standard)")
    ap.add_argument("--solver", default="dpll", choices=sorted(SOLVEURS))
    ap.add_argument("--cnf", help="conserver le fichier DIMACS intermédiaire à cet endroit")
    ap.add_argument("--extra", action="store_true", help="clauses redondantes R5/R6")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    with open(args.grille, encoding="utf-8") as f:
        texte = f.read()
    grid = parse_grid(texte)
    chats = solve_grid(grid, args.solver, args.seed, args.extra, args.cnf,
                       os.path.basename(args.grille))
    if chats is None:
        print("c aucune solution : la formule est insatisfiable", file=sys.stderr)
        sys.exit(2)

    sortie = format_solution(grid, chats, texte)
    erreurs = check_solution_text(sortie)                     # vérification du fichier lui-même
    if erreurs:
        raise SolveError("fichier solution incohérent : " + "; ".join(erreurs))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(sortie)
        print(f"solution vérifiée écrite dans {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(sortie)


if __name__ == "__main__":
    main()
