import requests
import json
import re
import os
from bs4 import BeautifulSoup
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# scraper.py — FastPharma
#
# Ce script va sur infossante.net, récupère la liste des pharmacies de garde
# de Ouagadougou, et sauvegarde le résultat dans "pharmacies_garde_ouaga.json"
#
# CORRECTIONS :
#   - Les coordonnées GPS s'appellent maintenant "lat" et "lng" (pas latitude/longitude)
#   - Chaque pharmacie a son propre champ "date"
#   - Le JSON est un tableau [] directement (pas un objet avec "pharmacies" dedans)
#   - Le nom ne contient plus "Pharmacie " en préfixe (l'app l'ajoute elle-même)
#   - Gestion des erreurs si le site est inaccessible
# ─────────────────────────────────────────────────────────────────────────────

URL = "https://infossante.net/pharmacie-de-garde-de-ouagadougou/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Nom du fichier de sortie — DOIT correspondre à l'URL dans constants.dart
OUTPUT_FILE = "pharmacies_garde_ouaga.json"


def nettoyer_nom(nom: str) -> str:
    """
    Supprime le préfixe 'Pharmacie ' si présent.
    L'app Flutter ajoute ce préfixe elle-même dans l'affichage.
    Ex: "Pharmacie de la Gare" → "de la Gare"
        "ROOD WOOKO"           → "ROOD WOOKO"  (inchangé)
    """
    prefixes = ["Pharmacie ", "PHARMACIE "]
    for p in prefixes:
        if nom.startswith(p):
            return nom[len(p):].strip()
    return nom.strip()


