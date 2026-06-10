import json
import os
from datetime import datetime, date

# ─────────────────────────────────────────────────────────────────────────────
# scraper.py — FastPharma
#
# À Ouagadougou, les pharmacies tournent en 4 groupes (I, II, III, IV).
# Chaque groupe est de garde une semaine sur 4.
# On calcule le groupe actif selon une date de référence connue,
# puis on génère le JSON avec les pharmacies du bon groupe.
#
# Source des groupes : infossante.net (observé manuellement)
# Le groupe est de garde du samedi au vendredi suivant.
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_FILE = "pharmacies_garde_ouaga.json"

# ── Date de référence ────────────────────────────────────────────────────────
# Le 07/06/2026 (samedi), le groupe en garde était le groupe actuel affiché.
# D'après infossante.net le 10/06/2026 :
# Pharmacies de garde = Poste, Savane, Concorde, Indépendance, Ecoles,
# Baraka, Djabal, Wend-Denda, Naab-Raga, Kamin, Zoungrana, St Lazare,
# Sacré Coeur, Jeunesse, Djimbia, Dunia, Téranga, Naaba Koom, Ste trinité,
# St Julien, Yennenga, Coura, Fraternité, Galiam, Santé-vitalité...
# → Ce sont les pharmacies de ZONE 3 + ZONE 2 du programme ONPBF
# On identifie ce groupe comme GROUPE II (selon le calendrier ONPBF)
#
# Semaine de référence : du 07/06/2026 au 13/06/2026 = GROUPE II
# Rotation : GI → GII → GIII → GIV → GI → ...
# Durée d'un cycle : 7 jours par groupe

DATE_REFERENCE = date(2026, 6, 7)   # Samedi 7 juin 2026
GROUPE_REFERENCE = 2                 # Groupe II était de garde ce jour

# ── Pharmacies par groupe ────────────────────────────────────────────────────
# Basé sur les données observées sur infossante.net et pharmacies_data.dart
# Chaque groupe = ~25 pharmacies

