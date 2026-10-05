"""Algorithme 3 de l'énoncé : DPLL_H, paramétré par une heuristique (Question 4).

    dpllh(F, h, stats) -> (True, valuation) / (False, None)

Même structure et mêmes opérations élémentaires que l'algorithme 2
(solver/dpll.py) ; seule la ligne 17 change : RandomChoice(F) est remplacé
par Heuristics(F, H), c'est-à-dire h.choose(F). L'exécution est
instrumentée (solver/stats.py) pour la Question 5.

Avec H0 et la même graine, dpllh effectue EXACTEMENT les mêmes tirages
que dpll_v2, donc parcourt le même arbre et renvoie la même valuation :
c'est vérifié par les tests et garantit que DPLL_H généralise bien
l'algorithme 2.
"""

import sys
from time import perf_counter

from solver.dpll import simplify, has_empty_clause, find_unit, find_pure, complete_model
from solver.heuristics import make_heuristic
from solver.stats import Stats


def dpllh(F, h, st, prof=0):
    st.nodes += 1
    if prof > st.max_depth:
        st.max_depth = prof

    if has_empty_clause(F):                     # lignes 1-2
        return False, None
    if not F:                                   # lignes 3-4
        return True, set()

    l = find_unit(F)                            # lignes 5-10
    if l is not None:
        st.unit += 1
    else:
        l = find_pure(F)                        # lignes 11-16
        if l is not None:
            st.pure += 1
    if l is not None:
        sat, v = dpllh(simplify(F, l), h, st, prof + 1)
        if sat:
            v.add(l)
            return True, v
        return False, None

    st.decisions += 1                           # ligne 17 : Heuristics(F, H)
    t = perf_counter()
    l = h.choose(F)
    st.heur_time += perf_counter() - t

    sat, v = dpllh(simplify(F, l), h, st, prof + 1)          # ligne 18 : p <- b
    if sat:
        v.add(l)
        return True, v
    st.backtracks += 1                                       # ligne 21 : else
    sat, v = dpllh(simplify(F, -l), h, st, prof + 1)         # ligne 22 : p <- ¬b
    if sat:
        v.add(-l)
        return True, v
    return False, None


def solve_h(nb_vars, clauses, heuristique="H0", seed=0):
    """Résout avec DPLL_H ; renvoie (sat, modèle complet ou None, Stats)."""
    sys.setrecursionlimit(max(sys.getrecursionlimit(), nb_vars + 1000))
    h = make_heuristic(heuristique, seed) if isinstance(heuristique, str) else heuristique
    st = Stats()
    t = perf_counter()
    h.prepare(clauses)
    st.prep_time = perf_counter() - t
    st.heur_time = st.prep_time
    sat, v = dpllh(clauses, h, st)
    return sat, (complete_model(v, nb_vars) if sat else None), st
