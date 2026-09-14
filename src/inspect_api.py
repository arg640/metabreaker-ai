# src/inspect_api.py
"""Inspecciona la estructura del JSON de Pikalytics."""
import json
from collections import Counter

with open("data/raw/pikalytics_api.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total de entradas: {len(data)}\n")

# 1. ¿Qué claves tiene cada entrada?
print("=== Claves de las primeras 3 entradas ===")
for entry in data[:3]:
    print(f"  {entry.get('name', '?'):<25} keys={list(entry.keys())}")

# 2. ¿Cuántas entradas tienen 'moves' no vacío?
print("\n=== Análisis del campo 'moves' ===")
con_moves = 0
sin_moves = 0
for entry in data:
    moves = entry.get("moves")
    if moves:
        con_moves += 1
    else:
        sin_moves += 1
print(f"  Con moves: {con_moves}")
print(f"  Sin moves: {sin_moves}")

# 3. ¿Qué tienen en 'moves' los que tienen?
print("\n=== Ejemplos de moves (3 entradas con moves) ===")
contador = 0
for entry in data:
    moves = entry.get("moves")
    if moves:
        print(f"\n  {entry['name']}:")
        print(f"    tipo de 'moves': {type(moves).__name__}")
        print(f"    longitud: {len(moves) if hasattr(moves, '__len__') else 'N/A'}")
        print(f"    contenido (primeros 2): {moves[:2] if isinstance(moves, list) else moves}")
        contador += 1
        if contador >= 3:
            break

# 4. Comparar: ¿Qué tienen los que NO tienen moves?
print("\n=== Ejemplos de entradas SIN moves ===")
contador = 0
for entry in data:
    if not entry.get("moves"):
        print(f"\n  {entry.get('name', '?')}:")
        print(f"    keys: {list(entry.keys())}")
        print(f"    percent: {entry.get('percent')}")
        print(f"    types: {entry.get('types')}")
        contador += 1
        if contador >= 3:
            break

# 5. Distribución de tipos de 'moves'
print("\n=== Tipos de dato del campo 'moves' ===")
tipos = Counter()
for entry in data:
    tipos[type(entry.get("moves")).__name__] += 1
for t, n in tipos.most_common():
    print(f"  {t}: {n}")