"""Compteurs d'exécution de DPLL_H (Questions 4 et 5).

Les critères correspondent à ceux de la Question 5 :
    decisions   nombre de décisions (ligne 17 de l'algorithme 3)
    backtracks  nombre de retours arrière (branche else, ligne 21)
    unit        nombre de propagations unitaires (ligne 5)
    pure        nombre d'éliminations de littéraux purs (ligne 11)
    nodes       nombre d'appels récursifs (nœuds de l'arbre de recherche)
    max_depth   profondeur maximale de récursion atteinte
    heur_time   temps passé à choisir les littéraux de décision (s)
    prep_time   temps du pré-traitement d'une heuristique statique (s)
Le temps total est mesuré par l'appelant (bench/runner.py), ce qui donne
le ratio heur_time / temps total.

Coût de l'instrumentation : quelques incréments d'entiers par nœud et deux
appels à time.perf_counter (~0,1 µs) par décision, négligeables devant le
coût d'un nœud (O(|F|), de l'ordre de 100 µs sur nos instances).
"""

from dataclasses import dataclass, asdict


@dataclass
class Stats:
    decisions: int = 0
    backtracks: int = 0
    unit: int = 0
    pure: int = 0
    nodes: int = 0
    max_depth: int = 0
    heur_time: float = 0.0
    prep_time: float = 0.0

    def as_dict(self):
        return asdict(self)
