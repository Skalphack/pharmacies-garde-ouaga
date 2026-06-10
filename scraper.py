import requests
import json
import re
import os
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://infossante.net/pharmacie-de-garde-de-ouagadougou/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
OUTPUT_FILE = "pharmacies_garde_ouaga.json"


def nettoyer_nom(nom):
    nom = nom.strip()
    if nom.lower().startswith("pharmacie "):
        return nom[10:].strip()
    return nom


def extraire_telephone(col):
    """
    Le site a deux formats de lien téléphone :
      Format 1 : <a href="tel:25318424">   (sans espace)
      Format 2 : <a href="tel: 25368648">  (avec espace après tel:)
    On cherche les deux.
    """
    # Chercher TOUS les liens <a> dans la colonne
    for lien in col.find_all("a"):
        href = lien.get("href", "")
        # Vérifier si c'est un lien téléphone (avec ou sans espace)
        if href.lower().startswith("tel:"):
            # Extraire le numéro : supprimer "tel:" et tous les espaces
            numero = href[4:].strip()
            numero = re.sub(r'[\s\-\.]', '', numero)
            # Enlever préfixe international
            if numero.startswith("+226"):
                numero = numero[4:]
            elif numero.startswith("00226"):
                numero = numero[5:]
            # Retourner seulement si c'est un vrai numéro (au moins 8 chiffres)
            if len(numero) >= 8 and numero.isdigit():
                return numero
    return ""


def extraire_gps(col):
    """Extraire lat/lng depuis les liens Google Maps."""
    for lien in col.find_all("a"):
        href = lien.get("href", "")
        if "maps.google.com" in href or "google.com/maps" in href:
            match = re.search(r'daddr=([-\d.]+),([-\d.]+)', href)
            if match:
                return float(match.group(1)), float(match.group(2))
    return None, None


def scraper_pharmacies():
    print(f"Connexion a {URL} ...")

    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Erreur connexion : {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")

    if not table:
        print("Aucun tableau trouve sur la page.")
        return []

    rows = table.find_all("tr")
    print(f"{len(rows) - 1} lignes trouvees dans le tableau")

    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")
    pharmacies = []

    for i, row in enumerate(rows[1:], start=1):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        # Nom (col 1)
        nom_brut = cols[1].get_text(strip=True)
        if not nom_brut:
            continue
        nom = nettoyer_nom(nom_brut)

        # Adresse (col 2) — supprimer "situé à X Km de vous"
        adresse = cols[2].get_text(strip=True)
        adresse = re.sub(r'\s*situe[e]?\s+a\s+[\d.,]+\s*Km.*', '', adresse, flags=re.IGNORECASE)
        adresse = re.sub(r'\s*situé[e]?\s+à\s+[\d.,]+\s*Km.*', '', adresse, flags=re.IGNORECASE)
        adresse = adresse.strip()
        # Supprimer "Ouagadougou, " au début
        if adresse.lower().startswith("ouagadougou, "):
            adresse = adresse[13:].strip()

        # Téléphone (col 3) — gère les deux formats tel: et tel: (avec espace)
        telephone = extraire_telephone(cols[3])

        # GPS (col 3)
        lat, lng = extraire_gps(cols[3])

        pharmacie = {
            "date":      date_aujourdhui,
            "nom":       nom,
            "adresse":   adresse,
            "telephone": telephone,
            "lat":       lat,
            "lng":       lng,
        }
        pharmacies.append(pharmacie)
        print(f"  OK [{i:2d}] {nom:<35} tel:{telephone or 'N/A':<12} GPS:{lat},{lng}")

    return pharmacies


def main():
    pharmacies = scraper_pharmacies()

    if not pharmacies:
        print("Aucune pharmacie recuperee.")
        if os.path.exists(OUTPUT_FILE):
            print(f"Fichier existant conserve : {OUTPUT_FILE}")
            return
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pharmacies, f, ensure_ascii=False, indent=2)

    print(f"\n{len(pharmacies)} pharmacie(s) sauvegardees pour le {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Fichier : {OUTPUT_FILE}")
    print("\nApercu des 3 premieres :")
    print(json.dumps(pharmacies[:3], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
