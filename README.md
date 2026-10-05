# MLSF – Solveur SAT DPLL pour Meowdoku

Projet MLSF 2026-2027, partie I. Le rapport détaillé (choix de conception,
résultats, analyses) est dans [rapport/rapport.md](rapport/rapport.md).

Python 3.12+, bibliothèque standard uniquement pour tout le code rendu.
`requirements-dev.txt` liste les outils de développement (oracle MiniSat,
figures). Toutes les commandes se lancent depuis la racine du dépôt.

## Question 1 – Modélisation

```
python meowdoku/encode.py instances/meowdoku/grille1.txt         # grille -> DIMACS
python meowdoku/generate.py 8 --seed 1 -o grille8.txt            # grille 8x8, 8 régions
python meowdoku/generate.py 10 --count 5 --dir out --cnf         # 5 grilles + leurs CNF
```

## Question 2 – DPLL

```
python -m solver.dpll instances/lampes.cnf [1|2]                 # algorithme 1 ou 2
python tools/validate.py [dossier] --timeout 60                  # validation (statuts + modèles)
python tools/oracle.py [dossier]                                 # statuts attendus (python-sat)
python bench/bench_q2.py tout && python bench/plots.py q2        # mesures et figures
```

## Question 3 – Résolution d'une grille

```
python meowdoku/solve_grid.py instances/meowdoku/grille1.txt [-o solution.txt]
python meowdoku/verify.py solution.txt
python meowdoku/generate.py 8 --unique --seed 3 -o grille8u.txt  # solution unique
```

## Question 4 – Heuristiques (DPLL_H)

```
python bench/runner.py H6d instances/satlib/uuf50-01.cnf         # H0, H1, H2s/H2d ... H7s/H7d
python meowdoku/solve_grid.py instances/meowdoku/grille1.txt --solver H7s
```

## Tests

```
python tests/test_meowdoku.py
python tests/test_dpll.py
python tests/test_solve_grid.py
python tests/test_heuristics.py
```
