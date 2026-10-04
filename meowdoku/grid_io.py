"""Lecture / écriture des fichiers de grilles Meowdoku (Questions 1 et 3).

Format d'une grille (figure 1b de l'énoncé) :

    c Grille 1              <- commentaire(s), ignorés
    GRID 6 6                <- N lignes, M colonnes
    ZONES A B C D E F       <- noms des K régions
                            <- lignes vides ignorées
    A B C B B D             <- N lignes de M noms de région
    ...

Format d'une solution (figure 2) : la grille recopiée, puis
    - K lignes « région ligne colonne » (coordonnées à partir de 1) ;
    - N lignes de M symboles, « * » pour un chat et « . » sinon.

Choix d'interprétation (à défaut de précision dans l'énoncé) :
    - dans « GRID N M », N est le nombre de LIGNES et M celui de COLONNES ;
      c'est cohérent avec la notation x_{i,j}, (i, j) ∈ {1..N} × {1..M},
      et avec la figure 2 où « A 3 2 » désigne la ligne 3, colonne 2 ;
    - une ligne est un commentaire si son premier mot est exactement « c »
      (et non si elle commence par la lettre c : une région pourrait
      s'appeler « C » ou « chat ») ;
    - les noms de région sont des mots quelconques séparés par des espaces
      (au-delà de 26 régions, le générateur utilise AA, AB, ...). Si tous
      les noms font un caractère, une ligne écrite sans espaces (« ABCBBD »)
      est aussi acceptée.
"""

from dataclasses import dataclass


class GridError(Exception):
    """Fichier de grille mal formé ou grille illicite."""


@dataclass
class Grid:
    n: int                  # nombre de lignes
    m: int                  # nombre de colonnes
    zones: list             # noms des régions, dans l'ordre de la ligne ZONES
    regions: list           # regions[i][j] = nom de la région de la case (i+1, j+1)
    comments: list          # commentaires d'origine (sans le « c »)

    @property
    def k(self):
        return len(self.zones)

    def cells_of(self):
        """Dictionnaire région -> liste des cases (i, j), indices à partir de 1."""
        res = {z: [] for z in self.zones}
        for i in range(self.n):
            for j in range(self.m):
                res[self.regions[i][j]].append((i + 1, j + 1))
        return res


def _useful_lines(text):
    """Lignes non vides et non commentaires, avec leur numéro ; et les commentaires."""
    utiles, commentaires = [], []
    for num, ligne in enumerate(text.splitlines(), start=1):
        mots = ligne.split()
        if not mots:
            continue
        if mots[0] == "c":
            commentaires.append(ligne.strip()[1:].strip())
            continue
        utiles.append((num, mots))
    return utiles, commentaires


def _parse_grid_lines(utiles):
    """Analyse l'en-tête et la grille ; renvoie (n, m, zones, regions, reste)."""
    if not utiles:
        raise GridError("fichier vide")

    num, mots = utiles[0]
    if mots[0] != "GRID" or len(mots) != 3:
        raise GridError(f"ligne {num} : « GRID N M » attendu, lu {' '.join(mots)!r}")
    try:
        n, m = int(mots[1]), int(mots[2])
    except ValueError:
        raise GridError(f"ligne {num} : dimensions non entières")
    if n < 1 or m < 1:
        raise GridError(f"ligne {num} : dimensions {n}x{m} invalides")

    if len(utiles) < 2 or utiles[1][1][0] != "ZONES":
        raise GridError("ligne « ZONES ... » attendue après « GRID »")
    num, mots = utiles[1]
    zones = mots[1:]
    if not zones:
        raise GridError(f"ligne {num} : aucune région déclarée")
    if len(set(zones)) != len(zones):
        raise GridError(f"ligne {num} : nom de région en double")

    un_caractere = all(len(z) == 1 for z in zones)
    regions = []
    lignes_grille = utiles[2:2 + n]
    if len(lignes_grille) < n:
        raise GridError(f"{n} lignes de grille attendues, {len(lignes_grille)} lues")
    for num, mots in lignes_grille:
        if len(mots) == 1 and un_caractere and len(mots[0]) == m:
            mots = list(mots[0])                     # ligne écrite sans espaces
        if len(mots) != m:
            raise GridError(f"ligne {num} : {m} cases attendues, {len(mots)} lues")
        for z in mots:
            if z not in zones:
                raise GridError(f"ligne {num} : région {z!r} non déclarée dans ZONES")
        regions.append(mots)

    # Les régions doivent former une partition : chaque case a exactement une
    # région (garanti par la lecture) et chaque région est non vide.
    presentes = {z for ligne in regions for z in ligne}
    vides = [z for z in zones if z not in presentes]
    if vides:
        raise GridError(f"région(s) vide(s) : {' '.join(vides)}")

    return n, m, zones, regions, utiles[2 + n:]


