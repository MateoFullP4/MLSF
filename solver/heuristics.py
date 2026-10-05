"""Heuristiques de branchement H0..H7 pour DPLL_H (Question 4).

Une heuristique choisit, au moment d'une décision (ligne 17 de
l'algorithme 3), un LITTÉRAL l : brancher sur l, c'est essayer d'abord
p <- 1 si l = p, p <- 0 si l = ¬p (puis la valeur opposée en cas d'échec).

Construction générique
----------------------
H2..H7 se décrivent par deux choix indépendants :

    MESURE s(l) attachée à chaque littéral l de la formule F
        occ     : occ(l, F), nombre d'occurrences de l              (H2, H3)
        occmin  : occ_k(l, F), occurrences dans les clauses de taille
                  minimale k = min |C|                              (H4, H5)
        jw      : J(l) = Σ_{C ∋ l} 2^-|C|  (Jeroslow-Wang)          (H6, H7)

    MODE de sélection
        var : variable p maximisant s(p) + s(¬p), c'est-à-dire #(p, F),
              #_k(p, F) ou Σ_k #_k(p, F) 2^-k selon la mesure ; valeur de
              vérité 1 si s(p) ≥ s(¬p), 0 sinon (polarité majoritaire) ;
        lit : littéral l maximisant s(l) ; valeur donnée par son signe.

    H2 = (occ, var)     H3 = (occ, lit)
    H4 = (occmin, var)  H5 = (occmin, lit)
    H6 = (jw, var)      H7 = (jw, lit)

et chacune existe en version
    dynamique (Hd) : s est recalculée sur la formule COURANTE à chaque
                     décision (coût O(|F|) par décision) ;
    statique  (Hs) : s est calculée UNE fois sur la formule initiale, qui
                     fixe un ordre de préférence des littéraux ; une
                     décision prend le premier littéral de cet ordre dont la
                     variable apparaît encore dans la formule courante.

H0 (choix aléatoire, RandomChoice de l'algorithme 2) et H1 (première
variable libre, valeur 1) complètent la liste.

Conventions
-----------
- « Variable non encore affectée » = variable qui apparaît dans la formule
  courante. Dans notre DPLL par réécriture, une variable affectée disparaît
  de F ; une variable non affectée mais absente de F (toutes ses clauses
  sont satisfaites) n'a aucune influence : brancher dessus serait inutile.
- Égalités : à score égal, on prend la plus petite variable, puis le
  littéral positif. Ce départage déterministe rend les résultats
  reproductibles (seule H0 utilise le hasard).
"""

import random
from collections import Counter
from itertools import chain

from solver.dpll import random_choice


def presentes(F):
    """Ensemble des variables de F (comme dpll.variables, mais la boucle
    interne est faite en C par chain/map : environ deux fois plus rapide)."""
    return set(map(abs, chain.from_iterable(F)))


# ---------------------------------------------------------------------------
# Mesures s(l) sur une formule (dictionnaires littéral -> score)
# ---------------------------------------------------------------------------

def mesure_occ(F):
    """occ(l, F) pour chaque littéral l de F."""
    return Counter(chain.from_iterable(F))


def mesure_occmin(F):
    """occ_k(l, F) avec k = taille minimale d'une clause de F."""
    k = min(map(len, F))
    return Counter(chain.from_iterable(c for c in F if len(c) == k))


def mesure_jw(F):
    """J(l) = Σ_{C ∈ F, l ∈ C} 2^-|C|  (calcul exact : sommes de puissances de 2)."""
    s = {}
    for c in F:
        w = 2.0 ** -len(c)
        for l in c:
            s[l] = s.get(l, 0.0) + w
    return s


MESURES = {"occ": mesure_occ, "occmin": mesure_occmin, "jw": mesure_jw}


# ---------------------------------------------------------------------------
# Modes de sélection
# ---------------------------------------------------------------------------

def choix_variable(s):
    """Variable p maximisant s(p) + s(¬p), avec la polarité majoritaire."""
    vs = {abs(l) for l in s}
    p = max(vs, key=lambda v: (s.get(v, 0) + s.get(-v, 0), -v))
    return p if s.get(p, 0) >= s.get(-p, 0) else -p


