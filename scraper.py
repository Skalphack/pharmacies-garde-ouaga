import requests
import json
import re
import os
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://infossante.net/pharmacie-de-garde-de-ouagadougou/"

# Headers qui imitent exactement un vrai navigateur Firefox sur Windows
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "DNT": "1",
}

OUTPUT_FILE = "pharmacies_garde_ouaga.json"


def nettoyer_nom(nom):
    nom = nom.strip()
    if nom.lower().startswith("pharmacie "):
        return nom[10:].strip()
    return nom


def extraire_telephone(col):
    for lien in col.find_all("a"):
        href = lien.get("href", "")
        if href.lower().startswith("tel:"):
            numero = href[4:].strip()
            numero = re.sub(r'[\s\-\.]', '', numero)
            if numero.startswith("+226"):
                numero = numero[4:]
            elif numero.startswith("00226"):
                numero = numero[5:]
            if len(numero) >= 8 and numero.isdigit():
                return numero
    return ""


def extraire_gps(col):
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
        # Utiliser une session pour mieux imiter un navigateur
        session = requests.Session()
        session.headers.update(HEADERS)

        # Visiter d'abord la page d'accueil (comme ferait un vrai navigateur)
        session.get("https://infossante.net/", timeout=15)

        # Puis visiter la page des gardes
        response = session.get(URL, timeout=30)
        response.raise_for_status()

    except Exception as e:
        print(f"Erreur connexion : {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Compter toutes les tables pour déboguer
    tables = soup.find_all("table")
    print(f"Nombre de tableaux trouves sur la page : {len(tables)}")

    # Chercher la table qui contient les pharmacies
    table = None
    for t in tables:
        rows = t.find_all("tr")
        if len(rows) > 2:  # La bonne table a plusieurs lignes
            table = t
            print(f"Table choisie : {len(rows)} lignes")
            break

    if not table:
        print("Aucun tableau trouve. Contenu de la page (500 premiers chars) :")
        print(response.text[:500])
        return []

    rows = table.find_all("tr")
    print(f"{len(rows) - 1} pharmacies dans le tableau")

    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")
    pharmacies = []

    for i, row in enumerate(rows[1:], start=1):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        nom_brut = cols[1].get_text(strip=True)
        if not nom_brut:
            continue
        nom = nettoyer_nom(nom_brut)

        adresse = cols[2].get_text(strip=True)
        adresse = re.sub(r'\s*situé[e]?\s+à\s+[\d.,]+\s*Km.*', '', adresse, flags=re.IGNORECASE)
        adresse = re.sub(r'\s*situe[e]?\s+a\s+[\d.,]+\s*Km.*', '', adresse, flags=re.IGNORECASE)
        adresse = adresse.strip()
        if adresse.lower().startswith("ouagadougou, "):
            adresse = adresse[13:].strip()

        telephone = extraire_telephone(cols[3])
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
