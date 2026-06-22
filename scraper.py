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

    soup = BeautifulSoup(resp.text, "html.parser")

    # Le tableau principal avec les pharmacies
    table = soup.find("table")
    if not table:
        print("❌ Tableau introuvable dans la page")
        return []

    rows = table.find_all("tr")[1:]  # skip header
    pharmacies = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        # Nom
        nom_tag = cols[1].find("a")
        nom = nom_tag.get_text(strip=True) if nom_tag else cols[1].get_text(strip=True)
        if not nom:
            continue

        # Adresse — on retire "situé à X Km de vous"
        adresse_raw = cols[2].get_text(separator=" ", strip=True)
        adresse = re.sub(r'situé à[\s\d.,]+Km de vous', '', adresse_raw).strip()
        adresse = re.sub(r'\s+', ' ', adresse)
        # Retirer le préfixe "Ouagadougou, "
        adresse = re.sub(r'^Ouagadougou,?\s*', '', adresse).strip()

        # Téléphone — dans le lien tel:
        tel_tag = cols[3].find("a", href=re.compile(r'^tel:'))
        telephone = ""
        if tel_tag:
            telephone = tel_tag.get_text(strip=True)

        # Coordonnées GPS — dans le lien Google Maps ?daddr=lat,lng
        lat, lng = None, None
        maps_tag = cols[3].find("a", href=re.compile(r'maps\.google'))
        if maps_tag:
            href = maps_tag.get("href", "")
            match = re.search(r'daddr=([-\d.]+),([-\d.]+)', href)
            if match:
                lat = float(match.group(1))
                lng = float(match.group(2))

        pharmacies.append({
            "date":      today,
            "nom":       nom,
            "adresse":   adresse,
            "telephone": telephone,
            "lat":       lat,
            "lng":       lng,
        })
        print(f"  ✅ {nom:<40} tel:{telephone or 'N/A'}")

    return pharmacies


def main():
    print(f"🔍 Scraping infossante.net...")
    pharmacies = scrape()

    if not pharmacies:
        print("⚠️ Aucune pharmacie trouvée — vérifier la structure du site")
        return

    # Dédoublonner par nom (le site a parfois des doublons)
    seen = set()
    unique = []
    for p in pharmacies:
        key = p["nom"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(p)

    print(f"\n📊 {len(pharmacies)} trouvées → {len(unique)} après dédoublonnage")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(unique)} pharmacies sauvegardées dans {OUTPUT_FILE}")
    print("\nAperçu des 3 premières :")
    print(json.dumps(unique[:3], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
