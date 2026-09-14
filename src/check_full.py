# src/check_full.py
import json

with open("data/raw/pikalytics_full.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total: {len(data)}")
print(f"Claves de la primera entrada: {list(data[0].keys())}")
print()

# Verificar que varios Pokémon tengan datos completos
for entry in data[:5]:
    nombre = entry.get("name", "?")
    moves = entry.get("moves") or []
    items = entry.get("items") or []
    abilities = entry.get("abilities") or []
    types = entry.get("types") or []
    print(f"{nombre:<25} moves={len(moves)} items={len(items)} abilities={len(abilities)} types={types}")

# Contar cuántos tienen datos completos en TODO el archivo
con_moves = sum(1 for e in data if e.get("moves"))
con_items = sum(1 for e in data if e.get("items"))
con_abilities = sum(1 for e in data if e.get("abilities"))
con_types = sum(1 for e in data if e.get("types"))

print()
print(f"Con moves:     {con_moves}/{len(data)}")
print(f"Con items:     {con_items}/{len(data)}")
print(f"Con abilities: {con_abilities}/{len(data)}")
print(f"Con types:     {con_types}/{len(data)}")