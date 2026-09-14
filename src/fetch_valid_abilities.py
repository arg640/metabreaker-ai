# src/fetch_valid_abilities.py
"""
Descarga el pokedex.js del servidor local de Showdown y extrae las
habilidades válidas por Pokémon. Guarda en data/raw/valid_abilities.json.
"""
import json
import re
from pathlib import Path

import requests

URL = "http://localhost:8000/data/pokedex.js"
OUTPUT = Path("data/raw/valid_abilities.json")

print(f"⬇️  Descargando {URL}...")
r = requests.get(URL, timeout=30)
r.raise_for_status()
text = r.text
print(f"✅ {len(text):,} caracteres recibidos")

# El archivo tiene entradas tipo:
#   \t\tname: "Rillaboom",
#   ...
#   \t\tabilities: {0: "Overgrow", H: "Grassy Surge"},
result = {}
current_name = None

for line in text.split("\n"):
    m = re.match(r'^\t\tname:\s*"([^"]+)"', line)
    if m:
        current_name = m.group(1)
        continue
    m = re.match(r'^\t\tabilities:\s*\{([^}]+)\}', line)
    if m and current_name:
        raw = m.group(1)
        abilities = []
        for part in raw.split(","):
            if ":" in part:
                ab = part.split(":", 1)[1].strip().strip('"').strip("'")
                if ab:
                    abilities.append(ab)
        result[current_name] = abilities
        current_name = None

print(f"\n✅ {len(result)} Pokémon con habilidades extraídas")

# Muestra ejemplos
for name in ["Rillaboom", "Sneasler", "Basculegion", "Golisopod", "Whimsicott"]:
    if name in result:
        print(f"   {name}: {result[name]}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n✅ Guardado en: {OUTPUT}")