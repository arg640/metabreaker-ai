# src/verify_teams.py
import json
from pathlib import Path

with open("data/processed/sample_teams.json", encoding="utf-8") as f:
    equipos = json.load(f)

print(f"Total de equipos: {len(equipos)}\n")

# Muestra el primer equipo completo
print("=== Equipo #1 ===")
for p in equipos[0]:
    tipos = "/".join(p["types"]) if p["types"] else "?"
    moves = ", ".join(m["name"] for m in p["moves"]) if p["moves"] else "(sin moves)"
    print(f"  {p['pokemon']} [{tipos}]")
    print(f"    Ability: {p['ability']}")
    print(f"    Item: {p['item']}")
    print(f"    Moves: {moves}")

# Cuenta cuántos Pokémon tienen datos incompletos
print("\n=== Verificación de integridad ===")
sin_moves = 0
sin_item = 0
sin_ability = 0
sin_types = 0
total_pokemon = 0

for equipo in equipos:
    for p in equipo:
        total_pokemon += 1
        if not p["moves"]:
            sin_moves += 1
        if not p["item"]:
            sin_item += 1
        if not p["ability"]:
            sin_ability += 1
        if not p["types"]:
            sin_types += 1

print(f"Total de Pokémon parseados: {total_pokemon}")
print(f"Sin moves: {sin_moves}")
print(f"Sin item: {sin_item}")
print(f"Sin ability: {sin_ability}")
print(f"Sin types: {sin_types}")