GROUPES = {
    1: [
        {"nom": "AGORA ROOD WOOKO",     "telephone": "25308890", "adresse": "Marché Rood Wooko, face à DIACFA Librairie",                   "lat": 12.3695,  "lng": -1.52255},
        {"nom": "AMARO",                "telephone": "25343329", "adresse": "Av. du Kadiogo Gounghin Petit Paris",                          "lat": 12.358,   "lng": -1.518},
        {"nom": "SAMANDIN SARL",        "telephone": "50355378", "adresse": "Av. du MOGHO NAABA non loin de l'église Jean XXIII",           "lat": 12.362,   "lng": -1.529},
        {"nom": "SANGOULE LAMIZANA",    "telephone": "25411300", "adresse": "Av. Yennega à côté de Marina Market centre Ville",            "lat": 12.366,   "lng": -1.533},
        {"nom": "SIGRI SARL",           "telephone": "25346422", "adresse": "Av. du Conseil de l'Entente Gounghin",                         "lat": 12.358,   "lng": -1.518},
        {"nom": "TALBA",                "telephone": "25361276", "adresse": "Av. Charles De Gaulle, face au Scolasticat, Zogona",           "lat": 12.38,    "lng": -1.543},
        {"nom": "TANKO",                "telephone": "25351557", "adresse": "Face au CMA Paul VI sur la route de Kamboinsé",               "lat": 12.402,   "lng": -1.563},
        {"nom": "TI-BANGRE",            "telephone": "25454595", "adresse": "Route de Bobo à l'entrée du pont de Boulmiougou",             "lat": 12.342,   "lng": -1.598},
        {"nom": "UNIVERS",              "telephone": "25419965", "adresse": "Voie principale Saaba, à 500m de la Préfecture",              "lat": 12.36,    "lng": -1.478},
        {"nom": "VIIM",                 "telephone": "78650658", "adresse": "100 mètres du Centre Médical de Nagrin",                       "lat": 12.375,   "lng": -1.488},
        {"nom": "WATI",                 "telephone": "25385292", "adresse": "Cissin à 200m de l'école de Santé St Edwige",                 "lat": 12.356,   "lng": -1.552},
        {"nom": "YOBI",                 "telephone": "25311630", "adresse": "A 200m de la Gendarmerie de Paspanga",                        "lat": 12.37,    "lng": -1.54},
        {"nom": "SCHIFEYI",             "telephone": "25402742", "adresse": "Non loin du blvd de la Jeunesse vers le foyer du sapeur",     "lat": 12.37,    "lng": -1.54},
        {"nom": "SIG-NOGHIN",           "telephone": "25508515", "adresse": "Av. Naaba Ziiwendé 150m du rond point de Rimkieta",           "lat": 12.396,   "lng": -1.555},
        {"nom": "SOMKETA",              "telephone": "78049669", "adresse": "Route de Kamboinsin, 100m avant la BAC de Kamboisin",         "lat": 12.435,   "lng": -1.51},
        {"nom": "ZIDOU",                "telephone": "78415644", "adresse": "Balkuy, en face de l'immeuble Yelhi",                         "lat": 12.348,   "lng": -1.518},
        {"nom": "ADADOUA",              "telephone": "63883939", "adresse": "Entre le CMA de Pissy et le Centre Médical Source de Vie",    "lat": 12.353,   "lng": -1.571},
        {"nom": "VINCENT DE PAUL",      "telephone": "",         "adresse": "Face à l'alimentation SOMDARA, à 150m du lycée Bangre Yiguia","lat": 12.37,    "lng": -1.52},
        {"nom": "ROOD WOOKO",           "telephone": "25308890", "adresse": "Centre ville, Marché Rood Woko",                              "lat": 12.365,   "lng": -1.534},
        {"nom": "DE LA GARE",           "telephone": "25316206", "adresse": "Secteur Koulouba",                                            "lat": 12.3698,  "lng": -1.52286},
        {"nom": "DU SAHEL",             "telephone": "25318195", "adresse": "Centre ville",                                                "lat": 12.366,   "lng": -1.533},
        {"nom": "KOULOUBA",             "telephone": "25311918", "adresse": "Koulouba centre ville",                                       "lat": 12.365,   "lng": -1.535},
        {"nom": "VIDAL",                "telephone": "25315288", "adresse": "Centre ville",                                                "lat": 12.366,   "lng": -1.532},
        {"nom": "DU CENTRE",            "telephone": "25311660", "adresse": "Centre ville",                                                "lat": 12.366,   "lng": -1.533},
        {"nom": "NOUVELLE",             "telephone": "25346134", "adresse": "200m côté est de Ciné BURKINA",                               "lat": 12.3658,  "lng": -1.5341},
    ],
    2: [
        {"nom": "de la Poste",          "telephone": "25318424", "adresse": "Koulouba",                                                    "lat": 12.3698,  "lng": -1.52286},
        {"nom": "Savane",               "telephone": "70850161", "adresse": "A 500m de l'école des Douanes coté Nord",                    "lat": 12.3775,  "lng": -1.52108},
        {"nom": "Concorde",             "telephone": "25312949", "adresse": "Av. Kwame N'Krumah non loin de Zabre Daaga",                 "lat": 12.3658,  "lng": -1.5188},
        {"nom": "Indépendance",         "telephone": "25376871", "adresse": "370 Avenue Eli SARE, à 500m de EAU Sahel Ouaga 2000",        "lat": 12.3706,  "lng": -1.51602},
        {"nom": "Ecoles",               "telephone": "25315232", "adresse": "Paspanga, Rue des écoles",                                   "lat": 12.3818,  "lng": -1.51633},
        {"nom": "Baraka",               "telephone": "",         "adresse": "Côté Est de la Cours du Ouidi Naaba",                        "lat": 12.3787,  "lng": -1.5398},
        {"nom": "Djabal",               "telephone": "25300576", "adresse": "Kamsonghin Av Ouezzin Coulibaly",                            "lat": 12.3564,  "lng": -1.52331},
        {"nom": "Wend-Denda",           "telephone": "",         "adresse": "Sect. 9 quartier Ouidi, Avenue Yatenga",                     "lat": 12.377,   "lng": -1.54407},
        {"nom": "Naab-Raga",            "telephone": "70143977", "adresse": "Samandin, Avenue Oumarou KANAZOE",                           "lat": 12.3525,  "lng": -1.53168},
        {"nom": "Kamin",                "telephone": "25343028", "adresse": "Sect. 06 Gounghin, côté Est du marché de Gounghin",          "lat": 12.3576,  "lng": -1.54559},
        {"nom": "Zoungrana",            "telephone": "25409875", "adresse": "Sect. 17 Tanghin rue 23/125",                                "lat": 12.3979,  "lng": -1.5295},
        {"nom": "St Lazare",            "telephone": "25368648", "adresse": "1200 Logements, rue 14.54",                                  "lat": 12.3686,  "lng": -1.49978},
        {"nom": "Sacré Coeur",          "telephone": "25346060", "adresse": "Avenue Simon Compaoré, à 500m du lycée Miste de Gounghin",   "lat": 12.3511,  "lng": -1.54624},
        {"nom": "de la Jeunesse",       "telephone": "25343504", "adresse": "Hamdalaye, rue 10.61",                                       "lat": 12.3721,  "lng": -1.55783},
        {"nom": "Djimbia",              "telephone": "25357765", "adresse": "Tanghin, 400m après le rond-point du Rotary",                "lat": 12.4014,  "lng": -1.51434},
        {"nom": "Dunia",                "telephone": "25362051", "adresse": "1200 Logements, Avenue des Arts",                            "lat": 12.3593,  "lng": -1.49523},
        {"nom": "Téranga",              "telephone": "25360970", "adresse": "Zogona, 13 avenue Babanguida",                               "lat": 12.3818,  "lng": -1.49342},
        {"nom": "Naaba Koom",           "telephone": "25483334", "adresse": "200m de la Clinique Notre-Dame-de-la-Paix",                  "lat": 12.3992,  "lng": -1.50343},
        {"nom": "Ste trinité",          "telephone": "25412646", "adresse": "Wemtenga, rue 29.13",                                       "lat": 12.3685,  "lng": -1.48846},
        {"nom": "St Julien",            "telephone": "25380610", "adresse": "A 100m du rond-point de la Patte-d'oie",                    "lat": 12.3347,  "lng": -1.52616},
        {"nom": "Yennenga",             "telephone": "25370337", "adresse": "Blvd Tansoba face à la mairie de BOGODOGO",                  "lat": 12.3513,  "lng": -1.48818},
        {"nom": "Coura",                "telephone": "25388390", "adresse": "200m Côté ouest du rond-point des Droits Humains",           "lat": 12.3273,  "lng": -1.51927},
        {"nom": "la Fraternité",        "telephone": "",         "adresse": "100m de ENAREF, Coté ECOBANK",                               "lat": 12.3901,  "lng": -1.48162},
        {"nom": "Galiam",               "telephone": "",         "adresse": "Tampouy, route de la mairie de Sig-Nonghin",                  "lat": 12.3997,  "lng": -1.56614},
        {"nom": "Santé-vitalité",       "telephone": "25409413", "adresse": "Rue WARABA, 500m après la cité de l'ASECNA",                 "lat": 12.368,   "lng": -1.508},
    ],
    3: [
        {"nom": "ARCHANGES",            "telephone": "79200183", "adresse": "Pissy, Face à la station OTAM",                              "lat": 12.362,   "lng": -1.531},
        {"nom": "BANG-POORE",           "telephone": "71500828", "adresse": "Sect. 17 Tanghin devant Arb-Yaar",                           "lat": 12.392,   "lng": -1.543},
        {"nom": "BAO-WENDSOM",          "telephone": "25414499", "adresse": "Tampouy sur le nouveau goudron",                             "lat": 12.405,   "lng": -1.543},
        {"nom": "BARKWENDE",            "telephone": "25408590", "adresse": "Arrdt 8, Sect 35, face à la cité de Rimkièta",               "lat": 12.396,   "lng": -1.555},
        {"nom": "BEATITUDES",           "telephone": "25374711", "adresse": "Blvd. France-Afrique Ouaga 2000 en face de la cite Azimo",   "lat": 12.335,   "lng": -1.535},
        {"nom": "BENAIA",               "telephone": "25372830", "adresse": "Katre-yaare ex secteur 29",                                  "lat": 12.362,   "lng": -1.518},
        {"nom": "CAMILLE",              "telephone": "25366127", "adresse": "Av. Charles De Gaule - Hôtel des finances de Dassasgho",    "lat": 12.375,   "lng": -1.515},
        {"nom": "COMPTE SPECIAL MARE",  "telephone": "25341128", "adresse": "Gounghin, non loin du Stade du 4 août",                      "lat": 12.358,   "lng": -1.518},
        {"nom": "CRYSTAL",              "telephone": "79370146", "adresse": "Face à la nouvelle Mairie de l'Arrdt 9",                    "lat": 12.348,   "lng": -1.562},
        {"nom": "DES APOTRES",          "telephone": "25380382", "adresse": "Arrdt 12, Sect 52 non loin de Notre Dame des Apôtres",      "lat": 12.332,   "lng": -1.545},
        {"nom": "DESA SARL",            "telephone": "25475050", "adresse": "Tanghin, non loin de Hôtel Ricardo",                        "lat": 12.392,   "lng": -1.543},
        {"nom": "DIABY",                "telephone": "60171305", "adresse": "Face au Festival des Glaces à Koulouba",                     "lat": 12.365,   "lng": -1.535},
        {"nom": "EL-WANOGO SARL",       "telephone": "25407022", "adresse": "A côté du Marché de Wayalghin",                             "lat": 12.372,   "lng": -1.498},
        {"nom": "ELITE",                "telephone": "25419177", "adresse": "Avenue Yennega route de Yagma",                              "lat": 12.384,   "lng": -1.531},
        {"nom": "HOSANNA",              "telephone": "25412648", "adresse": "Route de Fada en face du Lycée Naba Yemdé",                 "lat": 12.37,    "lng": -1.498},
        {"nom": "KATRA",                "telephone": "25372013", "adresse": "Située à Kalgondé après la gare RAHIMO",                    "lat": 12.356,   "lng": -1.509},
        {"nom": "KOSSODO",              "telephone": "25356304", "adresse": "En face de l'abattoir de Kossodo",                          "lat": 12.418,   "lng": -1.498},
        {"nom": "LANZANE",              "telephone": "70271078", "adresse": "En face de l'Auto-Ecole Magnificat à la Zone Une",          "lat": 12.37,    "lng": -1.52},
        {"nom": "LES CHAMPIONS",        "telephone": "76515822", "adresse": "A environ 100 mètres du marché de 14 Yaar",                  "lat": 12.383,   "lng": -1.538},
        {"nom": "LINA",                 "telephone": "58846470", "adresse": "Avenue Kwamé N'krumah non loin de la Banque Atlantique",    "lat": 12.366,   "lng": -1.532},
        {"nom": "MAGNIFICAT",           "telephone": "25412990", "adresse": "Sect.50 Karpala",                                           "lat": 12.34,    "lng": -1.56},
        {"nom": "MINITCHE",             "telephone": "79798771", "adresse": "Belleville non loin du rond-point de la transition",        "lat": 12.358,   "lng": -1.546},
        {"nom": "PELEGA",               "telephone": "25350501", "adresse": "Arrdt n°3, Av du Yatenga",                                  "lat": 12.375,   "lng": -1.535},
        {"nom": "SAINT BERNARD",        "telephone": "25451482", "adresse": "Face à la trame d'accueil Ouaga 2000",                      "lat": 12.335,   "lng": -1.535},
        {"nom": "SAINT JEAN",           "telephone": "25370033", "adresse": "500m de l'Hôpital de Bogodogo",                             "lat": 12.349,   "lng": -1.502},
    ],
    4: [
        {"nom": "AIMEVO",               "telephone": "25393699", "adresse": "En Face de la Mairie de Karpala",                           "lat": 12.34,    "lng": -1.56},
        {"nom": "ARZOUMA",              "telephone": "25480153", "adresse": "Quartier Pissy, à 100m de la clinique du Plateau",          "lat": 12.351,   "lng": -1.573},
        {"nom": "AVE MARIA",            "telephone": "25479888", "adresse": "Karpala non loin de la Station Oryx",                       "lat": 12.34,    "lng": -1.56},
        {"nom": "BALKUY",               "telephone": "25375136", "adresse": "Route de Pô, non loin de la Station Total",                 "lat": 12.348,   "lng": -1.518},
        {"nom": "BLESSING",             "telephone": "76653855", "adresse": "Après le rond point de la Transition",                      "lat": 12.354,   "lng": -1.548},
        {"nom": "CHARIS",               "telephone": "25479878", "adresse": "Cité relais de Zagtouli, route de bobo",                    "lat": 12.318,   "lng": -1.608},
        {"nom": "CHRISTVI",             "telephone": "78818819", "adresse": "Après le Marché de Bétail direction échangeur du Nord",     "lat": 12.392,   "lng": -1.543},
        {"nom": "COURA",                "telephone": "25388390", "adresse": "200m côté ouest du rond-point des Droits Humains",           "lat": 12.36,    "lng": -1.535},
        {"nom": "DJABAL",               "telephone": "25300576", "adresse": "Kamsonghin secteur 6, Av Ouezzin Coulibaly",                "lat": 12.364,   "lng": -1.508},
        {"nom": "DUNIA",                "telephone": "25408746", "adresse": "Avenue des Arts/ face au rond-point des Artistes",          "lat": 12.37,    "lng": -1.546},
        {"nom": "GALIAM",               "telephone": "25653165", "adresse": "Tampouy, route de la mairie de Sig-Nonghin",                "lat": 12.405,   "lng": -1.543},
        {"nom": "GEORGETTE",            "telephone": "25500528", "adresse": "Bassinko, route de Ouahigouya",                             "lat": 12.455,   "lng": -1.57},
        {"nom": "KAMBOINSIN",           "telephone": "73486758", "adresse": "Face du Centre Emetteur de KAMBOINSIN",                     "lat": 12.435,   "lng": -1.51},
        {"nom": "KILWIN",               "telephone": "25508462", "adresse": "Route de Ouahigouya, côté station Shell",                   "lat": 12.405,   "lng": -1.543},
        {"nom": "LA SAINTE TRINITE",    "telephone": "25412646", "adresse": "Wemtenga à côté de la Caisse Populaire Song-Taaba",        "lat": 12.37,    "lng": -1.505},
        {"nom": "NAGRIN",               "telephone": "25469048", "adresse": "Route de Saponé avant l'hôpital Blaise Compaoré",          "lat": 12.325,   "lng": -1.512},
        {"nom": "NINRWA",               "telephone": "25418038", "adresse": "Route Benogo - Kossodo",                                    "lat": 12.349,   "lng": -1.502},
        {"nom": "NONSIN",               "telephone": "25417776", "adresse": "Nonsin, route de Rimkieta",                                 "lat": 12.399,   "lng": -1.548},
        {"nom": "PIERRE TAPSOBA",       "telephone": "52117438", "adresse": "Saaba à 100m de la station OTAM",                          "lat": 12.36,    "lng": -1.478},
        {"nom": "RENAISSANCE SARL",     "telephone": "25459914", "adresse": "A 150m du rond-point de la Pate d'Oie",                    "lat": 12.347,   "lng": -1.539},
        {"nom": "SAABA",                "telephone": "25408699", "adresse": "En face du Lycée Notre Dame des Victoires",                 "lat": 12.36,    "lng": -1.478},
        {"nom": "SAINT LAZARE",         "telephone": "25368648", "adresse": "1200 logts, à côté du Pont de Boins Yaare",                "lat": 12.376,   "lng": -1.528},
        {"nom": "SAINT MICHEL",         "telephone": "25454808", "adresse": "Rimkiéta non loin de la phcie Barkwendé",                  "lat": 12.396,   "lng": -1.555},
        {"nom": "TAOKO",                "telephone": "25366927", "adresse": "Blvd Tansoba, à 500m de l'échangeur de l'Est",             "lat": 12.35,    "lng": -1.495},
        {"nom": "YENNENGA",             "telephone": "25370337", "adresse": "Blvd Tansoba face à la mairie de BOGODOGO",                 "lat": 12.349,   "lng": -1.502},
    ],
}


