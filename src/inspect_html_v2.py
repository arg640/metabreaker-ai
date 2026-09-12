# src/inspect_html_v2.py
from bs4 import BeautifulSoup
from collections import Counter

with open("data/raw/pikalytics_regmc.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# 1) Extrae TODOS los Top 20
print("=== 1. Top 20 Pokemon ===")
top20 = soup.find_all("a", class_="tournament-top20-card")
print(f"Encontrados: {len(top20)}")
for card in top20[:5]:  # solo los primeros 5 para no saturar
    rank = card.find("span", class_="tournament-top20-rank")
    name = card.find("span", class_="tournament-top20-name")
    usage = card.find("span", class_="tournament-top20-usage")
    print(f"  #{rank.text.strip() if rank else '?'} - {name.text.strip() if name else '?'} - {usage.text.strip() if usage else '?'}")

# 2) Un team-pokemon-card completo
print("\n=== 2. Primer team-pokemon-card (HTML completo) ===")
card = soup.find("div", class_="team-pokemon-card")
if card:
    print(card.prettify()[:4000])
else:
    print("No se encontro team-pokemon-card")

# 3) Nombres distintos en todos los team-pokemon-card
print("\n=== 3. Pokémon que aparecen en equipos de muestra ===")
names = Counter()
for card in soup.find_all("div", class_="team-pokemon-card"):
    name_el = card.find(class_="team-pokemon-name")
    if name_el:
        names[name_el.text.strip()] += 1
print(f"Total distintos: {len(names)}")
for name, n in names.most_common(20):
    print(f"  {name}: {n}")