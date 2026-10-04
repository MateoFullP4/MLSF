# MLSF – Solveur SAT DPLL pour Meowdoku

Projet MLSF 2026-2027, partie I. Le rapport détaillé (choix de conception,
résultats, analyses) est dans [rapport/rapport.md](rapport/rapport.md).

Python 3.12+, bibliothèque standard uniquement. Toutes les commandes se lancent
depuis la racine du dépôt.

## Question 1 – Modélisation

```
python meowdoku/encode.py instances/meowdoku/grille1.txt         # grille -> DIMACS
python meowdoku/generate.py 8 --seed 1 -o grille8.txt            # grille 8x8, 8 régions
python meowdoku/generate.py 10 --count 5 --dir out --cnf         # 5 grilles + leurs CNF
```

## Tests

```
python tests/test_meowdoku.py
```