def calculer_groupe_actuel():
    """
    Calcule quel groupe est de garde aujourd'hui.
    Chaque groupe est actif pendant 7 jours (du samedi au vendredi).
    """
    aujourd_hui = date.today()
    delta = (aujourd_hui - DATE_REFERENCE).days
    # Calculer dans quel cycle de 7 jours on se trouve
    semaines_ecoulees = delta // 7
    # Le groupe tourne : 2, 3, 4, 1, 2, 3, 4, 1, ...
    groupe = ((GROUPE_REFERENCE - 1 + semaines_ecoulees) % 4) + 1
    return groupe


def main():
    aujourd_hui = date.today()
    date_str = aujourd_hui.strftime("%Y-%m-%d")

    groupe = calculer_groupe_actuel()
    pharmacies_du_groupe = GROUPES[groupe]

    print(f"Date : {date_str}")
    print(f"Groupe de garde calculé : GROUPE {groupe}")
    print(f"Nombre de pharmacies : {len(pharmacies_du_groupe)}")

    # Construire la liste finale
    resultat = []
    for p in pharmacies_du_groupe:
        resultat.append({
            "date":      date_str,
            "nom":       p["nom"],
            "adresse":   p["adresse"],
            "telephone": p["telephone"],
            "lat":       p["lat"],
            "lng":       p["lng"],
        })
        print(f"  OK {p['nom']:<35} tel:{p['telephone'] or 'N/A'}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)

    print(f"\n{len(resultat)} pharmacies sauvegardees dans {OUTPUT_FILE}")
    print("\nApercu des 3 premieres :")
    print(json.dumps(resultat[:3], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
