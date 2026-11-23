ALGO jeu_plus_ou_moins
' Jeu interactif utilisant ALEA_ENTIER et la boucle ITER ... SORTIRSI ... FINITER
VAR
    secret, essai, tentatives : entiers
DEBUT
    secret := ALEA_ENTIER(1, 50)
    tentatives := 0

    AFFICHER "=== JEU DU NOMBRE MYSTÈRE (entre 1 et 50) ==="
    ITER
        SAISIR "Votre proposition : ", essai
        tentatives := tentatives + 1
        SORTIRSI essai = secret

        SI essai < secret ALORS
            AFFICHER "C'est PLUS grand !"
        SINON
            AFFICHER "C'est PLUS petit !"
        FINSI
    FINITER

    AFFICHER "Bravo ! Trouvé en ", tentatives, " tentative(s) !"
FIN
