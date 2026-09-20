# test_nuevo_player.py
"""Prueba de una batalla con el nuevo TeamPlayer."""
import asyncio
import json
import logging

from src.pokemon_set import equipo_a_showdown
from src.team_player import TeamPlayer
from src.pokemon_pool import limpiar_equipo

logging.getLogger("poke_env").setLevel(logging.ERROR)
logging.getLogger("TeamPlayer").setLevel(logging.ERROR)

BATTLE_FORMAT = "gen9championsvgc2026regmc"


async def main():
    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        rivales = json.load(f)

    equipo_1 = limpiar_equipo(rivales[0])
    equipo_2 = limpiar_equipo(rivales[1])

    print(f"Equipo 1: {[p['pokemon'] for p in equipo_1]}")
    print(f"Equipo 2: {[p['pokemon'] for p in equipo_2]}\n")

    p1 = TeamPlayer(
        team=equipo_a_showdown(equipo_1),
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=1,
        accept_open_team_sheet=True,
    )
    p2 = TeamPlayer(
        team=equipo_a_showdown(equipo_2),
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=1,
        accept_open_team_sheet=True,
    )

    print("Iniciando batalla...\n")
    await p1.battle_against(p2, n_battles=1)

    print(f"\n=== Resultado ===")
    print(f"Batallas terminadas: {p1.n_finished_battles}")
    print(f"Victorias P1: {p1.n_won_battles}")
    print(f"Victorias P2: {p2.n_won_battles}")

    print(f"\nEventos capturados P1: {len(p1.captured_events)}")
    print(f"Eventos capturados P2: {len(p2.captured_events)}")


if __name__ == "__main__":
    asyncio.run(main())