def parse_grid(text):
    """Analyse le texte d'un fichier grille et renvoie un objet Grid.

    Les lignes qui suivent la grille (par exemple la solution d'un fichier
    produit par la Question 3) sont ignorées.
    """
    utiles, commentaires = _useful_lines(text)
    n, m, zones, regions, _ = _parse_grid_lines(utiles)
    return Grid(n, m, zones, regions, commentaires)


def read_grid(chemin):
    with open(chemin, encoding="utf-8") as f:
        return parse_grid(f.read())


def format_grid(grid):
    """Texte d'un fichier grille au format de la figure 1b."""
    lignes = [f"c {c}" for c in grid.comments]
    lignes.append(f"GRID {grid.n} {grid.m}")
    lignes.append("ZONES " + " ".join(grid.zones))
    lignes.append("")
    largeur = max(len(z) for z in grid.zones)
    for ligne in grid.regions:
        lignes.append(" ".join(z.ljust(largeur) for z in ligne).rstrip())
    return "\n".join(lignes) + "\n"


def write_grid(chemin, grid):
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(format_grid(grid))


# ---------------------------------------------------------------------------
# Solutions (Question 3)
# ---------------------------------------------------------------------------

def format_solution(grid, chats, texte_grille=None):
    """Texte d'un fichier solution au format de la figure 2.

    chats : dictionnaire région -> (i, j), indices à partir de 1.
    texte_grille : texte du fichier d'entrée, recopié tel quel s'il est fourni
    (l'énoncé demande que le fichier résultat recopie le fichier d'entrée).
    """
    entete = texte_grille if texte_grille is not None else format_grid(grid)
    lignes = [entete.rstrip("\n"), ""]
    for z in grid.zones:
        i, j = chats[z]
        lignes.append(f"{z} {i} {j}")
    lignes.append("")
    positions = set(chats.values())
    for i in range(1, grid.n + 1):
        lignes.append(" ".join("*" if (i, j) in positions else "."
                               for j in range(1, grid.m + 1)))
    return "\n".join(lignes) + "\n"


def parse_solution(text):
    """Relit un fichier solution ; renvoie (grid, chats, positions_de_la_carte).

    Les deux représentations de la solution (dictionnaire et carte en « * »)
    sont relues séparément pour pouvoir vérifier qu'elles concordent.
    """
    utiles, commentaires = _useful_lines(text)
    n, m, zones, regions, reste = _parse_grid_lines(utiles)
    grid = Grid(n, m, zones, regions, commentaires)

    if len(reste) < len(zones) + n:
        raise GridError("solution incomplète")
    chats = {}
    for num, mots in reste[:len(zones)]:
        if len(mots) != 3 or mots[0] not in zones:
            raise GridError(f"ligne {num} : « région ligne colonne » attendu")
        if mots[0] in chats:
            raise GridError(f"ligne {num} : région {mots[0]} donnée deux fois")
        chats[mots[0]] = (int(mots[1]), int(mots[2]))

    carte = set()
    for i, (num, mots) in enumerate(reste[len(zones):len(zones) + n], start=1):
        if len(mots) != m or any(s not in ".*" for s in mots):
            raise GridError(f"ligne {num} : {m} symboles « . » ou « * » attendus")
        carte |= {(i, j) for j, s in enumerate(mots, start=1) if s == "*"}
    return grid, chats, carte
