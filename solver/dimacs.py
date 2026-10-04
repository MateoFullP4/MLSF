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

    Le parseur lit les entiers comme un flux, ce qui le rend tolérant :
      - une clause peut s'étendre sur plusieurs lignes ;
      - plusieurs clauses peuvent tenir sur une même ligne ;
      - un « % » isolé (fin de fichier des benchmarks SATLIB) arrête la lecture.
    """
    nb_vars = None
    nb_clauses_annonce = None
    clauses = []
    courante = []

    for num_ligne, ligne in enumerate(text.splitlines(), start=1):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("c"):
            continue                                  # ligne vide ou commentaire
        if ligne.startswith("%"):
            break                                     # convention SATLIB
        if ligne.startswith("p"):
            morceaux = ligne.split()
            if len(morceaux) != 4 or morceaux[1] != "cnf":
                raise DimacsError(f"ligne {num_ligne} : en-tête invalide : {ligne!r}")
            nb_vars, nb_clauses_annonce = int(morceaux[2]), int(morceaux[3])
            continue
        if nb_vars is None:
            raise DimacsError(f"ligne {num_ligne} : clause avant l'en-tête 'p cnf'")

        for jeton in ligne.split():
            try:
                lit = int(jeton)
            except ValueError:
                raise DimacsError(f"ligne {num_ligne} : entier attendu, lu {jeton!r}")
            if lit == 0:                              # fin de clause
                clauses.append(frozenset(courante))
                courante = []
            else:
                if abs(lit) > nb_vars:
                    raise DimacsError(
                        f"ligne {num_ligne} : variable {abs(lit)} > {nb_vars} annoncées")
                courante.append(lit)

    if nb_vars is None:
        raise DimacsError("en-tête 'p cnf' absent")
    if courante:                                      # dernière clause sans 0 final
        clauses.append(frozenset(courante))
    if len(clauses) != nb_clauses_annonce:
        # On tolère l'écart mais on le signale sur stderr (jamais sur stdout).
        print(f"c attention : {len(clauses)} clauses lues, "
              f"{nb_clauses_annonce} annoncées", file=sys.stderr)
    return nb_vars, clauses


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