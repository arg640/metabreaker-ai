# src/test_floette_battle.py
"""
Prueba: batalla rápida entre un equipo con Floette-Mega y un rival cualquiera.
Sirve para verificar que el equipo es aceptado por el servidor.
"""
import asyncio
import json
import logging

from src.pokemon_set import equipo_a_showdown
from src.team_player import TeamPlayer

logging.getLogger("poke_env").setLevel(logging.ERROR)
logging.getLogger("TeamPlayer").setLevel(logging.ERROR)

BATTLE_FORMAT = "gen9championsvgc2026regmc"


def equipo_test_floette():
    return [
        {
            "pokemon": "Floette-Eternal",
            "types": ["fairy"],
            "ability": "Flower Veil",
            "item": "Floettite",
            "moves": [
                {"name": "Moonblast", "type": "fairy"},
                {"name": "Dazzling Gleam", "type": "fairy"},
                {"name": "Calm Mind", "type": "psychic"},
                {"name": "Protect", "type": "normal"},
            ],
        },
        # 5 más para completar el equipo
        {"pokemon": "Rillaboom", "types": ["grass"], "ability": "Grassy Surge", "item": "Miracle Seed",
         "moves": [{"name": "Wood Hammer", "type": "grass"}, {"name": "Grassy Glide", "type": "grass"},
                   {"name": "High Horsepower", "type": "ground"}, {"name": "Fake Out", "type": "normal"}]},
        {"pokemon": "Incineroar", "types": ["fire", "dark"], "ability": "Intimidate", "item": "Sitrus Berry",
         "moves": [{"name": "Flare Blitz", "type": "fire"}, {"name": "Throat Chop", "type": "dark"},
                   {"name": "Fake Out", "type": "normal"}, {"name": "Parting Shot", "type": "dark"}]},
        {"pokemon": "Garchomp", "types": ["dragon", "ground"], "ability": "Rough Skin", "item": "Life Orb",
         "moves": [{"name": "Earthquake", "type": "ground"}, {"name": "Dragon Claw", "type": "dragon"},
                   {"name": "Rock Slide", "type": "rock"}, {"name": "Protect", "type": "normal"}]},
        {"pokemon": "Gholdengo", "types": ["steel", "ghost"], "ability": "Good as Gold", "item": "Leftovers",
         "moves": [{"name": "Make It Rain", "type": "steel"}, {"name": "Shadow Ball", "type": "ghost"},
                   {"name": "Nasty Plot", "type": "dark"}, {"name": "Protect", "type": "normal"}]},
        {"pokemon": "Sneasler", "types": ["fighting", "poison"], "ability": "Poison Touch", "item": "Grassy Seed",
         "moves": [{"name": "Close Combat", "type": "fighting"}, {"name": "Dire Claw", "type": "poison"},
                   {"name": "Rock Slide", "type": "rock"}, {"name": "Protect", "type": "normal"}]},
    ]


async def main():
    # Cargar el equipo como rival
    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        equipos_meta = json.load(f)
    rival = equipos_meta[0]

    # Mostrar el formato Showdown del equipo con Floette
    print("=== Equipo con Floette (formato Showdown) ===\n")
    print(equipo_a_showdown(equipo_test_floette()))
    print("\n=== Iniciando batalla de prueba ===\n")

    p1 = TeamPlayer(
        team=equipo_a_showdown(equipo_test_floette()),
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=1,
        accept_open_team_sheet=True,
    )
    p2 = TeamPlayer(
        team=equipo_a_showdown(rival),
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=1,
        accept_open_team_sheet=True,
    )

    await p1.battle_against(p2, n_battles=1)

    print(f"\n=== Resultado ===")
    print(f"Batallas terminadas: {p1.n_finished_battles}")
    print(f"Victorias P1: {p1.n_won_battles}")
    print(f"Victorias P2: {p2.n_won_battles}")

    if p1.n_finished_battles == 0:
        print("\n❌ El equipo fue RECHAZADO por el servidor.")
    else:
        print("\n✅ El equipo fue ACEPTADO y la batalla terminó.")


if __name__ == "__main__":
    asyncio.run(main())