ALGO structures_et_types_utilisateurs
' Utilisation de TYPE ... FIN TYPE et STRUCTURE ... FINSTRUCTURE (norme Alg_32)
TYPE Adresse
    rue : chaîne(50)
    ville : chaîne(30)
FIN TYPE

VAR
    adr_campus : Adresse
    STRUCTURE etudiant
        matricule : entier
        nom : chaîne(30)
        moyenne : réel
        admis : booléen
    FINSTRUCTURE
DEBUT
    adr_campus.rue := "Avenue de l'Université"
    adr_campus.ville := "Cotonou / Kandi"

    etudiant.matricule := 202601
    etudiant.nom := "Ahouansou"
    etudiant.moyenne := 15.75
    etudiant.admis := etudiant.moyenne >= 10.0

    AFFICHER "Étudiant #", etudiant.matricule, " : ", MAJ(etudiant.nom)
    AFFICHER "Campus   : ", adr_campus.rue, " — ", adr_campus.ville
    AFFICHER "Moyenne  : ", etudiant.moyenne, " / 20"
    AFFICHER "Admis    : ", etudiant.admis
FIN
