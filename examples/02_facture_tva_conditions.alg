ALGO facturation_tva_remise
' Calcul d'une facture TTC avec remise progressive selon la catégorie
CONST
    TAUX_TVA_REDUIT = 0.055
    TAUX_TVA_NORMAL = 0.20
VAR
    montant_ht, taux_remise, remise, net_ht, tva, montant_ttc : réels
    categorie : entier
    code_tva : chaîne(1)
DEBUT
    SAISIR "Montant HT de la commande : ", montant_ht
    SAISIR "Catégorie client (1, 2 ou 3) : ", categorie
    SAISIR "Code TVA (A=5.5%, B=20%) : ", code_tva

    SELON categorie
        CAS 1 :
            taux_remise := 0.05
        CAS 2 :
            taux_remise := 0.10
        CAS 3 :
            taux_remise := 0.18
        CAS SINON :
            taux_remise := 0.0
    FINSELON

    remise := montant_ht * taux_remise
    net_ht := montant_ht - remise

    SI MAJ(code_tva) = "A" ALORS
        tva := net_ht * TAUX_TVA_REDUIT
    SINON
        tva := net_ht * TAUX_TVA_NORMAL
    FINSI

    montant_ttc := ARRONDI((net_ht + tva) * 100) / 100

    A_LA_LIGNE
    AFFICHER "--- RÉCAPITULATIF FACTURE ---"
    AFFICHER "Montant brut HT : ", montant_ht
    AFFICHER "Remise accordée : ", remise
    AFFICHER "Net HT          : ", net_ht
    AFFICHER "TVA             : ", tva
    AFFICHER "Total TTC       : ", montant_ttc
    IMPRIMER "Facture TTC = ", montant_ttc
FIN
