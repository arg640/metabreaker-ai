# src/experiment_flashfire.py
"""
Experimento: ¿Cuánto depende el equipo #1 de Flash Fire?
- Experimento A: simular contra los 10 rivales tal cual → contar activaciones.
- Experimento B: simular contra los mismos rivales SIN movimientos Fire → comparar winrate.
"""
import asyncio
import json
import logging
import copy
from pathlib import Path

from src.pokemon_set import equipo_a_showdown
from src.team_player import TeamPlayer

logging.getLogger("poke_env").setLevel(logging.CRITICAL)
logging.getLogger("TeamPlayer").setLevel(logging.CRITICAL)

BATTLE_FORMAT = "gen9championsvgc2026regmc"
N_BATALLAS = 5   # batallas por rival


def quitar_movimientos_fire(equipo: list[dict]) -> list[dict]:
    """Devuelve una copia del equipo sin movimientos de tipo fire."""
    equipo_sin_fire = []
    for p in equipo:
        p2 = copy.deepcopy(p)
        p2["moves"] = [m for m in p["moves"] if m.get("type", "").lower() != "fire"]
        # Si se quedó sin movimientos, poner uno neutral
        if not p2["moves"]:
            p2["moves"] = [{"name": "Protect", "type": "normal"}]
        equipo_sin_fire.append(p2)
    return equipo_sin_fire


async def simular(equipo_1: list[dict], equipo_2: list[dict], n_batallas: int) -> tuple:
    """Devuelve (winrate, lista de eventos capturados)."""
    from src.pokemon_pool import limpiar_equipo

    # Aplicar correcciones (habilidades, Species Clause, Item Clause)
    equipo_1 = limpiar_equipo(equipo_1)
    equipo_2 = limpiar_equipo(equipo_2)

    if len(equipo_1) < 6 or len(equipo_2) < 6:
        return 0.0, []

    p1 = TeamPlayer(
        team=equipo_a_showdown(equipo_1),
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=n_batallas,
        accept_open_team_sheet=True,
    )
    p2 = TeamPlayer(
        team=equipo_a_showdown(equipo_2),
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=n_batallas,
        accept_open_team_sheet=True,
    )
    await p1.battle_against(p2, n_battles=n_batallas)
    wr = p1.n_won_battles / p1.n_finished_battles if p1.n_finished_battles > 0 else 0.0
    return wr, p1.captured_events


async def main():
    # Cargar equipo #1
    with open("data/processed/ga_result.json", encoding="utf-8") as f:
        equipo_1 = json.load(f)["equipo"]

    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        rivales = json.load(f)[:10]

    print("=" * 60)
    print("EXPERIMENTO FLASH FIRE")
    print("=" * 60)
    print(f"Equipo #1: {[p['pokemon'] for p in equipo_1]}")
    print(f"Rivales: {len(rivales)}")
    print(f"Batallas por rival: {N_BATALLAS}\n")

    # ============ EXPERIMENTO A: rivales tal cual ============
    print("--- Experimento A: rivales con movimientos Fire ---")
    wins_a = 0
    total_a = 0
    eventos_flash_fire = 0
    eventos_immune = 0

    for i, rival in enumerate(rivales, 1):
        wr, eventos = await simular(equipo_1, rival, N_BATALLAS)
        wins_a += int(wr * N_BATALLAS)
        total_a += N_BATALLAS
        n_ff = sum(1 for t, _ in eventos if t == "flash_fire")
        n_inm = sum(1 for t, _ in eventos if t == "immune")
        eventos_flash_fire += n_ff
        eventos_immune += n_inm
        print(f"  Rival {i:>2}: winrate={wr:.1%} | Flash Fire activado: {n_ff} | Inmunidades: {n_inm}")

    wr_a = wins_a / total_a if total_a else 0.0
    print(f"\n  Winrate TOTAL (con Fire): {wr_a:.1%}")
    print(f"  Activaciones de Flash Fire: {eventos_flash_fire}")
    print(f"  Inmunidades capturadas: {eventos_immune}")

    # ============ EXPERIMENTO B: rivales sin movimientos Fire ============
    print("\n--- Experimento B: rivales SIN movimientos Fire ---")
    wins_b = 0
    total_b = 0

    for i, rival in enumerate(rivales, 1):
        rival_sin_fire = quitar_movimientos_fire(rival)
        wr, _ = await simular(equipo_1, rival_sin_fire, N_BATALLAS)
        wins_b += int(wr * N_BATALLAS)
        total_b += N_BATALLAS
        print(f"  Rival {i:>2}: winrate={wr:.1%}")

    wr_b = wins_b / total_b if total_b else 0.0
    print(f"\n  Winrate TOTAL (sin Fire): {wr_b:.1%}")

    # ============ Comparación ============
    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)
    print(f"  Con movimientos Fire:   {wr_a:.1%}")
    print(f"  Sin movimientos Fire:   {wr_b:.1%}")
    diff = wr_a - wr_b
    print(f"  Diferencia:             {diff:+.1%}")
    if abs(diff) > 0.10:
        print("\n  ⚠️  La diferencia es GRANDE → Flash Fire influye mucho")
    elif abs(diff) > 0.05:
        print("\n  🟡 La diferencia es moderada → Flash Fire influye algo")
    else:
        print("\n  ✅ La diferencia es pequeña → Flash Fire NO es determinante")


if __name__ == "__main__":
    asyncio.run(main())