# src/test_conversion.py
import json
from src.pokemon_set import equipo_a_showdown

with open("data/processed/sample_teams.json", encoding="utf-8") as f:
    equipos = json.load(f)

print("=== Equipo #1 en formato Showdown ===\n")
print(equipo_a_showdown(equipos[0]))