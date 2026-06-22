# pip install lxml beautifulsoup4 requests --break-system-packages
import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import date

OUTPUT_FILE = "pharmacies_garde_ouaga.json"
URL = "https://infossante.net/pharmacie-de-garde-de-ouagadougou/"


def scrape():
    today = date.today().strftime("%Y-%m-%d")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FastPharma/1.0)"}
    try:
        resp = requests.get(URL, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Erreur requête : {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")

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


def main():
    print(f"🔍 Scraping infossante.net...")
    pharmacies = scrape()
    if not pharmacies:
        print("⚠️ Aucune pharmacie récupérée")
        return
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pharmacies, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(pharmacies)} pharmacies sauvegardées dans {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
