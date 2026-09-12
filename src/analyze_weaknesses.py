# src/analyze_weaknesses.py
"""Analiza las debilidades compartidas del Top 20 del meta actual."""
import pandas as pd
from collections import Counter
from src.type_chart import TYPES, multiplicador

# Tipos de los 20 Pokémon más usados (hardcoded por ahora)
TOP20_TYPES: dict[str, list[str]] = {
    "Rillaboom":         ["grass"],
    "Sneasler":          ["fighting", "poison"],
    "Incineroar":        ["fire", "dark"],
    "Salamence":         ["dragon", "flying"],
    "Kingambit":         ["dark", "steel"],
    "Basculegion":       ["water", "ghost"],
    "Golisopod":         ["bug", "water"],
    "Indeedee-F":        ["psychic", "normal"],
    "Farigiraf":         ["normal", "psychic"],
    "Garchomp":          ["dragon", "ground"],
    "Pelipper":          ["water", "flying"],
    "Whimsicott":        ["grass", "fairy"],
    "Sinistcha":         ["grass", "ghost"],
    "Gholdengo":         ["steel", "ghost"],
    "Archaludon":        ["steel", "dragon"],
    "Floette-Eternal":   ["fairy"],
    "Tyranitar":         ["rock", "dark"],
    "Baxcalibur":        ["dragon", "ice"],
    "Lucario":           ["fighting", "steel"],
    "Milotic":           ["water"],
}


def main():
    df_top = pd.read_csv("data/processed/meta_top20.csv")
    df_top["types"] = df_top["pokemon"].map(TOP20_TYPES)

    if df_top["types"].isna().any():
        print("⚠️ Pokémon sin tipos asignados:")
        print(df_top[df_top["types"].isna()][["pokemon"]])
        return

    # Matriz de multiplicadores: filas = Pokémon, columnas = tipo de ataque
    matriz = []
    for _, row in df_top.iterrows():
        fila = {"pokemon": row["pokemon"], "usage_pct": row["usage_pct"]}
        for atk in TYPES:
            fila[atk] = multiplicador(atk, row["types"])
        matriz.append(fila)
    df_matriz = pd.DataFrame(matriz)

    # Ranking: tipos de ataque que golpean súper efectivamente al mayor número de Pokémon del Top 20
    print("=== Tipos de ataque que golpean a más Pokémon del Top 20 (x2 o más) ===\n")
    conteo_debilidades = Counter()
    for atk in TYPES:
        n_debiles = (df_matriz[atk] >= 2.0).sum()
        conteo_debilidades[atk] = n_debiles

    for atk, n in conteo_debilidades.most_common():
        barra = "█" * n
        print(f"  {atk:<10} {n:>2}/20  {barra}")

    # También: tipos que golpean a 0 Pokémon (inútiles contra el meta)
    print("\n=== Tipos con efectividad nula contra el Top 20 ===")
    for atk in TYPES:
        n_inmunes = (df_matriz[atk] == 0.0).sum()
        if n_inmunes >= 2:
            print(f"  {atk}: {n_inmunes} Pokémon inmunes")

    # Guardar la matriz para análisis posteriores
    df_matriz.to_csv("data/processed/weakness_matrix.csv", index=False, encoding="utf-8")
    print("\n✅ Matriz guardada en data/processed/weakness_matrix.csv")

    # Top 3 tipos de ataque anti-meta
    print("\n=== 🎯 Top 3 tipos de ataque recomendados para el equipo anti-meta ===")
    for atk, n in conteo_debilidades.most_common(3):
        pokemon_debiles = df_matriz[df_matriz[atk] >= 2.0]["pokemon"].tolist()
        print(f"\n  {atk.upper()} ({n}/20):")
        for p in pokemon_debiles:
            print(f"    - {p}")


if __name__ == "__main__":
    main()