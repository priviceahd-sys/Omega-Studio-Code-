ALGO tri_bulles_et_dichotomie
' Tri à bulles d'un tableau d'entiers suivi d'une recherche dichotomique
CONST
    TAILLE = 8
VAR
    t[8] : tableau d'entiers
    i, cible, pos : entiers
DEBUT
    t[1] := 42
    t[2] := 15
    t[3] := 8
    t[4] := 91
    t[5] := 23
    t[6] := 4
    t[7] := 67
    t[8] := 19

    AFFICHER "Tableau initial :"
    afficher_tableau(t, TAILLE)

    trier_bulles(t, TAILLE)

    AFFICHER "Tableau trié par ordre croissant :"
    afficher_tableau(t, TAILLE)

    cible := 23
    pos := recherche_dichotomique(t, TAILLE, cible)
    SI pos > 0 ALORS
        AFFICHER "Valeur ", cible, " trouvée à l'indice ", pos
    SINON
        AFFICHER "Valeur ", cible, " absente du tableau."
    FINSI
FIN

PROCEDURE afficher_tableau(e tab[] : tableau d'entiers ; e n : entier)
VAR
    k : entier
DEBUT
    POUR k := 1 A n
        AFFICHER "[", tab[k], "] " &
    FINPOUR
    A_LA_LIGNE
FIN

PROCEDURE trier_bulles(es tab[] : tableau d'entiers ; e n : entier)
VAR
    i, j, tmp : entiers
DEBUT
    POUR i := 1 A n - 1
        POUR j := 1 A n - i
            SI tab[j] > tab[j + 1] ALORS
                tmp := tab[j]
                tab[j] := tab[j + 1]
                tab[j + 1] := tmp
            FINSI
        FINPOUR
    FINPOUR
FIN

FONCTION recherche_dichotomique(e tab[] : tableau d'entiers ; e n, val : entiers) : entier
VAR
    gauche_i, droite_i, milieu_i, trouve_pos : entiers
DEBUT
    gauche_i := 1
    droite_i := n
    trouve_pos := 0
    TANT QUE gauche_i <= droite_i ET trouve_pos = 0
        milieu_i := (gauche_i + droite_i) DIV 2
        SI tab[milieu_i] = val ALORS
            trouve_pos := milieu_i
        SINON SI tab[milieu_i] < val ALORS
            gauche_i := milieu_i + 1
        SINON
            droite_i := milieu_i - 1
        FINSI
    FINTQ
    VALRET := trouve_pos
FIN
