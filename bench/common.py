"""Outils communs aux scripts de mesure et de validation.

execute(...) lance bench/runner.py dans un sous-processus avec un délai ;
run_all(...) exécute une liste de tâches en parallèle (threads qui
attendent chacun leur sous-processus).

Remarque sur le parallélisme : les mesures tournent sur plusieurs cœurs à
la fois pour tenir dans un temps raisonnable. Cela peut perturber
légèrement les temps (fréquence turbo, cache partagé) ; on garde donc un
nombre de tâches parallèles inférieur au nombre de cœurs physiques, et on
compare toujours des solveurs mesurés dans les mêmes conditions.
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RUNNER = os.path.join(RACINE, "bench", "runner.py")


def execute(solveur, chemin, seed=0, delai=60.0):
    """Résultat (dictionnaire) de runner.py, ou {"status": "TIMEOUT" / "ERROR"}."""
    cmd = [sys.executable, RUNNER, solveur, chemin, "--seed", str(seed)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=delai)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT"}
    if p.returncode != 0:
        return {"status": "ERROR", "error": p.stderr.strip().splitlines()[-1:]}
    return json.loads(p.stdout)


def run_all(taches, delai=60.0, jobs=None, progression=True):
    """taches : liste de (solveur, chemin, graine). Renvoie la liste des résultats."""
    jobs = jobs or max(1, (os.cpu_count() or 2) // 2)
    faites = [0]

    def une(t):
        r = execute(t[0], t[1], t[2], delai)
        faites[0] += 1
        if progression and faites[0] % 25 == 0:
            print(f"  {faites[0]}/{len(taches)}", file=sys.stderr)
        return r

    with ThreadPoolExecutor(jobs) as pool:
        return list(pool.map(une, taches))
