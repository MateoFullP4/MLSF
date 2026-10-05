"""Tests de la Question 2.  Lancer depuis le dossier projet/ :

    python tests/test_dpll.py

Stratégie de validation :
  1. tests unitaires sur simplify / clause unitaire / littéral pur ;
  2. cas limites (formule vide, clause vide, tautologies) ;
  3. comparaison avec une recherche exhaustive (force brute) sur des
     centaines de petites formules aléatoires : c'est un « oracle » dont
     la correction est évidente ;
  4. pour chaque réponse SAT, vérification que le modèle satisfait toutes
     les clauses.
"""

import itertools
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from solver.dimacs import parse_dimacs, read_dimacs, DimacsError   # noqa: E402
from solver.dpll import (simplify, find_unit, find_pure,          # noqa: E402
                         solve, check_model)
from tools.gen_cnf import random_ksat, pigeonhole                  # noqa: E402

F = frozenset


def brute_force(nb_vars, clauses):
    """Essaie les 2^n valuations. Correct par construction, lent."""
    for bits in itertools.product((False, True), repeat=nb_vars):
        modele = {(i + 1) if b else -(i + 1) for i, b in enumerate(bits)}
        if check_model(clauses, modele):
            return True
    return False


def test_operations_elementaires():
    formule = [F({1, 2, -4}), F({2, 3}), F({1, -2, 4, -5})]
    # x2 <- 1 : les clauses 1 et 2 disparaissent, ¬x2 est retiré de la 3e
    assert simplify(formule, 2) == [F({1, 4, -5})]
    # x2 <- 0 : la clause 3 disparaît, x2 est retiré des clauses 1 et 2
    assert simplify(formule, -2) == [F({1, -4}), F({3})]
    assert find_unit(formule) is None
    assert find_unit([F({1, 2}), F({-3})]) == -3
    # littéraux purs de la formule : x1, x3, ¬x5
    assert find_pure(formule) in (1, 3, -5)
    assert find_pure([F({1, 2}), F({-1, -2})]) is None


def test_cas_limites():
    assert solve(0, [])[0] is True                       # aucune clause : SAT
    assert solve(1, [F()])[0] is False                   # clause vide : UNSAT
    assert solve(1, [F({1}), F({-1})])[0] is False       # x et ¬x
    sat, m = solve(2, [F({1, -1})])                      # tautologie seule
    assert sat and len(m) == 2
    n, cls = parse_dimacs("p cnf 2 1\n1\n-2 0\n")        # clause sur 2 lignes
    assert cls == [F({1, -2})]


def test_parseur_robuste():
    # plusieurs clauses sur une ligne, « % » de fin SATLIB
    assert parse_dimacs("c x\np cnf 3 2\n1 2 0 -3 0\n%\n0\n")[1] == [F({1, 2}), F({-3})]
    # « 0 » isolé en fin de fichier (fichiers SATLIB pret) : ignoré, et non
    # lu comme une clause vide qui rendrait la formule insatisfiable
    assert parse_dimacs("p cnf 2 1\n1 2 0\n0\n")[1] == [F({1, 2})]
    # 0 final manquant sur certaines lignes (dubois100.cnf) : lecture par ligne
    n, cls = parse_dimacs("p cnf 3 3\n1 2\n-1 3 0\n2 3 0\n")
    assert cls == [F({1, 2}), F({-1, 3}), F({2, 3})]
    # une vraie clause vide annoncée dans l'en-tête est conservée
    assert parse_dimacs("p cnf 1 2\n1 0\n0\n")[1] == [F({1}), F()]
    for mauvais in ("1 2 0\n", "p cnf x 2\n", "p dnf 2 1\n1 0\n", "p cnf 2 1\n3 0\n",
                    "p cnf 2 1\n1 a 0\n"):
        try:
            parse_dimacs(mauvais)
        except DimacsError:
            continue
        raise AssertionError(f"aurait dû être refusé : {mauvais!r}")


def test_lampes():
    chemin = os.path.join(os.path.dirname(__file__), "..", "instances", "lampes.cnf")
    n, cls = read_dimacs(chemin)
    for version in (1, 2):
        sat, m = solve(n, cls, version=version, seed=0)
        assert sat
    # Le problème a 3 solutions (L2 seule ; L3 seule ; L1 et L3) : on vérifie
    # le modèle renvoyé sans supposer lequel est trouvé.
    assert check_model(cls, m)


def test_contre_force_brute(nb_essais=600):
    rng = random.Random(12345)
    stats = {True: 0, False: 0}
    for essai in range(nb_essais):
        n = rng.randint(3, 12)
        m = rng.randint(1, 6 * n)
        k = rng.choice((1, 2, 3, 3, 3)) if n >= 3 else 1
        cls = random_ksat(n, m, k=k, rng=rng)
        attendu = brute_force(n, cls)
        stats[attendu] += 1
        for version in (1, 2):
            for graine in (0, 1, 2):
                sat, modele = solve(n, cls, version=version, seed=graine)
                assert sat == attendu, (essai, version, graine, n, cls)
                if version == 2 and sat:
                    assert len(modele) == n
                    assert check_model(cls, modele), (essai, cls, modele)
    print(f"    {nb_essais} formules : {stats[True]} SAT, {stats[False]} UNSAT")


def test_pigeonhole():
    for n in (2, 3, 4):
        nv, cls = pigeonhole(n)
        for version in (1, 2):
            assert solve(nv, cls, version=version, seed=0)[0] is False


def test_recursion_profonde():
    # Chaîne d'implications x1 -> x2 -> ... -> x3000 avec x1 forcé :
    # 3000 propagations unitaires imbriquées, au-delà de la limite par défaut.
    n = 3000
    cls = [F({1})] + [F({-i, i + 1}) for i in range(1, n)]
    sat, m = solve(n, cls, seed=0)
    assert sat and all(l > 0 for l in m)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"[..] {t.__name__}")
        t()
        print(f"[ok] {t.__name__}")
    print(f"\nTous les tests passent ({len(tests)}).")
