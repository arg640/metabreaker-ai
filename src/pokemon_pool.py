# src/pokemon_pool.py
"""
Pool de Pokémon elegibles para el algoritmo genético.
Se construye a partir de los equipos de muestra del meta.
"""
import json
from pathlib import Path
from collections import Counter

# Habilidades problemáticas conocidas (forma incorrecta asignada por Pikalytics)
# clave: (nombre_pokemon, habilidad_invalida) -> habilidad_valida
HABILIDADES_CORREGIDAS = {
    ("Lycanroc", "Tough Claws"): "Sand Rush",
    ("Lycanroc-Midday", "Tough Claws"): "Sand Rush",
    ("Lycanroc-Midnight", "Tough Claws"): "No Guard",
}


def corregir_habilidad(p: dict) -> dict:
    """Corrige habilidades inválidas conocidas."""
    key = (p["pokemon"], p.get("ability", ""))
    if key in HABILIDADES_CORREGIDAS:
        p = dict(p)
        p["ability"] = HABILIDADES_CORREGIDAS[key]
    return p

def construir_pool(min_apariciones: int = 1) -> list[dict]:
    """
    Construye el pool de Pokémon candidatos a partir del sample_teams.json.
    Devuelve una lista de dicts únicos por especie.
    """
    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        equipos = json.load(f)

    # Cuenta cuántas veces aparece cada Pokémon
    apariciones = Counter()
    datos_por_pokemon = {}  # guarda el primer dict encontrado por especie

    for equipo in equipos:
        for p in equipo:
            nombre = p["pokemon"]
            apariciones[nombre] += 1
            if nombre not in datos_por_pokemon:
                datos_por_pokemon[nombre] = p

    # Filtra por apariciones mínimas y ordena por popularidad
    pool = []
    for nombre, count in apariciones.most_common():
        if count >= min_apariciones:
            entry = dict(datos_por_pokemon[nombre])
            entry["apariciones"] = count
            entry = corregir_habilidad(entry)
            pool.append(entry)

    return pool


if __name__ == "__main__":
    pool = construir_pool()
    print(f"Pool total: {len(pool)} Pokémon únicos\n")
    for i, p in enumerate(pool[:15]):
        tipos = "/".join(p["types"])
        print(f"  [{i:>2}] {p['pokemon']:<25} [{tipos}] - {p['apariciones']} apariciones")