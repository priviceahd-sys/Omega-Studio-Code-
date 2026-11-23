ALGO recursivite_factorielle_fibonacci
' Démonstration des fonctions récursives et de la pile d'appels en Pas-à-Pas (F11)
VAR
    k : entier
DEBUT
    AFFICHER "=== Factorielles (0! à 7!) ==="
    POUR k := 0 A 7
        AFFICHER k, "! = ", factorielle(k)
    FINPOUR

    A_LA_LIGNE
    AFFICHER "=== Suite de Fibonacci (F0 à F10) ==="
    POUR k := 0 A 10
        AFFICHER fibonacci(k), " " &
    FINPOUR
    A_LA_LIGNE
FIN

FONCTION factorielle(e n : entier) : entier
DEBUT
    SI n <= 1 ALORS
        VALRET := 1
    SINON
        VALRET := n * factorielle(n - 1)
    FINSI
FIN

FONCTION fibonacci(e n : entier) : entier
DEBUT
    SI n <= 1 ALORS
        DELIVRE(n)
    SINON
        DELIVRE(fibonacci(n - 1) + fibonacci(n - 2))
    FINSI
FIN
