ALGO bienvenue_omega_studio
' ============================================================
' Bienvenue dans Omega Studio Code (évolution moderne d'Alg_32)
' Appuyez sur F5 pour exécuter ou F10 pour le mode Pas-à-Pas !
' ============================================================
CONST
    ANNEE_COURANTE = 2026
VAR
    prenom : chaîne(40)
    somme, i : entiers
DEBUT
    AFFICHER "+----------------------------------------------+"
    AFFICHER "|   Bienvenue dans OMEGA STUDIO CODE v2.0 !    |"
    AFFICHER "+----------------------------------------------+"
    AFFICHER "Date système : ", DATESYST(), " à ", HEURESYST()
    A_LA_LIGNE

    prenom := "Étudiant Omarchy"
    AFFICHER "Bonjour ", MAJ(prenom), " !"

    somme := 0
    POUR i := 1 A 10
        somme := somme + i
    FINPOUR

    AFFICHER "La somme des entiers de 1 à 10 vaut : ", somme
    AFFICHER "Racine carrée de 144 = ", RAC2(144)
FIN
