ALGO ecran_couleurs_vga
' Démonstration des instructions historiques COULEUR, EFFACE_ECRAN et CURSEUR d'Alg_32
VAR
    ligne_cadre : chaîne
DEBUT
    EFFACE_ECRAN
    COULEUR 14, 1
    ligne_cadre := REPETECAR(44, 61)

    CURSEUR 2, 10
    AFFICHER ligne_cadre
    CURSEUR 3, 10
    AFFICHER "   MODE ÉCRAN COULEUR ALG_32 (Jaune/Bleu)   "
    CURSEUR 4, 10
    AFFICHER ligne_cadre
    CURSEUR 6, 10
    AFFICHER "Position courante : L=", LIGNE(), " C=", COLONNE()
FIN
