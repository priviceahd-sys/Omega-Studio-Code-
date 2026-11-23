ALGO chaines_palindrome_et_cesar
' Manipulation de chaînes avec LONG, MILIEU, MAJ, ANSI et CAR
VAR
    mot, inverse, chiffre : chaîne
    i, n, code_c : entiers
DEBUT
    mot := "RADAR"
    n := LONG(mot)
    inverse := ""

    POUR i := n A 1 PAS -1
        inverse := inverse + MILIEU(mot, i, 1)
    FINPOUR

    AFFICHER "Mot analysé : ", mot, " (longueur = ", n, ")"
    AFFICHER "Mot inversé : ", inverse
    SI MAJ(mot) = MAJ(inverse) ALORS
        AFFICHER "=> C'est un palindrome !"
    SINON
        AFFICHER "=> Ce n'est pas un palindrome."
    FINSI

    ' Chiffrement de César (+3)
    chiffre := ""
    POUR i := 1 A LONG(mot)
        code_c := ((ANSI(MILIEU(mot, i, 1)) - 65 + 3) MOD 26) + 65
        chiffre := chiffre + CAR(code_c)
    FINPOUR
    AFFICHER "Chiffrement César (+3) : ", chiffre
FIN
