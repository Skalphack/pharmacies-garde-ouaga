import re
import requests

URL = "https://infossante.net/pharmacie-de-garde-de-ouagadougou/"
headers = {"User-Agent": "Mozilla/5.0 (compatible; FastPharma/1.0)"}

resp = requests.get(URL, headers=headers, timeout=15)
print(f"Status: {resp.status_code}")
print(f"Taille réponse: {len(resp.text)} caractères\n")

# Sauvegarder le brut pour inspection manuelle
with open("debug_raw.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("📁 HTML brut sauvegardé dans debug_raw.html\n")

# Compter les occurrences clés dans TOUTE la page (pas juste dans <table>)
print(f"Occurrences de 'tel:' dans tout le HTML : {resp.text.count('tel:')}")
print(f"Occurrences de 'daddr=' dans tout le HTML : {resp.text.count('daddr=')}")
print(f"Occurrences de 'En garde' dans tout le HTML : {resp.text.count('En garde')}")
print(f"Occurrences de '<table' dans tout le HTML : {resp.text.count('<table')}")
print(f"Occurrences de '<tr' dans tout le HTML : {resp.text.count('<tr')}")
print(f"Occurrences de 'pharmacie-' (liens fiches) : {resp.text.count('pharmacie-')}\n")

# Chercher des blocs <script> contenant potentiellement les données en JSON
scripts_with_data = re.findall(r"<script[^>]*>(.*?)</script>", resp.text, re.DOTALL)
print(f"Nombre de balises <script> : {len(scripts_with_data)}")
for i, s in enumerate(scripts_with_data):
    if "daddr" in s or "pharmacie" in s.lower() or "En garde" in s:
        print(f"\n--- Script #{i} contient des indices (extrait) ---")
        print(s[:500])

# Vérifier si le User-Agent change la réponse (test avec UA "bot")
resp_bot = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"},
    timeout=15,
)
print(f"\n--- Test avec User-Agent Googlebot ---")
print(f"Occurrences de 'tel:' : {resp_bot.text.count('tel:')}")
print(f"Occurrences de '<tr' : {resp_bot.text.count('<tr')}")
