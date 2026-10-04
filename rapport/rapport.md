# Projet MLSF – Un solveur SAT pour Meowdoku – Partie I

*Rapport — binôme : Mateo Weill, (à compléter) — octobre 2026*

## Organisation du rendu

```
sat.py                 point d'entrée imposé (Question 6)
solver/
  dimacs.py            lecture / écriture DIMACS                       (Q2)
  dpll.py              algorithmes 1 et 2 de l'énoncé                  (Q2)
  heuristics.py        heuristiques de branchement H0..H7              (Q4)
  dpllh.py             algorithme 3, DPLL_H instrumenté                (Q4, Q5)
  stats.py             compteurs et chronométrage                      (Q5)
  optimized.py         solveur optimisé                                (Q6)
meowdoku/
  grid_io.py           lecture / écriture des grilles et solutions     (Q1, Q3)
  encode.py            grille -> CNF / DIMACS, et décodage             (Q1, Q3)
  verify.py            vérification directe des règles du jeu         (Q1, Q3)
  generate.py          générateur de grilles                           (Q1)
  solve_grid.py        résolution d'une grille                         (Q3)
tools/                 générateurs d'instances, validation, benchmarks
tests/                 tests automatiques (python tests/test_xxx.py)
instances/             instances DIMACS et grilles
bench/                 scripts et résultats des mesures                (Q2, Q5)
rapport/               ce rapport
```

Conventions communes à tout le code :

- **Python 3.12, bibliothèque standard uniquement** : c'est l'environnement de la
  compétition (`python:3.12-slim`), dans lequel on ne peut pas compter sur numpy ou
  autre paquet externe. Les tests passent aussi en 3.13.
- Une **formule CNF** est une liste de clauses ; une **clause** est un `frozenset`
  d'entiers non nuls ; le littéral `k` représente $x_k$ et `-k` représente
  $\neg x_k$ (comme dans DIMACS). La justification est donnée en Question 2.
- Les scripts se lancent depuis la racine du projet (`python meowdoku/encode.py ...`).
  Toute sortie de diagnostic va sur `stderr`, pour que `stdout` reste réservé aux
  résultats (exigence de la Question 6).
- Chaque question fait l'objet d'un commit séparé, ce qui permet de retrouver dans
  l'historique git l'état du code à chaque étape.

Les écarts à l'énoncé et les coquilles relevées sont signalés dans le texte par
**[Écart]** et rassemblés en fin de rapport.

---

## Question 1 – Modélisation de Meowdoku

### 1.1 Format des grilles et choix d'interprétation

Le lecteur (`meowdoku/grid_io.py`) suit le format de la figure 1b. L'énoncé laisse
quelques points ouverts, que l'on a tranchés ainsi :

