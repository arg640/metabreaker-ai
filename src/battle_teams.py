# src/battle_teams.py
"""
Simula una batalla entre dos equipos del sample_teams.json usando poke-env.
Uso: python -m src.battle_teams
"""
import asyncio
import json
from pathlib import Path

from src.pokemon_set import equipo_a_showdown
from src.team_player import TeamPlayer
import logging
logging.getLogger("poke_env").setLevel(logging.ERROR)


async def main():
    # 1. Carga los equipos del JSON
    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        equipos = json.load(f)

    print(f"Total de equipos cargados: {len(equipos)}")

    # 2. Convierte los primeros 2 equipos a formato Showdown
    equipo_1_txt = equipo_a_showdown(equipos[0])
    equipo_2_txt = equipo_a_showdown(equipos[1])

    print(f"\nEquipo 1: {[p['pokemon'] for p in equipos[0]]}")
    print(f"Equipo 2: {[p['pokemon'] for p in equipos[1]]}\n")

    # 3. Crea dos jugadores, cada uno con su equipo
    player_1 = TeamPlayer(
    team=equipo_1_txt,
    battle_format="gen9championsvgc2026regmc",
    max_concurrent_battles=1,
    accept_open_team_sheet=True,  
)
    player_2 = TeamPlayer(
    team=equipo_2_txt,
    battle_format="gen9championsvgc2026regmc",
    max_concurrent_battles=1,
    accept_open_team_sheet=True,  
)

    # 4. Batalla
    print("Iniciando batalla...")
    await player_1.battle_against(player_2, n_battles=10)

    # 5. Resultados
        # 5. Resultados
    n_batallas = player_1.n_finished_battles
    wins_1 = player_1.n_won_battles
    wins_2 = player_2.n_won_battles
    winrate_1 = wins_1 / n_batallas if n_batallas else 0

    print(f"\n=== Resultado ===")
    print(f"Batallas terminadas: {n_batallas}")
    print(f"Victorias del Equipo 1: {wins_1} ({winrate_1:.1%})")
    print(f"Victorias del Equipo 2: {wins_2} ({1 - winrate_1:.1%})")

    if wins_1 > wins_2:
        print("🏆 Ganador global: Equipo 1")
    elif wins_2 > wins_1:
        print("🏆 Ganador global: Equipo 2")
    else:
        print("🤝 Empate")


if __name__ == "__main__":
    asyncio.run(main())