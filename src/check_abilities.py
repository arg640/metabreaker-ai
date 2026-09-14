# src/check_abilities.py
"""Muestra la distribución de habilidades del pool para detectar errores de Pikalytics."""
from collections import Counter
from src.pokemon_pool import construir_pool

pool = construir_pool()
abilities = Counter(p["ability"] for p in pool if p["ability"])

print(f"Total habilidades únicas: {len(abilities)}\n")
for ab, n in abilities.most_common():
    pokemons = [p["pokemon"] for p in pool if p["ability"] == ab]
    print(f"{ab:<25} ({n}): {', '.join(pokemons[:8])}{'...' if len(pokemons) > 8 else ''}")