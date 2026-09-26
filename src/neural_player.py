"""NeuralPlayer: usa el modelo BC v7 (con moves vistos) para elegir moves."""
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from poke_env.player import SimpleHeuristicsPlayer, DoubleBattleOrder


MODEL_PATH = Path("models_bc/bc_model.pt")

# Debe coincidir con bc_train.py v7
MAX_SPECIES = 100
MAX_ACTIONS = 150
N_FIXED = 28
N_SPECIES_BLOCK = MAX_SPECIES * 4
N_MOVES_BLOCK = MAX_ACTIONS
N_COUNT_BLOCK = 4
N_FEATURES = N_FIXED + N_SPECIES_BLOCK + N_MOVES_BLOCK + N_COUNT_BLOCK
N_ACTIONS = MAX_ACTIONS


def norm(name):
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")


class NeuralPlayer(SimpleHeuristicsPlayer):
    def __init__(self, team: str, *args, **kwargs):
        super().__init__(*args, team=team, **kwargs)
        self._load_model()

    def _load_model(self):
        self.device = torch.device("cpu")
        ckpt = torch.load(MODEL_PATH, map_location=self.device, weights_only=False)
        self.species_vocab = ckpt["species_vocab"]
        self.move_vocab = ckpt["move_vocab"]
        self.idx_to_move = {v: k for k, v in self.move_vocab.items()}

        self.model = nn.Sequential(
            nn.Linear(N_FEATURES, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, N_ACTIONS),
        )
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()

    def _moves_seen_pokemon(self, pokemon):
        """Set de IDs de moves que un Pokémon tiene revelados."""
        if pokemon is None:
            return set()
        try:
            return {norm(m.id) for m in pokemon.moves.values() if m is not None}
        except Exception:
            return set()

    def _extract_features(self, battle, acting_slot: int) -> np.ndarray:
        """Construye el vector de 582 features para el Pokémon activo en `acting_slot`."""
        feats = np.zeros(N_FEATURES, dtype=np.float32)

        feats[0] = min(battle.turn / 20.0, 1.0)

        p1 = list(battle.active_pokemon) if battle.active_pokemon else []
        p2 = list(battle.opponent_active_pokemon) if battle.opponent_active_pokemon else []

        for i, p in enumerate(p1[:2]):
            if p is not None:
                feats[1 + i] = float(p.current_hp_fraction)
                if p.status is not None:
                    feats[5 + i] = 1.0
                if p.fainted:
                    feats[9 + i] = 1.0
        for i, p in enumerate(p2[:2]):
            if p is not None:
                feats[3 + i] = float(p.current_hp_fraction)
                if p.status is not None:
                    feats[7 + i] = 1.0
                if p.fainted:
                    feats[11 + i] = 1.0

        try:
            if battle.side_conditions.get("tailwind", 0) > 0:
                feats[13] = 1.0
            if battle.opponent_side_conditions.get("tailwind", 0) > 0:
                feats[14] = 1.0
            if battle.fields.get("trickroom", 0) > 0:
                feats[15] = 1.0
        except Exception:
            pass

        try:
            w = battle.weather or {}
            if "sunnyday" in w: feats[16] = 1.0
            elif "raindance" in w: feats[17] = 1.0
            elif "sandstorm" in w: feats[18] = 1.0
            elif "snow" in w or "hail" in w: feats[19] = 1.0
        except Exception:
            pass

        try:
            f = battle.fields or {}
            if "electricterrain" in f: feats[21] = 1.0
            elif "grassyterrain" in f: feats[22] = 1.0
            elif "psychicterrain" in f: feats[23] = 1.0
            elif "mistyterrain" in f: feats[24] = 1.0
        except Exception:
            pass

        feats[26] = float(acting_slot)

        slots = [
            p1[0].species if len(p1) > 0 and p1[0] else "",
            p1[1].species if len(p1) > 1 and p1[1] else "",
            p2[0].species if len(p2) > 0 and p2[0] else "",
            p2[1].species if len(p2) > 1 and p2[1] else "",
        ]
        for i, sp in enumerate(slots):
            idx = self.species_vocab.get(norm(sp), -1)
            if idx >= 0:
                feats[N_FIXED + MAX_SPECIES * i + idx] = 1.0

        acting_pokemon = p1[acting_slot] if acting_slot < len(p1) else None
        seen = self._moves_seen_pokemon(acting_pokemon)
        moves_off = N_FIXED + N_SPECIES_BLOCK
        for mv in seen:
            idx = self.move_vocab.get(mv, -1)
            if idx >= 0:
                feats[moves_off + idx] = 1.0

        counts_off = moves_off + N_MOVES_BLOCK
        feats[counts_off + 0] = min(len(self._moves_seen_pokemon(p1[0] if len(p1) > 0 else None)) / 4.0, 1.0)
        feats[counts_off + 1] = min(len(self._moves_seen_pokemon(p1[1] if len(p1) > 1 else None)) / 4.0, 1.0)
        feats[counts_off + 2] = min(len(self._moves_seen_pokemon(p2[0] if len(p2) > 0 else None)) / 4.0, 1.0)
        feats[counts_off + 3] = min(len(self._moves_seen_pokemon(p2[1] if len(p2) > 1 else None)) / 4.0, 1.0)

        return feats

    def _choose_for_slot(self, battle, slot: int):
        """Elige un move para el Pokémon activo en `slot` (0 o 1)."""
        active_list = list(battle.active_pokemon) if battle.active_pokemon else []
        if slot >= len(active_list) or active_list[slot] is None:
            return None

        pokemon = active_list[slot]
        movimientos = list(pokemon.moves.values())
        if not movimientos:
            return None

        # Filtrar a moves realmente disponibles en este turno
        disponibles_ids = set()
        try:
            # En poke-env, battle.available_moves es la lista del Pokémon activo en su slot
            # Para el segundo slot puede haber battle.available_moves en cada Pokémon
            if slot == 0:
                disponibles_ids = {norm(m.id) for m in battle.available_moves}
            else:
                # Intentar obtener los moves del segundo Pokémon
                # poke-env expone battle.active_pokemon[slot].moves como dict
                # y battle.available_moves solo para el primer slot
                # Como fallback: usar todos los moves conocidos
                disponibles_ids = {norm(m.id) for m in movimientos}
        except Exception:
            disponibles_ids = {norm(m.id) for m in movimientos}

        feats = self._extract_features(battle, slot)
        with torch.no_grad():
            x = torch.tensor(feats, dtype=torch.float32).unsqueeze(0)
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1).squeeze(0).numpy()

        best_prob = -1
        best_move = None
        for move in movimientos:
            m_id = norm(move.id)
            if m_id not in disponibles_ids:
                continue
            idx = self.move_vocab.get(m_id, -1)
            if idx >= 0 and probs[idx] > best_prob:
                best_prob = probs[idx]
                best_move = move

        # Si no encontró ninguno con el modelo, usar el primero disponible
        if best_move is None and movimientos:
            best_move = movimientos[0]

        return best_move

    def choose_move(self, battle):
        try:
            active_list = list(battle.active_pokemon) if battle.active_pokemon else []
            n_actives = len(active_list)

            # Singles: devolver un BattleOrder simple
            if n_actives <= 1:
                move = self._choose_for_slot(battle, 0)
                if move is not None:
                    return self.create_order(move)
                return super().choose_move(battle)

            # Dobles: construir 2 BattleOrders y combinarlos
            move1 = self._choose_for_slot(battle, 0)
            move2 = self._choose_for_slot(battle, 1)

            order1 = None
            order2 = None

            if move1 is not None:
                try:
                    order1 = self.create_order(move1)
                except Exception:
                    order1 = None

            if move2 is not None:
                try:
                    order2 = self.create_order(move2)
                except Exception:
                    order2 = None

            # Si ambos existen, combinar en DoubleBattleOrder
            if order1 is not None and order2 is not None:
                return DoubleBattleOrder(first_order=order1, second_order=order2)

            # Si falta uno, usar el padre (que sí sabe manejar dobles)
            return super().choose_move(battle)

        except Exception:
            return super().choose_move(battle)