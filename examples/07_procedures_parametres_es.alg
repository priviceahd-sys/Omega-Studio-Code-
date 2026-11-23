ALGO procedures_parametres_es
' Passage de paramètres en Entrée (e), Sortie (s) et Entrée/Sortie (es)
VAR
    x, y, quotient, reste : entiers
DEBUT
    x := 47
    y := 6
    AFFICHER "Avant échange : x = ", x, ", y = ", y
    echanger(x, y)
    AFFICHER "Après échange : x = ", x, ", y = ", y

    division_euclidienne(47, 6, quotient, reste)
    AFFICHER "47 divisé par 6 => quotient = ", quotient, ", reste = ", reste
FIN

PROCEDURE echanger(es a, b : entiers)
VAR
    temp : entier
DEBUT
    temp := a
    a := b
    b := temp
FIN

PROCEDURE division_euclidienne(e dividende, diviseur : entiers ; s q, r : entiers)
DEBUT
    q := dividende DIV diviseur
    r := dividende MOD diviseur
FIN
