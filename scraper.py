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

    table = soup.find("table")
    if not table:
        print("❌ Tableau introuvable dans la page")
        return []

    rows = table.find_all("tr")[1:]  # skip header
    print(f"📋 {len(rows)} lignes trouvées dans le tableau")

    pharmacies = []

    for i, row in enumerate(rows[:3]):
        cols = row.find_all("td")
        print(f"\n--- Row {i} : {len(cols)} cols ---")
        for j, col in enumerate(cols):
            print(f"  col[{j}]: {col.get_text(strip=True)[:80]}")
            print(f"         html: {str(col)[:150]}")

    return pharmacies


def main():
    print(f"🔍 Scraping infossante.net...")
    pharmacies = scrape()

    if not pharmacies:
        print("⚠️ Debug en cours — vérifier les logs ci-dessus")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pharmacies, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(pharmacies)} pharmacies sauvegardées dans {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
