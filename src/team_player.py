# src/team_player.py
"""
Player de poke-env con:
- Team Preview inteligente (eligen leads con Fake Out / Intimidate / Speed Control).
- Lógica de Fake Out en turno 1.
- Megaevolución cuando da ventaja clara.
- Logging de eventos (Flash Fire, inmunidades).
"""
import random
from poke_env.player import SimpleHeuristicsPlayer


# ============================================================
# LISTAS DE MOVIMIENTOS CLAVE
# ============================================================
FAKE_OUT = "fakeout"
SPEED_CONTROL = {"tailwind", "trickroom", "icywind", "electroweb"}
PROTECT_MOVES = {"protect", "detect", "kingsshield", "spikyshield",
                 "banefulbunker", "obstruct", "silktrap", "burningbulwark"}
MEGA_STONES_HABILIDADES_UTILES = {
    "charizard-Mega-Y": "drought",
    "charizardmega-y": "drought",
}


class TeamPlayer(SimpleHeuristicsPlayer):
    def __init__(self, team: str, *args, **kwargs):
        super().__init__(*args, team=team, **kwargs)
        self.captured_events = []
        self._megaevolucionado = False
        self._fake_out_usado = False

    # ============================================================
    # LOGGING (mantenemos lo que ya había)
    # ============================================================
    def _handle_battle_message(self, split_messages):
        try:
            for message in split_messages:
                if not isinstance(message, list):
                    continue
                for line in message:
                    if not isinstance(line, str):
                        continue
                    if "Flash Fire" in line or "flashfire" in line.lower():
                        self.captured_events.append(("flash_fire", line))
                    elif "-immune" in line:
                        self.captured_events.append(("immune", line))
        except Exception:
            pass
        return super()._handle_battle_message(split_messages)

    # ============================================================
    # UTILIDADES
    # ============================================================
    def _nombres_moves(self, pokemon) -> set:
        """Devuelve el set de IDs de movimientos de un Pokémon."""
        try:
            return {m.id for m in pokemon.moves.values() if m is not None}
        except Exception:
            return set()

    def _score_lead(self, pokemon) -> int:
        """Puntúa qué tan buen lead es un Pokémon."""
        score = 0
        moves = self._nombres_moves(pokemon)
        ability = (pokemon.ability or "").lower()

        # Fake Out es el rey del lead
        if FAKE_OUT in moves:
            score += 100
        # Intimidate
        if ability == "intimidate":
            score += 50
        # Speed control
        if moves & SPEED_CONTROL:
            score += 40
        # Protect es señal de Pokémon bien construido
        if moves & PROTECT_MOVES:
            score += 10
        # Si tiene Mega Stone, bonus pequeño
        if pokemon.item and "ite" in pokemon.item.lower():
            score += 5

        return score

    # ============================================================
    # TEAM PREVIEW
    # ============================================================
    def teampreview(self, battle):
        """
        Elige los 4 Pokémon a llevar y su orden.
        Los 2 primeros serán los leads.
        """
        try:
            # battle.team es dict {posición: Pokemon}
            team = battle.team
            if not team or len(team) < 4:
                return self.random_teampreview(battle)

            # Puntuar cada Pokémon como lead
            scored = []
            for pos, pokemon in team.items():
                score = self._score_lead(pokemon)
                scored.append((pos, score, pokemon.species))

            # Ordenar por score descendente
            scored.sort(key=lambda x: -x[1])

            # Elegir los 4 mejores
            elegidos = [pos for pos, _, _ in scored[:4]]

            # Formatear: "/team " + posiciones en orden
            # Las posiciones ya vienen ordenadas por mejor lead primero
            return "/team " + "".join(str(p) for p in elegidos)

        except Exception:
            return self.random_teampreview(battle)

    # ============================================================
    # CHOOSE MOVE
    # ============================================================
    def choose_move(self, battle):
        """
        Lógica custom:
        1. Turno 1: usar Fake Out si está disponible.
        2. Megaevolucionar cuando sea ventajoso.
        3. Delegar al SimpleHeuristicsPlayer.
        """
        try:
            # --- 1. FAKE OUT TURNO 1 ---
            if not self._fake_out_usado and battle.turn == 1:
                # En dobles, necesitamos devolver órdenes para cada Pokémon activo
                if battle.available_moves:
                    fake_out_order = self._intentar_fake_out(battle)
                    if fake_out_order is not None:
                        self._fake_out_usado = True
                        return fake_out_order

            # --- 2. MEGAEVOLUCIÓN ---
            if not self._megaevolucionado and battle.can_mega_evolve:
                mega_order = self._intentar_megaevolucionar(battle)
                if mega_order is not None:
                    self._megaevolucionado = True
                    return mega_order

        except Exception:
            pass

        # --- 3. Delegar al padre ---
        return super().choose_move(battle)

    def _intentar_fake_out(self, battle):
        """Intenta usar Fake Out si algún Pokémon activo lo tiene disponible."""
        try:
            # battle.active_pokemon es lista (en dobles, 2 elementos)
            for i, pokemon in enumerate(battle.active_pokemon):
                if pokemon is None:
                    continue
                moves = self._nombres_moves(pokemon)
                if FAKE_OUT in moves:
                    # Buscar el movimiento fakeout en available_moves
                    for move in battle.available_moves:
                        if move.id == FAKE_OUT:
                            # Para dobles, devolver lista con orden
                            return self.create_order(move)
        except Exception:
            return None
        return None

    def _intentar_megaevolucionar(self, battle):
        """Megaevoluciona si algún Pokémon activo puede y conviene."""
        try:
            # poke-env 0.16+: battle.active_pokemon y battle.can_mega_evolve
            for pokemon in battle.active_pokemon:
                if pokemon is None:
                    continue
                # Si el Pokémon puede megaevolucionar y tiene movimientos disponibles,
                # megaevolucionar con él este turno.
                if pokemon.can_mega_evolve if hasattr(pokemon, "can_mega_evolve") else False:
                    # Crear orden de mega + primer movimiento disponible
                    if battle.available_moves:
                        move = battle.available_moves[0]
                        return self.create_order(move, mega=True)
        except Exception:
            return None
        return None