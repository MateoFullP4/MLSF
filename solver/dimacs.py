"""Lecture et écriture de fichiers au format DIMACS CNF.

Représentation choisie pour une formule CNF :
    - un littéral est un entier non nul : k pour x_k, -k pour ¬x_k ;
    - une clause est un frozenset de littéraux ;
    - une formule est une liste de clauses.

Pourquoi des frozenset ?
    - le test « l in C » se fait en temps constant (utile pour F[l <- 1]) ;
    - les doublons dans une clause (« 1 1 2 0 ») disparaissent d'eux-mêmes ;
    - ils sont immuables : on peut partager une clause entre deux formules
      sans risque qu'une modification de l'une abîme l'autre.
"""

import sys


class DimacsError(Exception):
    """Fichier DIMACS mal formé."""


def parse_dimacs(text):
    """Analyse le contenu d'un fichier DIMACS.

    Renvoie un couple (nb_vars, clauses) où clauses est une liste de frozenset.

    Lecture normale : les entiers sont lus comme un FLUX, chaque 0 fermant
    une clause. C'est la lecture standard du format, qui tolère qu'une
    clause s'étende sur plusieurs lignes ou que plusieurs clauses tiennent
    sur une ligne. Un « % » isolé (fin de fichier des benchmarks SATLIB)
    arrête la lecture.

    Fichiers mal formés : le nombre de clauses annoncé dans l'en-tête sert
    de contrôle. S'il ne correspond pas à la lecture en flux :
      1. des clauses VIDES en surnombre à la fin du fichier sont ignorées
         (cas des fichiers SATLIB « pret » qui finissent par un « 0 »
         isolé : le lire comme une clause vide rendrait toute formule
         insatisfiable) ;
      2. sinon on essaie une lecture LIGNE PAR LIGNE (chaque ligne est une
         clause, le 0 final étant facultatif), conformément à l'énoncé
         (« chaque clause tient sur une ligne ») ; on la retient si elle
         donne exactement le nombre annoncé (cas de « dubois100.cnf », où
         des lignes n'ont pas de 0 final : la lecture en flux fusionnerait
         deux clauses en une, ce qui affaiblirait la formule) ;
      3. sinon on garde la lecture en flux.
    Toute correction est signalée sur stderr (jamais sur stdout).
    """
    nb_vars = None
    nb_clauses_annonce = None
    lignes = []                                       # lignes de clauses, en entiers

    for num_ligne, ligne in enumerate(text.splitlines(), start=1):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("c"):
            continue                                  # ligne vide ou commentaire
        if ligne.startswith("%"):
            break                                     # convention SATLIB
        if ligne.startswith("p"):
            morceaux = ligne.split()
            try:
                if len(morceaux) != 4 or morceaux[1] != "cnf":
                    raise ValueError
                nb_vars, nb_clauses_annonce = int(morceaux[2]), int(morceaux[3])
                if nb_vars < 0 or nb_clauses_annonce < 0:
                    raise ValueError
            except ValueError:
                raise DimacsError(f"ligne {num_ligne} : en-tête invalide : {ligne!r}")
            continue
        if nb_vars is None:
            raise DimacsError(f"ligne {num_ligne} : clause avant l'en-tête 'p cnf'")

        entiers = []
        for jeton in ligne.split():
            try:
                lit = int(jeton)
            except ValueError:
                raise DimacsError(f"ligne {num_ligne} : entier attendu, lu {jeton!r}")
            if abs(lit) > nb_vars:
                raise DimacsError(
                    f"ligne {num_ligne} : variable {abs(lit)} > {nb_vars} annoncées")
            entiers.append(lit)
        lignes.append(entiers)

    if nb_vars is None:
        raise DimacsError("en-tête 'p cnf' absent")

    clauses = _lecture_flux(lignes)
    if len(clauses) != nb_clauses_annonce:
        corrigees = _sans_vides_finales(clauses, nb_clauses_annonce)
        if len(corrigees) == nb_clauses_annonce:
            print(f"c attention : {len(clauses) - len(corrigees)} clause(s) vide(s) "
                  f"en fin de fichier ignorée(s)", file=sys.stderr)
            clauses = corrigees
        else:
            par_ligne = _sans_vides_finales(
                [frozenset(l for l in e if l != 0) for e in lignes], nb_clauses_annonce)
            if len(par_ligne) == nb_clauses_annonce:
                print("c attention : 0 final manquant, lecture ligne par ligne",
                      file=sys.stderr)
                clauses = par_ligne
    if len(clauses) != nb_clauses_annonce:
        # On tolère l'écart mais on le signale sur stderr (jamais sur stdout).
        print(f"c attention : {len(clauses)} clauses lues, "
              f"{nb_clauses_annonce} annoncées", file=sys.stderr)
    return nb_vars, clauses


def _lecture_flux(lignes):
    """Lecture standard : les 0 ferment les clauses, les fins de ligne ne comptent pas."""
    clauses, courante = [], []
    for entiers in lignes:
        for lit in entiers:
            if lit == 0:                              # fin de clause
                clauses.append(frozenset(courante))
                courante = []
            else:
                courante.append(lit)
    if courante:                                      # dernière clause sans 0 final
        clauses.append(frozenset(courante))
    return clauses


def _sans_vides_finales(clauses, nb_annonce):
    """Retire les clauses vides situées au-delà du nombre annoncé, en fin de liste."""
    res = list(clauses)
    while len(res) > nb_annonce and not res[-1]:
        res.pop()
    return res


def read_dimacs(chemin):
    """Lit un fichier DIMACS et renvoie (nb_vars, clauses)."""
    with open(chemin, encoding="utf-8") as f:
        return parse_dimacs(f.read())


def write_dimacs(chemin, nb_vars, clauses, commentaires=()):
    """Écrit une formule au format DIMACS (servira pour la Question 1)."""
    with open(chemin, "w", encoding="utf-8") as f:
        for c in commentaires:
            f.write(f"c {c}\n")
        f.write(f"p cnf {nb_vars} {len(clauses)}\n")
        for clause in clauses:
            # tri pour un fichier lisible et reproductible
            f.write(" ".join(str(l) for l in sorted(clause, key=abs)) + " 0\n")