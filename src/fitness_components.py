# src/fitness_components.py
"""
Componentes de fitness que no requieren simulación.
Cada uno recibe una lista de dicts (equipo) y devuelve un float entre 0 y 1.

Calibración: un equipo "típico" del meta debe sacar entre 0.4 y 0.7
en cada componente. Un equipo excelente, 0.8+. Uno malo, 0.2 o menos.
"""
from collections import Counter
from src.type_chart import TYPES, multiplicador


# ============================================================
# COBERTURA DEFENSIVA
# ============================================================
def cobertura_defensiva(equipo: list[dict]) -> float:
    """
    Mide qué tan cubierto está el equipo defensivamente.
    Penaliza que un mismo tipo de ataque golpee a muchos Pokémon del equipo.
    """
    debilidades = Counter()
    for atk in TYPES:
        for p in equipo:
            if multiplicador(atk, p["types"]) >= 2.0:
                debilidades[atk] += 1

    if not debilidades:
        return 1.0

    # Score basado en el peor tipo de ataque
    max_d = max(debilidades.values())
    # Umbrales:
    #   max_d <= 2  → 1.0 (bien cubierto)
    #   max_d = 3   → 0.75
    #   max_d = 4   → 0.50
    #   max_d = 5   → 0.25
    #   max_d >= 6  → 0.0
    if max_d <= 2:
        score_max = 1.0
    else:
        score_max = max(0.0, 1.0 - (max_d - 2) * 0.25)

    # Penalización suave por muchas debilidades totales (con techo bajo)
    total = sum(debilidades.values())
    penalizacion = min(total / 100.0, 0.15)

    return max(0.0, score_max - penalizacion)


# ============================================================
# SINERGIA OFENSIVA
# ============================================================
TIPOS_CLAVE = ["ground", "fire", "fighting"]


def sinergia_ofensiva(equipo: list[dict]) -> float:
    """
    Mide si el equipo cubre los 3 tipos clave anti-meta (Ground, Fire, Fighting).

    Ideal: al menos 2 Pokémon por tipo clave → score 1.0.
    """
    cobertura = {}
    for tipo in TIPOS_CLAVE:
        n = sum(1 for p in equipo if _puede_golpear_con(p, tipo))
        cobertura[tipo] = n

    # Score por tipo: min(n, 2) / 2.0
    scores = [min(n, 2) / 2.0 for n in cobertura.values()]
    return sum(scores) / len(scores)


def _puede_golpear_con(pokemon: dict, tipo_ataque: str) -> bool:
    """True si el Pokémon tiene al menos un movimiento del tipo indicado."""
    for move in pokemon.get("moves", []):
        if move.get("type", "").lower() == tipo_ataque.lower():
            return True
    return False


# ============================================================
# DIVERSIDAD DE TIPOS
# ============================================================
def diversidad_de_tipos(equipo: list[dict]) -> float:
    """
    Mide la diversidad de tipos defensivos del equipo.
    Con 6 Pokémon, lo ideal es tener al menos 10 tipos únicos.
    """
    tipos_unicos = set()
    for p in equipo:
        for t in p.get("types", []):
            tipos_unicos.add(t.lower())

    # Umbral: 10 tipos únicos = 1.0
    return min(len(tipos_unicos) / 10.0, 1.0)


if __name__ == "__main__":
    import json

    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        equipos = json.load(f)

    for i, equipo in enumerate(equipos[:5]):
        nombres = [p["pokemon"] for p in equipo]
        print(f"\n=== Equipo {i+1}: {nombres} ===")
        print(f"  Cobertura defensiva: {cobertura_defensiva(equipo):.2f}")
        print(f"  Sinergia ofensiva:   {sinergia_ofensiva(equipo):.2f}")
        print(f"  Diversidad de tipos: {diversidad_de_tipos(equipo):.2f}")