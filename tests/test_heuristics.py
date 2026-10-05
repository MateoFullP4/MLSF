"""Tests de la Question 4 (heuristiques, DPLL_H).  Lancer depuis la racine :

    python tests/test_heuristics.py

Stratégie :
  1. chaque heuristique est vérifiée À LA MAIN sur la formule d'exemple de
     l'énoncé (les calculs sont détaillés en commentaire) ;
  2. avec H0 et une même graine, DPLL_H et l'algorithme 2 renvoient
     exactement la même valuation (même arbre parcouru) ;
  3. toutes les heuristiques donnent le statut de la force brute sur
     400 formules aléatoires, avec des modèles vérifiés (« conformes à
     l'implémentation de l'algorithme 2 » au sens de l'énoncé) ;
  4. les compteurs sont cohérents (relations entre décisions, retours
     arrière et nœuds).
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver.heuristics import (make_heuristic, NOMS, mesure_occ,         # noqa: E402
                               mesure_occmin, mesure_jw)
from solver.dpllh import solve_h                                         # noqa: E402
from solver.dpll import solve, check_model                              # noqa: E402
from tools.gen_cnf import random_ksat, pigeonhole                        # noqa: E402
from test_dpll import brute_force                                        # noqa: E402

F = frozenset
# (x1 ∨ x2 ∨ ¬x4) ∧ (x2 ∨ x3) ∧ (x1 ∨ ¬x2 ∨ x4 ∨ ¬x5)
EXEMPLE = [F({1, 2, -4}), F({2, 3}), F({1, -2, 4, -5})]


def test_mesures_exemple():
    occ = mesure_occ(EXEMPLE)
    # énoncé : #(x2) = 3, #+(x2) = 2, #-(x2) = 1, occ(x4) = 1
    assert occ[2] + occ[-2] == 3 and occ[2] == 2 and occ[-2] == 1 and occ[4] == 1
    # k = 2 : seule la clause (x2 ∨ x3) compte
    assert dict(mesure_occmin(EXEMPLE)) == {2: 1, 3: 1}
    jw = mesure_jw(EXEMPLE)
    # énoncé : Σ_k #_k(x2) 2^-k = 1/8 + 1/4 + 1/16 = 7/16
    assert jw[2] + jw[-2] == 7 / 16


def test_choix_exemple():
    attendu = {
        # H1 : plus petite variable, valeur 1
        "H1": 1,
        # H2 : #(p) = x1:2 x2:3 x3:1 x4:2 x5:1 -> x2 ; #+ = 2 >= #- = 1 -> x2 <- 1
        "H2d": 2,
        # H3 : occ = x1:2 x2:2 (égalité -> plus petite variable) -> x1
        "H3d": 1,
        # H4 : k = 2, #_2 = x2:1 x3:1 (égalité) -> x2, polarité + -> x2 <- 1
        "H4d": 2,
        # H5 : littéraux de taille 2 : x2, x3 (égalité) -> x2
        "H5d": 2,
        # H6 : x2 = 7/16 (max) ; positif 1/8 + 1/4 = 6/16 >= 1/16 -> x2 <- 1 (énoncé)
        "H6d": 2,
        # H7 : J(x2) = 6/16, J(x3) = 4/16, J(x1) = 3/16 -> x2
        "H7d": 2,
    }
    for nom, l in attendu.items():
        h = make_heuristic(nom)
        h.prepare(EXEMPLE)
        assert h.choose(EXEMPLE) == l, (nom, h.choose(EXEMPLE), l)
        if nom.endswith("d"):
            # sur la formule initiale, statique et dynamique coïncident
            hs = make_heuristic(nom[:-1] + "s")
            hs.prepare(EXEMPLE)
            assert hs.choose(EXEMPLE) == l, nom
    # version statique sur une formule réduite : x2 a disparu -> suivant de l'ordre
    hs = make_heuristic("H6s")
    hs.prepare(EXEMPLE)
    reduite = [F({1, -4}), F({3}), F({1, 4, -5})]  # forme sans x2 (non issue de DPLL)
    # ordre statique H6 : x2 (7/16), x3 (4/16), x1 (3/16), x4 (3/16), x5 (1/16)
    assert hs.choose(reduite) == 3
    # sigles de l'énoncé
    assert make_heuristic("VJW-d").nom == "H6d" and make_heuristic("CA").nom == "H0"


def test_h0_identique_algorithme2():
    rng = random.Random(3)
    for _ in range(150):
        n = rng.randint(5, 25)
        cls = random_ksat(n, rng.randint(n, 5 * n), 3, rng)
        for graine in (0, 1):
            sat2, m2 = solve(n, cls, version=2, seed=graine)
            sath, mh, _ = solve_h(n, cls, "H0", seed=graine)
            assert (sat2, m2) == (sath, mh)


def test_contre_force_brute():
    rng = random.Random(2026)
    bilan = {True: 0, False: 0}
    for _ in range(400):
        n = rng.randint(3, 12)
        k = rng.choice((2, 3, 3, 4))
        cls = random_ksat(n, rng.randint(1, 6 * n), min(k, n), rng)
        if rng.random() < 0.2:                           # quelques clauses unitaires
            cls.append(F({rng.choice((1, -1)) * rng.randint(1, n)}))
        attendu = brute_force(n, cls)
        bilan[attendu] += 1
        for nom in NOMS:
            sat, m, st = solve_h(n, cls, nom, seed=1)
            assert sat == attendu, (nom, cls)
            if sat:
                assert len(m) == n and check_model(cls, m), (nom, cls, m)
    print(f"    400 formules x {len(NOMS)} heuristiques : "
          f"{bilan[True]} SAT, {bilan[False]} UNSAT")


def test_tiroirs_et_compteurs():
    nv, cls = pigeonhole(4)
    for nom in NOMS:
        sat, _, st = solve_h(nv, cls, nom)
        assert not sat
        # sur une instance UNSAT, chaque décision est suivie d'un retour arrière
        assert st.backtracks == st.decisions
        # chaque nœud est la racine, un fils de décision (2 par décision) ou
        # l'unique fils d'une propagation (unitaire ou pur)
        assert st.nodes == 1 + 2 * st.decisions + st.unit + st.pure
        assert 0 <= st.heur_time and st.max_depth <= nv + 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"[..] {t.__name__}")
        t()
        print(f"[ok] {t.__name__}")
    print(f"\nTous les tests passent ({len(tests)}).")
