ALGO base_sql_etudiants
' Démonstration des blocs EXEC SQL ... FIN EXEC d'Alg_32 (propulsé par SQLite3 intégré !)
VAR
    seuil : réel
    nb_admis : entier
    moy_promo : réel
DEBUT
    seuil := 12.0

    EXEC SQL
        START DATABASE :memory:
    FIN EXEC

    EXEC SQL
        CREATE TABLE etudiants (
            id INTEGER PRIMARY KEY,
            nom TEXT,
            filiere TEXT,
            note REAL
        )
    FIN EXEC

    EXEC SQL
        INSERT INTO etudiants VALUES (1, 'Adéoti Clarisse', 'Génie Logiciel', 16.5)
    FIN EXEC
    EXEC SQL
        INSERT INTO etudiants VALUES (2, 'Boni Rachid', 'Réseaux', 11.0)
    FIN EXEC
    EXEC SQL
        INSERT INTO etudiants VALUES (3, 'Dossou Kévin', 'IA & Données', 14.8)
    FIN EXEC

    AFFICHER "=== Étudiants ayant une note >= ", seuil, " ==="
    EXEC SQL
        SELECT id, nom, filiere, note FROM etudiants WHERE note >= :seuil ORDER BY note DESC
    FIN EXEC

    EXEC SQL
        SELECT COUNT(*), AVG(note) INTO :nb_admis, :moy_promo FROM etudiants WHERE note >= 10
    FIN EXEC

    A_LA_LIGNE
    AFFICHER "Nombre d'étudiants >= 10 : ", nb_admis
    AFFICHER "Moyenne générale         : ", ARRONDI(moy_promo * 100) / 100

    EXEC SQL
        STOP DATABASE
    FIN EXEC
FIN
