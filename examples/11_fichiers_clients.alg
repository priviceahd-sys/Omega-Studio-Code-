ALGO gestion_fichier_clients
' Gestion d'un fichier séquentiel Alg_32 (OUVRIR, ECRIRE, LIRE, FF, FERMER)
FICHIER f_clients EN ORGANISATION SEQUENTIELLE
ENREGISTREMENT enr_client
    code_cli : entier
    nom_cli : chaîne(30)
    solde_cli : réel
FINENREGISTREMENT

DEBUT
    ' 1. Écriture d'enregistrements dans le fichier
    OUVRIR f_clients EN écriture
    code_cli := 101
    nom_cli := "Soglo Nadia"
    solde_cli := 125000.0
    ECRIRE enr_client

    code_cli := 102
    nom_cli := "Kouassi Marc"
    solde_cli := 84500.5
    ECRIRE enr_client
    FERMER f_clients

    ' 2. Relecture séquentielle jusqu'à Fin de Fichier FF()
    AFFICHER "=== Liste des clients enregistrés ==="
    OUVRIR f_clients EN lecture
    LIRE enr_client
    TANT QUE NON FF(f_clients)
        AFFICHER "#", code_cli, " - ", nom_cli, " | Solde : ", solde_cli
        LIRE enr_client
    FINTQ
    FERMER f_clients
FIN
