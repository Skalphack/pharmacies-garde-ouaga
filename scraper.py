import requests
import json
import re
import os
from bs4 import BeautifulSoup
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# scraper.py — FastPharma (version corrigée)
#
# Structure réelle du tableau sur infossante.net :
#   col 0 : N° (numéro)
#   col 1 : Pharmacie (lien cliquable vers la fiche)
#   col 2 : Emplacement Géographique (adresse + "situé à X Km de vous")
#   col 3 : Contacts (numéro tel: + texte "En garde" + lien Itineraire Maps)
#
# PROBLÈME PRÉCÉDENT : le texte "situé à X Km de vous" était dans l'adresse
# et le regex ne supprimait pas correctement → adresse mal parsée
# Aussi : la date était en français "10 juin 2026" au lieu de "2026-06-10"
# ─────────────────────────────────────────────────────────────────────────────

URL = "https://infossante.net/pharmacie-de-garde-de-ouagadougou/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
OUTPUT_FILE = "pharmacies_garde_ouaga.json"


def nettoyer_nom(nom: str) -> str:
    """Supprime le préfixe 'Pharmacie ' ou 'pharmacie ' si présent."""
    nom = nom.strip()
    if nom.lower().startswith("pharmacie "):
        return nom[10:].strip()
    return nom


def scraper_pharmacies() -> list:
    print(f"📡 Connexion à {URL} ...")

    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au site.")
        return []
    except requests.exceptions.Timeout:
        print("❌ Timeout (30s).")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP : {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
        print("❌ Aucun tableau trouvé sur la page.")
        return []

    rows = table.find_all("tr")
    print(f"📋 {len(rows) - 1} lignes trouvées dans le tableau")

    # Date au format ISO : "2026-06-10" (PAS en français !)
    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")

    pharmacies = []

    for i, row in enumerate(rows[1:], start=1):
        cols = row.find_all("td")

        if len(cols) < 4:
            print(f"  ⚠️  Ligne {i} ignorée (seulement {len(cols)} colonnes)")
            continue

        # ── col 1 : Nom ───────────────────────────────────────────────────
        nom_brut = cols[1].get_text(strip=True)
        if not nom_brut:
            continue
        nom = nettoyer_nom(nom_brut)

        # ── col 2 : Adresse ───────────────────────────────────────────────
        adresse_brute = cols[2].get_text(strip=True)
        # Supprimer "situé à X Km de vous" et tout ce qui suit
        adresse = re.sub(
            r'\s*situé[e]?\s+à\s+[\d.,]+\s*Km.*',
            '',
            adresse_brute,
            flags=re.IGNORECASE
        ).strip()
        # Supprimer aussi "Ouagadougou, " au début si présent
        if adresse.lower().startswith("ouagadougou, "):
            adresse = adresse[13:].strip()

        # ── col 3 : Téléphone ─────────────────────────────────────────────
        # Le lien tel: ressemble à <a href="tel:25318424">25318424</a>
        tel_link = cols[3].find("a", href=lambda h: h and h.startswith("tel:"))
        telephone = ""
        if tel_link:
            href = tel_link.get("href", "")
            # Extraire le numéro depuis href="tel:25318424"
            telephone = href.replace("tel:", "").strip()
            # Nettoyer espaces/tirets
            telephone = re.sub(r'[\s\-\.]', '', telephone)
            # Enlever préfixe international si présent
            if telephone.startswith("+226"):
                telephone = telephone[4:]
            elif telephone.startswith("00226"):
                telephone = telephone[5:]

        # ── col 3 : Coordonnées GPS ───────────────────────────────────────
        lat = None
        lng = None
        maps_link = cols[3].find(
            "a",
            href=lambda h: h and (
                "maps.google.com" in str(h) or
                "google.com/maps" in str(h)
            )
        )
        if maps_link:
            href = maps_link.get("href", "")
            # Format principal sur ce site : daddr=12.3698,-1.52286
            match = re.search(r'daddr=([-\d.]+),([-\d.]+)', href)
            if match:
                lat = float(match.group(1))
                lng = float(match.group(2))

        pharmacie = {
            "date":      date_aujourdhui,
            "nom":       nom,
            "adresse":   adresse,
            "telephone": telephone,
            "lat":       lat,
            "lng":       lng,
        }

        pharmacies.append(pharmacie)
        print(f"  ✓ [{i:2d}] {nom:<35} tél: {telephone or 'N/A':<12} GPS: {lat},{lng}")

    return pharmacies


def main():
    pharmacies = scraper_pharmacies()

    if not pharmacies:
        print("\n⚠️  Aucune pharmacie récupérée.")
        if os.path.exists(OUTPUT_FILE):
            print(f"   → Fichier existant conservé : {OUTPUT_FILE}")
            return
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        print(f"   → Fichier vide créé : {OUTPUT_FILE}")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pharmacies, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(pharmacies)} pharmacie(s) sauvegardées pour le {datetime.now().strftime('%Y-%m-%d')}")
    print(f"   Fichier : {OUTPUT_FILE}")

    # Afficher un aperçu des 3 premières
    print("\n📄 Aperçu des 3 premières entrées :")
    print(json.dumps(pharmacies[:3], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
