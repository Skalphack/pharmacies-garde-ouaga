# pip install lxml beautifulsoup4 requests --break-system-packages
import json
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from datetime import date

OUTPUT_FILE = "pharmacies_garde_ouaga.json"
URL = "https://infossante.net/pharmacie-de-garde-de-ouagadougou/"

# Nombre de tentatives et délai entre chaque tentative (en secondes).
# Utile car juste après minuit le site source peut être en train de
# régénérer sa page (liste vide, timeout, erreur 5xx transitoire...).
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 90


def fetch_page():
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FastPharma/1.0)",
        # Certains sites (Cloudflare notamment) peuvent servir une page
        # mise en cache et périmée juste après minuit. On demande
        # explicitement une version fraîche.
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    resp = requests.get(URL, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.text


def scrape_once():
    today = date.today().strftime("%Y-%m-%d")
    html = fetch_page()

    # Détection basique d'une page de challenge Cloudflare / anti-bot
    # au lieu de la vraie page (ça ressemble à une page normale côté
    # HTTP status mais le contenu n'a pas de tableau exploitable).
    if "Just a moment" in html or "cf-browser-verification" in html:
        print("⚠️ Page de vérification anti-bot reçue au lieu du contenu attendu")
        return []

    soup = BeautifulSoup(html, "lxml")

    # Il y a plusieurs <table> dans la page (layout, pub...).
    # On cible celle qui contient des liens tel: (= la table des pharmacies)
    table = None
    all_tables = soup.find_all("table")
    print(f"🔎 {len(all_tables)} table(s) trouvée(s) dans la page")
    for t in all_tables:
        if t.find("a", href=re.compile(r"^tel:")):
            table = t
            break

    if not table:
        print("❌ Tableau des pharmacies introuvable (aucune table avec lien tel:)")
        return []

    rows = table.find_all("tr")[1:]  # skip header
    print(f"📋 {len(rows)} lignes trouvées dans le tableau")

    pharmacies = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        # col[1] : nom + lien fiche
        nom_tag = cols[1].find("a")
        nom = nom_tag.get_text(strip=True) if nom_tag else cols[1].get_text(strip=True)
        fiche_url = nom_tag["href"] if nom_tag else None

        # col[2] : adresse (on retire "situé à X.XX Km de vous")
        adresse_raw = cols[2].get_text(" ", strip=True)
        adresse = re.sub(r"situé à [\d.]+ Km de vous", "", adresse_raw).strip()
        adresse = re.sub(r"\s+", " ", adresse).strip(" ,")

        # col[3] : tel + statut + lien itinéraire (contient lat/lng)
        tel_tag = cols[3].find("a", href=re.compile(r"^tel:"))
        telephone = tel_tag.get_text(strip=True) if tel_tag else None
        if telephone:
            telephone = re.sub(r"\s+", "", telephone)  # ex: "25 40 70 09" -> "25407009"
        telephone = telephone or None  # chaîne vide -> None

        maps_tag = cols[3].find("a", href=re.compile(r"daddr="))
        lat, lng = None, None
        if maps_tag:
            m = re.search(r"daddr=([\-\d.]+),([\-\d.]+)", maps_tag["href"])
            if m:
                lat, lng = float(m.group(1)), float(m.group(2))

        statut = "en_garde" if "En garde" in cols[3].get_text() else "inconnu"

        pharmacies.append({
            "nom": nom,
            "adresse": adresse,
            "telephone": telephone,
            "lat": lat,
            "lng": lng,
            "statut": statut,
            "fiche_url": fiche_url,
            "date": today,
        })

    return pharmacies


def scrape():
    """Essaie plusieurs fois avant d'abandonner, pour absorber les
    ratés transitoires (site en train de tourner sa page à minuit,
    timeout réseau, erreur 5xx, challenge anti-bot passager...)."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            pharmacies = scrape_once()
            if pharmacies:
                return pharmacies
            print(f"⚠️ Tentative {attempt}/{MAX_RETRIES} : 0 pharmacie récupérée")
        except Exception as e:
            last_error = e
            print(f"❌ Tentative {attempt}/{MAX_RETRIES} : erreur requête : {e}")

        if attempt < MAX_RETRIES:
            print(f"⏳ Nouvelle tentative dans {RETRY_DELAY_SECONDS}s...")
            time.sleep(RETRY_DELAY_SECONDS)

    if last_error:
        print(f"❌ Échec définitif après {MAX_RETRIES} tentatives : {last_error}")
    return []


def main():
    print("🔍 Scraping infossante.net...")
    pharmacies = scrape()

    if not pharmacies:
        # Avant : simple `return` ici — le job GitHub Actions finissait
        # quand même en succès (vert), sans commit, en laissant le
        # fichier de la veille en place. Aucun signal visible qu'un
        # scrape a raté (site source down, structure HTML changée...).
        # On fait maintenant échouer le job explicitement pour être
        # notifié (email/badge rouge) au lieu de servir des données
        # périmées sans le savoir.
        print("❌ Aucune pharmacie récupérée après plusieurs tentatives — le site source a peut-être changé de structure, ou est indisponible.")
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pharmacies, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(pharmacies)} pharmacies sauvegardées dans {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
