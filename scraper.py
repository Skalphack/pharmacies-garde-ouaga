import requests
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# scraper.py — FastPharma
#
# Utilise l'API officielle fasopharmacies.ytsamy.name
# C'est une vraie API JSON publique faite pour les développeurs.
# Elle retourne toutes les pharmacies avec leur statut de garde du jour.
#
# Documentation : https://www.fasopharmacies.ytsamy.name/site/api-doc
# ─────────────────────────────────────────────────────────────────────────────

# ID de la ville Ouagadougou dans l'API = 1
API_URL = "https://www.fasopharmacies.ytsamy.name/api/pharmacies?ville=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

OUTPUT_FILE = "pharmacies_garde_ouaga.json"


def scraper_pharmacies():
    print(f"Connexion a l'API fasopharmacies ...")

    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Erreur API : {e}")
        return []

    print(f"Total pharmacies recues : {len(data)}")

    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")
    pharmacies_garde = []

    for p in data:
        # Garder uniquement celles qui sont de garde aujourd'hui
        if not p.get("pharmacieEstDeGarde", False):
            continue

        nom = p.get("nom", "").strip()
        # Supprimer "Pharmacie " au début
        if nom.lower().startswith("pharmacie "):
            nom = nom[10:].strip()

        # Téléphone : utiliser "telephone" ou le premier de "otherphones"
        telephone = p.get("telephone", "") or ""
        if not telephone and p.get("otherphones"):
            # otherphones est une chaîne "25452999, 25361338"
            telephone = p["otherphones"].split(",")[0].strip()
        # Nettoyer le numéro
        telephone = telephone.replace(" ", "").replace("-", "")
        if telephone.startswith("+226"):
            telephone = telephone[4:]
        elif telephone.startswith("00226"):
            telephone = telephone[5:]

        lat = p.get("latitude")
        lng = p.get("longitude")

        pharmacie = {
            "date":      date_aujourdhui,
            "nom":       nom,
            "adresse":   "",  # L'API ne fournit pas l'adresse détaillée
            "telephone": telephone,
            "lat":       lat,
            "lng":       lng,
        }
        pharmacies_garde.append(pharmacie)
        print(f"  OK {nom:<35} tel:{telephone or 'N/A':<12} GPS:{lat},{lng}")

    return pharmacies_garde


def main():
    pharmacies = scraper_pharmacies()

    if not pharmacies:
        print("Aucune pharmacie de garde trouvee.")
        if os.path.exists(OUTPUT_FILE):
            print(f"Fichier existant conserve : {OUTPUT_FILE}")
            return
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pharmacies, f, ensure_ascii=False, indent=2)

    print(f"\n{len(pharmacies)} pharmacie(s) de garde pour le {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Fichier : {OUTPUT_FILE}")
    print("\nApercu des 3 premieres :")
    print(json.dumps(pharmacies[:3], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