| Point | Choix | Justification |
|---|---|---|
| Sens de `GRID N M` | N lignes, M colonnes | cohérent avec $x_{i,j}$, $(i,j)\in\{1..N\}\times\{1..M\}$, et avec la figure 2 (« A 3 2 » = ligne 3, colonne 2 : on l'a vérifié sur la carte) |
| Ligne de commentaire | premier mot exactement `c` | une ligne de grille peut commencer par une région nommée `C` (ou `chat`) : « commence par la lettre c » serait ambigu |
| Noms de régions | mots quelconques séparés par des espaces | permet plus de 26 régions (le générateur utilise A…Z, AA, AB…) ; une ligne sans espaces (`ABCBBD`) est aussi acceptée si tous les noms font 1 caractère |
| Coordonnées | à partir de 1 | comme dans la figure 2 |

Le lecteur **vérifie que la grille est licite** : dimensions positives, N lignes de
M cases, régions toutes déclarées, sans doublon et **non vides**. Comme chaque case
reçoit exactement un nom de région, ces contrôles garantissent que les régions
forment une partition de la grille, comme l'exige l'énoncé. Toute anomalie lève une
`GridError` qui indique la ligne fautive.

### 1.2 Variables

On introduit exactement les variables demandées par l'énoncé, une par case :

$$x_{i,j} \text{ vraie} \iff \text{un chat est sur la case } (i,j), \qquad
\text{numéro DIMACS}(x_{i,j}) = (i-1)\cdot M + j \in \{1,\dots,NM\}.$$

La numérotation ligne par ligne est la plus simple à inverser :
$i = \lfloor (v-1)/M \rfloor + 1$ et $j = (v-1) \bmod M + 1$ (fonctions `var` et
`cell_of`). **Aucune variable auxiliaire** n'est ajoutée : on peut ainsi lire la
valuation témoin directement comme une configuration de chats, ce qui est le
décodage demandé.

### 1.3 Clauses

Notons $\mathrm{AMO}(S)$ (*at most one*) l'ensemble de clauses qui impose « au plus
une variable vraie dans $S$ ». On l'encode par l'**encodage binomial** (ou par
paires) : $\mathrm{AMO}(S) = \{\neg a \vee \neg b \mid \{a,b\}\subseteq S\}$, soit
$\binom{|S|}{2}$ clauses binaires. Chaque règle du jeu donne une famille de clauses :

| Règle | Clauses | Nombre (N = M = K = n) |
|---|---|---|
| R1 au plus un chat par ligne $i$ | $\mathrm{AMO}(\{x_{i,1},\dots,x_{i,M}\})$ | $n\binom{n}{2}$ |
| R2 au plus un chat par colonne $j$ | $\mathrm{AMO}(\{x_{1,j},\dots,x_{N,j}\})$ | $n\binom{n}{2}$ |
| R3a au moins un chat par région $R$ | $\bigvee_{(i,j)\in R} x_{i,j}$ | $K$ |
| R3b au plus un chat par région $R$ | $\mathrm{AMO}(\{x_{i,j} \mid (i,j)\in R\})$ | $\sum_R \binom{\lvert R\rvert}{2}$ |
| R4 pas de chats 8-adjacents | $\neg x_{i,j}\vee\neg x_{i',j'}$ pour $\max(\lvert i-i'\rvert,\lvert j-j'\rvert)=1$ | $\le 4n^2$ |

« Exactement un par région » est la conjonction de R3a et R3b. Pour R4, chaque paire
de cases voisines n'est engendrée qu'une seule fois : on ne regarde que les voisins
*après* $(i,j)$ dans l'ordre de lecture, c'est-à-dire droite, bas-gauche, bas et
bas-droite.

**Fusion des doublons.** Certaines clauses sont produites par plusieurs règles. Une
adjacence horizontale (R4) est déjà une clause de R1, une adjacence verticale une
clause de R2, et deux cases d'une même région sur une même ligne donnent la même
clause dans R1 et R3b. On a préféré **engendrer chaque règle littéralement** (le
code se lit comme l'énoncé, donc on peut le vérifier règle par règle), puis
**fusionner les clauses identiques** dans un dictionnaire, qui conserve l'ordre
d'insertion et donc un fichier reproductible. On aurait pu ne produire que les
adjacences diagonales, mais cette optimisation aurait rendu R4 incomplète prise
isolément. Les compteurs par règle sont écrits en commentaire du fichier DIMACS,
pour la traçabilité :

```
c grille 6x6, 6 regions : A B C D E F
c variable x(i,j) = (i-1)*6 + j  (chat en ligne i, colonne j)
c   R1 ligne<=1     : 90 clauses engendrees
c   R2 colonne<=1   : 90 clauses engendrees
c   R3a region>=1   : 6 clauses engendrees
c   R3b region<=1   : 172 clauses engendrees
c   R4 adjacence    : 110 clauses engendrees
c   total apres fusion des doublons : 309 clauses
p cnf 36 309
```

**Taille de la formule.** Avec $N=M=K=n$, la formule a $n^2$ variables et
$O(n^3 + \sum_R |R|^2)$ clauses. Le terme des régions dépend de la forme des
régions : dans le pire cas (une région quasi totale), il vaut $O(n^4)$. Mesures sur
des grilles produites par notre générateur (graine 1) :

| n | variables | clauses engendrées | clauses après fusion |
|---|---|---|---|
| 6 | 36 | 408 | 268 |
| 8 | 64 | 937 | 648 |
| 10 | 100 | 1 878 | 1 360 |
| 12 | 144 | 3 187 | 2 381 |
| 15 | 225 | 6 246 | 4 837 |
| 20 | 400 | 14 364 | 11 580 |
| 30 | 900 | 46 041 | 38 940 |

**Alternative écartée : encodages AMO compacts.** Les encodages *sequential counter*
(Sinz, 2005) ou *ladder* réalisent $\mathrm{AMO}(S)$ avec $O(|S|)$ clauses au lieu de
$O(|S|^2)$, mais ils introduisent des variables auxiliaires. L'énoncé demande une
formule portant sur les seules variables $x_{i,j}$. De plus, pour les tailles
visées ($n \le 30$, moins de 40 000 clauses), l'encodage binomial reste modeste, et
il propage mieux : dès qu'un $x$ devient vrai, une propagation unitaire suffit à
rendre fausses toutes les cases incompatibles, sans passer par des variables
intermédiaires.

**Clauses redondantes optionnelles (`--extra`).** Si $K = N$, on peut ajouter
« au moins un chat par ligne » (R5), et de même R6 pour les colonnes si $K = M$.
Ces clauses sont des **conséquences logiques** des règles. R3 impose exactement $K$
chats, puisque les régions sont disjointes et contiennent un chat chacune. R1
impose au plus un chat par ligne. Si $K=N$, les $N$ lignes en contiennent donc
exactement un chacune, par le principe des tiroirs. Ces clauses ne changent pas
l'ensemble des solutions, mais elles peuvent créer des clauses unitaires plus tôt
dans DPLL. Elles sont désactivées par défaut, pour rester fidèle à l'énoncé, et
leur effet sera mesuré en Question 5.

### 1.4 Validation de l'encodage

On veut établir que, pour toute valuation $v$, on a $v \models \mathrm{CNF}(G)$ si
et seulement si les cases où $v(x_{i,j})=1$ forment une solution de $G$.

Pour cela, `meowdoku/verify.py` implémente les quatre règles **directement**,
sans logique propositionnelle (simples comptages et tests de distance). On dispose
ainsi d'un oracle dont la correction se lit immédiatement sur le code. Les tests
(`tests/test_meowdoku.py`) vérifient alors :

1. la solution de la figure 2 satisfait la CNF de la grille de la figure 1, et
   déplacer un seul chat la fait échouer ;
2. **équivalence exhaustive** : sur 75 grilles aléatoires de tailles 2×2 à 4×4 (et
   2×6, 3×4, 4×3), avec $K$ aléatoire, et avec ou sans `--extra`, on parcourt les
   $2^{NM}$ valuations (jusqu'à 65 536 par grille), et on vérifie que la CNF est
   satisfaite **exactement** quand l'oracle déclare la configuration valide. Les
   grilles de test ont des germes quelconques et ne sont donc pas toujours
   solubles : 65 en ont au moins une solution, 10 n'en ont aucune. Les deux cas
   sont donc couverts. Ce test prouve, sur ces grilles, la **correction** (tout
   modèle est une solution) et la **complétude** (toute solution est un modèle) de
   l'encodage, y compris avec les clauses redondantes ;
3. les fichiers mal formés (région vide, non déclarée, ligne trop courte, etc.)
   sont refusés.

### 1.5 Générateur de grilles

`meowdoku/generate.py` produit des grilles **ayant au moins une solution par
construction**, par la méthode de la *solution plantée* :

1. **Placement des chats.** On tire $K$ lignes distinctes (toutes si $K=N$),
   triées, puis on choisit une colonne par ligne par **retour arrière en ordre
   aléatoire**. Deux contraintes s'appliquent : la colonne n'est pas déjà
   utilisée, et si la ligne précédente est adjacente, l'écart de colonne est au
   moins 2 (sinon contact diagonal). Deux chats sur des lignes non consécutives ne
   peuvent pas se toucher, donc ces contraintes suffisent à respecter R1, R2 et R4.
2. **Croissance des régions.** Chaque chat devient le germe d'une région. Toutes
   les régions grandissent simultanément selon un modèle de croissance d'Eden : on
   tire uniformément un couple (région, case libre 4-voisine de la région) dans la
   « frontière », et on rattache la case à la région, jusqu'à ce que toutes les
   cases soient prises.
3. **Nommage.** Les régions sont nommées A, B, C… dans l'ordre de lecture de leur
   première case, comme dans la figure 1.

*Correction.* Chaque région contient exactement un germe, et les germes respectent
R1, R2 et R4 : la configuration des germes est donc une solution. De plus, chaque
case est rattachée à exactement une région et chaque région contient son germe :
les régions forment une partition. Elles sont aussi **connexes**, comme dans le
jeu réel, car une case n'est rattachée à une région que si elle touche une case de
cette région. Tout cela est vérifié par les tests sur 100 grilles de 1×1 à 20×20.

*Cas traités.* Le cas général $N\times M$ avec $K \le \min(N,M)$ est accepté
(`python meowdoku/generate.py 5 7 4`). Le cas usuel $N=M=K$ s'obtient avec
`python meowdoku/generate.py 8`. Pour $N=M=K \in \{2,3\}$, aucune configuration
valide n'existe. Le retour arrière le prouve par recherche exhaustive et le
générateur l'indique. *Reproductibilité* : l'option `--seed` fixe la graine, qui
est aussi notée en commentaire dans la grille produite.

*Limite.* Une grille générée a **au moins** une solution, comme l'exige l'énoncé,
mais pas forcément une seule. Les grilles du jeu réel ont une solution unique. Une
option de génération à solution unique, qui nécessite le solveur, est ajoutée en
Question 3.

*Complexité.* La croissance coûte $O(NM)$ en espérance, car chaque case entre au
plus 4 fois dans la frontière. Le retour arrière est exponentiel dans le pire cas,
mais il trouve une solution quasi immédiatement pour $n \ge 4$, car les contraintes
sont peu serrées : une grille 30×30 est produite en quelques millisecondes.

**Commandes.**

```
python meowdoku/encode.py instances/meowdoku/grille1.txt              # -> grille1.cnf
python meowdoku/encode.py grille.txt -o sortie.cnf --extra
python meowdoku/generate.py 8 --seed 1 -o grille8.txt
python meowdoku/generate.py 10 --count 20 --dir instances/meowdoku/gen --seed 100 --cnf
python tests/test_meowdoku.py
```

---

## Usage des assistants IA

Le projet a été réalisé avec l'aide de Claude (Anthropic) dans l'éditeur, via
l'extension Claude Code. Le principe a été le suivant : l'assistant propose du code
et des justifications, question par question ; chaque choix est relu, testé et
documenté dans ce rapport avant d'être intégré au dépôt (un commit par question).
Les points où l'énoncé laissait une marge d'interprétation sont signalés
explicitement. Les tests ont été conçus pour ne pas dépendre de la confiance
accordée au code produit : ils comparent avec des oracles indépendants (force
brute, vérificateur direct des règles du jeu).

- **Q1** : proposition de l'encodage et du générateur par l'assistant ; la
  validation repose sur le test d'équivalence exhaustive (§1.4), qui ne dépend
  d'aucune hypothèse sur le code d'encodage.