def choix_litteral(s):
    """Littéral l maximisant s(l)."""
    return max(s, key=lambda l: (s[l], -abs(l), l > 0))


def ordre_variables(s):
    """Ordre statique (mode var) : littéraux classés par score de leur variable."""
    vs = {abs(l) for l in s}
    tri = sorted(vs, key=lambda v: (-(s.get(v, 0) + s.get(-v, 0)), v))
    return [p if s.get(p, 0) >= s.get(-p, 0) else -p for p in tri]


def ordre_litteraux(s):
    """Ordre statique (mode lit) : littéraux classés par score."""
    return sorted(s, key=lambda l: (-s[l], abs(l), l < 0))


# ---------------------------------------------------------------------------
# Heuristiques
# ---------------------------------------------------------------------------

class Heuristique:
    """Interface : prepare(F) une fois sur la formule initiale, puis
    choose(F) à chaque décision, sur la formule courante (non vide, sans
    clause vide, unitaire ni littéral pur)."""

    nom = "?"
    dynamique = True

    def prepare(self, F):
        pass

    def choose(self, F):
        raise NotImplementedError


class Aleatoire(Heuristique):
    """H0 (CA) : exactement RandomChoice de l'algorithme 2 (même tirage)."""

    def __init__(self, rng):
        self.rng = rng

    def choose(self, F):
        return random_choice(F, self.rng)


class PremiereVariable(Heuristique):
    """H1 (PVL) : plus petite variable présente dans F, valeur 1."""

    def choose(self, F):
        return min(presentes(F))


class Dynamique(Heuristique):
    def __init__(self, mesure, mode):
        self.mesure = MESURES[mesure]
        self.selection = choix_variable if mode == "var" else choix_litteral

    def choose(self, F):
        return self.selection(self.mesure(F))


class Statique(Heuristique):
    dynamique = False

    def __init__(self, mesure, mode):
        self.mesure = MESURES[mesure]
        self.mode = mode
        self.ordre = None

    def prepare(self, F):
        s = self.mesure(F) if F else {}
        # Tous les littéraux de F doivent figurer dans l'ordre, y compris
        # ceux que la mesure ignore (score 0) : pour H4s/H5s, seuls les
        # littéraux des clauses de taille minimale de la formule INITIALE
        # sont mesurés (par exemple ses clauses unitaires), les autres sont
        # alors départagés par leur numéro.
        s = {l: s.get(l, 0) for l in chain.from_iterable(F)}
        self.ordre = ordre_variables(s) if self.mode == "var" else ordre_litteraux(s)

    def choose(self, F):
        vs = presentes(F)
        for l in self.ordre:
            if abs(l) in vs:
                return l
        # une variable de F absente de la formule initiale ne peut pas exister
        raise AssertionError("aucune variable de l'ordre statique dans F")


# Hi -> (mesure, mode, nom long de l'énoncé)
DEFINITIONS = {
    "H2": ("occ", "var", "VPPM"), "H3": ("occ", "lit", "LP"),
    "H4": ("occmin", "var", "VFCM"), "H5": ("occmin", "lit", "LFCM"),
    "H6": ("jw", "var", "VJW"), "H7": ("jw", "lit", "LJW"),
}

NOMS = ["H0", "H1"] + [h + v for h in DEFINITIONS for v in ("s", "d")]


def make_heuristic(nom, seed=0):
    """Construit l'heuristique `nom` : H0, H1, ou H2s/H2d ... H7s/H7d.

    Les sigles de l'énoncé sont aussi acceptés (CA, PVL, VPPM-s, LJW-d, ...).
    """
    alias = {"CA": "H0", "PVL": "H1"}
    alias.update({f"{n}-{v}": h + v for h, (_, _, n) in DEFINITIONS.items() for v in "sd"})
    nom = alias.get(nom, nom)
    if nom == "H0":
        h = Aleatoire(random.Random(seed))
    elif nom == "H1":
        h = PremiereVariable()
    elif nom[:2] in DEFINITIONS and nom[2:] in ("s", "d"):
        mesure, mode, _ = DEFINITIONS[nom[:2]]
        h = (Statique if nom[2] == "s" else Dynamique)(mesure, mode)
    else:
        raise ValueError(f"heuristique inconnue : {nom} (connues : {', '.join(NOMS)})")
    h.nom = nom
    return h
