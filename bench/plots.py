"""Figures du rapport à partir des CSV de bench/results/ (outil de développement).

    python bench/plots.py q2        (nécessite matplotlib : pip install matplotlib)

Figures écrites dans rapport/figures/. Conventions : une seule échelle par
axe, palette catégorielle dans un ordre fixe (même couleur = même solveur
ou même statut d'une figure à l'autre), grille discrète, légende dès deux
séries.
"""

import csv
import os
import statistics
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RESULTS = os.path.join(RACINE, "bench", "results")
FIGURES = os.path.join(RACINE, "rapport", "figures")

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
TEXTE, TEXTE2, GRILLE = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9,
    "axes.edgecolor": GRILLE, "axes.labelcolor": TEXTE2, "axes.titlesize": 10,
    "axes.titlecolor": TEXTE, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRILLE, "grid.linewidth": 0.6,
    "xtick.color": TEXTE2, "ytick.color": TEXTE2, "legend.frameon": False,
    "lines.linewidth": 2, "lines.markersize": 5,
})


def lire(nom):
    with open(os.path.join(RESULTS, nom), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sauver(fig, nom):
    os.makedirs(FIGURES, exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, nom))
    plt.close(fig)
    print("->", os.path.join(FIGURES, nom), file=sys.stderr)


def temps(l, delai=60.0):
    """Temps d'une ligne ; un délai dépassé compte pour le délai (borne basse)."""
    return float(l["temps"]) if l["statut"] in ("SAT", "UNSAT") else delai


def q2():
    # --- transition de phase
    L = lire("q2_phase.csv")
    par = defaultdict(list)
    for l in L:
        par[float(l["ratio"])].append(l)
    rs = sorted(par)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3))
    a1.plot(rs, [100 * sum(l["statut"] == "SAT" for l in par[r]) / len(par[r]) for r in rs],
            marker="o", color=SERIES[0])
    a1.set(xlabel="ratio clauses / variables (m/n)", ylabel="% de formules SAT",
           title="Proportion satisfiable (n = 30)")
    a1.axvline(4.26, color=TEXTE2, lw=0.8, ls="--")
    a2.plot(rs, [statistics.median(temps(l) for l in par[r]) for r in rs],
            marker="o", color=SERIES[0], label="médiane")
    a2.plot(rs, [max(temps(l) for l in par[r]) for r in rs],
            marker="o", color=SERIES[1], label="maximum")
    a2.set(xlabel="ratio clauses / variables (m/n)", ylabel="temps (s)",
           title="Temps de résolution, algorithme 2")
    a2.axvline(4.26, color=TEXTE2, lw=0.8, ls="--")
    a2.legend()
    sauver(fig, "q2_phase.png")

    # --- croissance avec n, par statut et par algorithme
    L = lire("q2_taille.csv")
    # le statut d'une formule est celui trouvé par l'un des deux algorithmes
    statut = {}
    for l in L:
        if l["statut"] in ("SAT", "UNSAT"):
            statut[(l["n"], l["i"])] = l["statut"]
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    k = 0
    for st in ("SAT", "UNSAT"):
        for s, style in (("dpll1", "--"), ("dpll2", "-")):
            pts = defaultdict(list)
            for l in L:
                if l["solveur"] == s and statut.get((l["n"], l["i"])) == st:
                    pts[int(l["n"])].append(temps(l))
            ns = sorted(pts)
            ax.plot(ns, [statistics.median(pts[n]) for n in ns], style, marker="o",
                    color=SERIES[0 if st == "SAT" else 1],
                    label=f"{st}, algorithme {s[-1]}")
            k += 1
    ax.set_yscale("log")
    ax.set(xlabel="nombre de variables n (m = 4,26 n)", ylabel="temps médian (s, échelle log)",
           title="3-SAT aléatoire au seuil : croissance exponentielle")
    ax.legend()
    sauver(fig, "q2_taille.png")


if __name__ == "__main__":
    {"q2": q2}[sys.argv[1] if len(sys.argv) > 1 else "q2"]()
