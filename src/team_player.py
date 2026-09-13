# src/team_player.py
"""
Player de poke-env que juega con un equipo específico y usa
la heurística simple de poke-env para elegir movimientos.
"""
from poke_env.player import SimpleHeuristicsPlayer


class TeamPlayer(SimpleHeuristicsPlayer):
    def __init__(self, team: str, *args, **kwargs):
        super().__init__(*args, team=team, **kwargs)