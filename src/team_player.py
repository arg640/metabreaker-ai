# src/team_player.py
"""
Player de poke-env que juega con un equipo específico en formato Showdown.
Usa la política aleatoria incorporada, que maneja correctamente singles y doubles.
"""
from poke_env.player import Player


class TeamPlayer(Player):
    def __init__(self, team: str, *args, **kwargs):
        super().__init__(*args, team=team, **kwargs)

    def choose_move(self, battle):
        # choose_random_move ya maneja singles, doubles y team preview
        return self.choose_random_move(battle)