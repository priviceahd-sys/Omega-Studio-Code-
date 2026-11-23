ALGO table_multiplication
' Illustration des boucles REPETER...JUSQU'A et POUR...FINPOUR
VAR
    n, i, produit : entiers
DEBUT
    REPETER
        SAISIR "Entrez un nombre entier entre 1 et 20 : ", n
    JUSQU'A n >= 1 ET n <= 20

    A_LA_LIGNE
    AFFICHER "=== Table de multiplication de ", n, " ==="
    POUR i := 1 A 12
        produit := n * i
        AFFICHER n, " x ", i, TAB(12), "= ", produit
    FINPOUR
FIN