def scraper_pharmacies() -> list:
    """
    Va sur le site, lit le tableau HTML, et retourne une liste de dicts.
    Chaque dict représente UNE pharmacie de garde pour la date d'aujourd'hui.
    """
    print(f"📡 Connexion à {URL} ...")

    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()  # Lève une erreur si code HTTP >= 400
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au site. Vérifiez votre connexion.")
        return []
    except requests.exceptions.Timeout:
        print("❌ Le site met trop de temps à répondre (timeout 30s).")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP : {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Chercher le tableau HTML sur la page
    table = soup.find("table")
    if not table:
        print("❌ Aucun tableau trouvé sur la page.")
        print("   Le site a peut-être changé de structure.")
        return []

    rows = table.find_all("tr")
    if len(rows) <= 1:
        print("⚠️  Le tableau est vide (aucune ligne de données).")
        return []

    # Date d'aujourd'hui au format YYYY-MM-DD (ex: "2026-06-10")
    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")

    pharmacies = []

    # On commence à l'index 1 pour sauter la ligne d'en-tête
    for i, row in enumerate(rows[1:], start=1):
        cols = row.find_all("td")

        # Le tableau a au moins 4 colonnes : N°, Nom, Adresse, Contact
        if len(cols) < 4:
            continue

        # ── Nom ──────────────────────────────────────────────────────────────
        nom_brut = cols[1].get_text(strip=True)
        if not nom_brut:
            continue  # Ignorer les lignes sans nom
        nom = nettoyer_nom(nom_brut)

        # ── Adresse ──────────────────────────────────────────────────────────
        adresse = cols[2].get_text(strip=True)
        # Supprimer la partie "situé à ..." qui peut traîner
        adresse = re.sub(r'\s*situé[e]? à.*', '', adresse, flags=re.IGNORECASE).strip()

        # ── Téléphone ────────────────────────────────────────────────────────
        # Chercher un lien tel: dans la colonne contact
        tel_link = cols[3].find("a", href=lambda h: h and h.startswith("tel:"))
        if tel_link:
            # Nettoyer : enlever "tel:" et les espaces/tirets
            telephone = tel_link.get_text(strip=True)
            telephone = re.sub(r'[\s\-\.]', '', telephone)
            # Enlever le préfixe international +226 ou 00226
            if telephone.startswith("+226"):
                telephone = telephone[4:]
            elif telephone.startswith("00226"):
                telephone = telephone[5:]
        else:
            # Essayer de trouver un numéro directement dans le texte
            texte_contact = cols[3].get_text(strip=True)
            match_tel = re.search(r'[\d\s\-\.]{8,}', texte_contact)
            telephone = match_tel.group(0).strip() if match_tel else ""
            telephone = re.sub(r'[\s\-\.]', '', telephone)

        # ── Coordonnées GPS ──────────────────────────────────────────────────
        # IMPORTANT : les champs s'appellent "lat" et "lng" (pas latitude/longitude)
        # pour correspondre exactement à ce qu'attend Pharmacie.fromJson() dans Flutter
        lat = None
        lng = None

        # Chercher un lien Google Maps dans toute la ligne
        maps_link = cols[3].find(
            "a",
            href=lambda h: h and ("maps.google.com" in str(h) or "google.com/maps" in str(h))
        )
        if maps_link:
            href = maps_link['href']
            # Format 1 : daddr=12.3695,-1.52255
            match = re.search(r'daddr=([-\d.]+),([-\d.]+)', href)
            if match:
                lat = float(match.group(1))
                lng = float(match.group(2))
            else:
                # Format 2 : @12.3695,-1.52255
                match = re.search(r'@([-\d.]+),([-\d.]+)', href)
                if match:
                    lat = float(match.group(1))
                    lng = float(match.group(2))
                else:
                    # Format 3 : ll=12.3695,-1.52255
                    match = re.search(r'll=([-\d.]+),([-\d.]+)', href)
                    if match:
                        lat = float(match.group(1))
                        lng = float(match.group(2))

        # ── Construire l'objet pharmacie ─────────────────────────────────────
        # STRUCTURE EXACTE attendue par Pharmacie.fromJson() dans Flutter :
        # - "date"      : date de garde (YYYY-MM-DD)
        # - "nom"       : nom sans "Pharmacie " devant
        # - "adresse"   : adresse
        # - "telephone" : numéro local 8 chiffres (sans +226)
        # - "lat"       : latitude (float ou null)
        # - "lng"       : longitude (float ou null)
        pharmacie = {
            "date":      date_aujourdhui,   # ← chaque pharmacie a sa propre date
            "nom":       nom,
            "adresse":   adresse,
            "telephone": telephone,
            "lat":       lat,               # ← "lat" pas "latitude"
            "lng":       lng,               # ← "lng" pas "longitude"
        }

        pharmacies.append(pharmacie)
        print(f"  ✓ {nom} | tél: {telephone or 'N/A'} | GPS: {lat},{lng}")

    return pharmacies


def main():
    pharmacies = scraper_pharmacies()

    if not pharmacies:
        print("\n⚠️  Aucune pharmacie récupérée.")
        print("   Si ce dossier contient déjà un fichier pharmacies_garde_ouaga.json,")
        print("   il sera conservé tel quel (pas d'écrasement avec données vides).")

        # Ne pas écraser l'ancien fichier si on n'a rien récupéré
        if os.path.exists(OUTPUT_FILE):
            print(f"   → Fichier existant conservé : {OUTPUT_FILE}")
            return
        else:
            # Créer un fichier vide valide pour éviter les crashs de l'app
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
            print(f"   → Fichier vide créé : {OUTPUT_FILE}")
            return

    # ── Sauvegarder en JSON ───────────────────────────────────────────────────
    # STRUCTURE : un tableau [] directement, pas un objet {}
    # C'est exactement ce qu'attend _parseJson() dans api_service.dart :
    #   final List<dynamic> raw = jsonDecode(body) as List<dynamic>;
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pharmacies, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(pharmacies)} pharmacie(s) de garde sauvegardées")
    print(f"   Date : {datetime.now().strftime('%Y-%m-%d')}")
    print(f"   Fichier : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
