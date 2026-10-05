"""Algorithme DPLL : versions 1 et 2 de l'énoncé (Question 2).

    dpll_v1(F)  -> True / False                       (algorithme 1)
    dpll_v2(F)  -> (True, valuation) / (False, None)   (algorithme 2)

La formule F est une liste de frozenset de littéraux (voir dimacs.py).
Une valuation est un ensemble de littéraux : 3 signifie x3 <- 1,
-3 signifie x3 <- 0.

Ces versions suivent l'énoncé ligne à ligne : chaque appel récursif
reçoit une NOUVELLE formule simplifiée (copie). C'est simple et facile
à prouver correct, mais coûteux ; l'optimisation viendra à la Question 6.
"""

import random
import sys


# ---------------------------------------------------------------------------
# Opérations élémentaires sur la formule
# ---------------------------------------------------------------------------

def simplify(F, lit):
    """Calcule F[lit <- 1].

    - une clause contenant lit est vraie : on la supprime ;
    - une clause contenant -lit perd ce littéral (il est faux) ;
    - les autres clauses sont gardées telles quelles (partagées, pas copiées).
    """
    neg = -lit
    res = []
    for c in F:
        if lit in c:
            continue
        if neg in c:
            res.append(c - {neg})          # nouveau frozenset sans ¬lit
        else:
            res.append(c)
    return res


def has_empty_clause(F):
    return any(len(c) == 0 for c in F)


def find_unit(F):
    """Renvoie le littéral d'une clause unitaire, ou None s'il n'y en a pas."""
    for c in F:
        if len(c) == 1:
            return next(iter(c))
    return None


def find_pure(F):
    """Renvoie un littéral pur (l présent, ¬l absent de F), ou None."""
    litteraux = set()
    for c in F:
        litteraux |= c
    for l in litteraux:
        if -l not in litteraux:
            return l
    return None


def variables(F):
    """Ensemble des variables apparaissant dans F."""
    vs = set()
    for c in F:
        for l in c:
            vs.add(abs(l))
    return vs


def random_choice(F, rng):
    """RandomChoice de l'énoncé : variable de F au hasard, valeur au hasard.

    Renvoie directement le littéral correspondant : p si b = 1, -p si b = 0.
    On trie les variables pour que le tirage ne dépende que de la graine
    (l'ordre d'itération d'un set n'est pas garanti).
    """
    p = rng.choice(sorted(variables(F)))
    b = rng.random() < 0.5
    return p if b else -p


# ---------------------------------------------------------------------------
# Algorithme 1 : satisfaisabilité seule
# ---------------------------------------------------------------------------

def dpll_v1(F, rng):
    if has_empty_clause(F):                 # ligne 1 : clause vide
        return False
    if not F:                               # ligne 3 : plus aucune clause
        return True

    l = find_unit(F)                        # ligne 5 : clause unitaire
    if l is not None:
        return dpll_v1(simplify(F, l), rng)

    l = find_pure(F)                        # ligne 7 : littéral pur
    if l is not None:
        return dpll_v1(simplify(F, l), rng)

    l = random_choice(F, rng)               # ligne 9 : branchement
    if dpll_v1(simplify(F, l), rng):        # ligne 10 : branche p <- b
        return True
    return dpll_v1(simplify(F, -l), rng)    # ligne 13 : branche p <- ¬b


# ---------------------------------------------------------------------------
# Algorithme 2 : satisfaisabilité + valuation témoin
# ---------------------------------------------------------------------------

def dpll_v2(F, rng):
    """Renvoie (True, v) avec v un ensemble de littéraux, ou (False, None)."""
    if has_empty_clause(F):                 # lignes 1-2
        return False, None
    if not F:                               # lignes 3-4
        return True, set()

    l = find_unit(F)                        # lignes 5-10
    if l is None:
        l = find_pure(F)                    # lignes 11-16
    if l is not None:
        # Unitaire et pur ont exactement le même traitement : une seule
        # branche, pas de retour arrière possible sur ce choix.
        sat, v = dpll_v2(simplify(F, l), rng)
        if sat:
            v.add(l)                        # v ∪ {l}
            return True, v
        return False, None

    l = random_choice(F, rng)               # ligne 17
    sat, v = dpll_v2(simplify(F, l), rng)   # ligne 18 : p <- b
    if sat:
        v.add(l)
        return True, v
    sat, v = dpll_v2(simplify(F, -l), rng)  # ligne 22 : retour arrière, p <- ¬b
    if sat:
        v.add(-l)
        return True, v
    return False, None


# ---------------------------------------------------------------------------
# Utilitaires autour du solveur
# ---------------------------------------------------------------------------

def complete_model(valuation, nb_vars):
    """Transforme une valuation partielle en modèle complet sur x1..x_n.

    Les variables qui ont disparu de la formule sans être affectées
    (toutes leurs clauses étaient déjà satisfaites) peuvent prendre
    n'importe quelle valeur : on choisit Faux.
    Renvoie une liste [±1, ±2, ..., ±n].
    """
    vraies = {l for l in valuation if l > 0}
    return [k if k in vraies else -k for k in range(1, nb_vars + 1)]


def check_model(clauses, modele):
    """Vérifie qu'un modèle (liste ou ensemble de littéraux) satisfait chaque clause."""
    m = set(modele)
    return all(any(l in m for l in c) for c in clauses)


def solve(nb_vars, clauses, version=2, seed=None):
    """Point d'entrée commun.

    Renvoie (True, modele_complet) ou (False, None) ; pour la version 1,
    renvoie (statut, None).

    Profondeur de récursion : chaque appel affecte au moins une variable
    de la formule courante, donc la profondeur est au plus nb_vars + 1.
    On relève la limite de Python (1000 par défaut) en conséquence.
    """
    sys.setrecursionlimit(max(sys.getrecursionlimit(), nb_vars + 1000))
    rng = random.Random(seed)
    if version == 1:
        return dpll_v1(clauses, rng), None
    sat, v = dpll_v2(clauses, rng)
    if not sat:
        return False, None
    return True, complete_model(v, nb_vars)


if __name__ == "__main__":
    # Essai rapide : python -m solver.dpll fichier.cnf [1|2]
    from solver.dimacs import read_dimacs

    n, cls = read_dimacs(sys.argv[1])
    version = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    sat, modele = solve(n, cls, version=version)
    print("s SATISFIABLE" if sat else "s UNSATISFIABLE")
    if modele is not None:
        print("v " + " ".join(map(str, modele)) + " 0")