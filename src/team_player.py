# src/team_player.py
"""
Player de poke-env con logging opcional de batallas.
Captura eventos clave como Flash Fire, immunidades y boosts de habilidad.
"""
from poke_env.player import SimpleHeuristicsPlayer


class TeamPlayer(SimpleHeuristicsPlayer):
    def __init__(self, team: str, *args, **kwargs):
        super().__init__(*args, team=team, **kwargs)
        # Lista de eventos capturados
        self.captured_events = []

    def _handle_battle_message(self, split_messages):
        """Captura eventos relevantes antes de pasarlos al padre."""
        try:
            for message in split_messages:
                if not isinstance(message, list):
                    continue
                for line in message:
                    if not isinstance(line, str):
                        continue
                    # Capturamos eventos relacionados con habilidades
                    if "Flash Fire" in line or "flashfire" in line.lower():
                        self.captured_events.append(("flash_fire", line))
                    elif "-immune" in line:
                        self.captured_events.append(("immune", line))
        except Exception:
            pass  # No dejar que el logging rompa la batalla

        return super()._handle_battle_message(split_messages)