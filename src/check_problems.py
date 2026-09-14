# src/check_problems.py
import json

with open("data/raw/pikalytics_full.json", encoding="utf-8") as f:
    data = json.load(f)

# Buscar Pinsir (uno de los que da 0%)
for entry in data:
    if entry.get("name") == "pinsir":
        print("=== Pinsir (raw) ===")
        print(f"  percent: {repr(entry.get('percent'))}")
        print(f"  ranking: {repr(entry.get('ranking'))}")
        print(f"  winRate: {repr(entry.get('winRate'))}")
        print(f"  games: {repr(entry.get('games'))}")
        break

# Buscar Indeedee-f
for entry in data:
    if entry.get("name") == "indeedee-f":
        print("\n=== Indeedee-f (raw) ===")
        print(f"  name (raw): {repr(entry.get('name'))}")
        print(f"  display_name: {repr(entry.get('display_name'))}")
        print(f"  name_trans: {repr(entry.get('name_trans'))}")
        break

# Buscar Sirfetch'd (con apóstrofe)
for entry in data:
    if entry.get("name") == "sirfetch'd":
        print("\n=== Sirfetch'd (raw) ===")
        print(f"  name (raw): {repr(entry.get('name'))}")
        print(f"  display_name: {repr(entry.get('display_name'))}")
        print(f"  name_trans: {repr(entry.get('name_trans'))}")
        break

# Ver los últimos 5 nombres tal como vienen en el JSON
print("\n=== Últimos 10 nombres (raw) ===")
for entry in data[-10:]:
    print(f"  name={repr(entry.get('name'))}  display_name={repr(entry.get('display_name'))}  percent={repr(entry.get('percent'))}")