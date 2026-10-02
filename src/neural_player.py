"""NeuralPlayer con expert lookup (DAgger real)."""
import json
import pickle
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from poke_env.player import SimpleHeuristicsPlayer, DoubleBattleOrder


MODEL_PATH = Path("models_bc/bc_model.pt")
EXPERT_INDEX_PATH = Path("models_bc/expert_index.pkl")
LOG_DIR = Path("data/ga_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
WINNER_LOGS = LOG_DIR / "winner_logs.jsonl"

MAX_SPECIES = 100
MAX_ACTIONS = 150
N_FIXED = 28
N_SPECIES_BLOCK = MAX_SPECIES * 4
N_MOVES_BLOCK = MAX_ACTIONS
N_COUNT_BLOCK = 4
N_FEATURES = N_FIXED + N_SPECIES_BLOCK + N_MOVES_BLOCK + N_COUNT_BLOCK
N_ACTIONS = MAX_ACTIONS

# Umbral de distancia para considerar que un estado es "similar" a uno humano
EXPERT_DISTANCE_THRESHOLD = 0.15


# ============================================================
# CACHÉ GLOBAL DE MODELO Y EXPERTO
# ============================================================
_CACHED_CKPT = None
_CACHED_CKPT_PATH = None
_CACHED_TREE = None
_CACHED_TREE_X = None
_CACHED_TREE_Y = None

# Contadores globales
_EXPERT_STATS = {"hits": 0, "misses": 0, "avg_distance": 0.0}


def _get_cached_ckpt(model_path: Path) -> dict:
    global _CACHED_CKPT, _CACHED_CKPT_PATH
    if _CACHED_CKPT is None or _CACHED_CKPT_PATH != str(model_path):
        print(f"[NeuralPlayer] 📂 Cargando modelo desde {model_path}...")
        _CACHED_CKPT = torch.load(model_path, map_location="cpu", weights_only=False)
        _CACHED_CKPT_PATH = str(model_path)
        print(f"[NeuralPlayer] ✅ Modelo cacheado (val_acc={_CACHED_CKPT.get('val_acc', '?')})")
    return _CACHED_CKPT


def _get_cached_expert() -> tuple:
    global _CACHED_TREE, _CACHED_TREE_X, _CACHED_TREE_Y
    if _CACHED_TREE is None:
        if not EXPERT_INDEX_PATH.exists():
            print(f"[NeuralPlayer] ⚠️ No existe {EXPERT_INDEX_PATH}. Sin experto.")
            _CACHED_TREE = False
            return None, None, None
        print(f"[NeuralPlayer] 📂 Cargando índice del experto...")
        with EXPERT_INDEX_PATH.open("rb") as f:
            data = pickle.load(f)
        _CACHED_TREE = data["tree"]
        _CACHED_TREE_X = data["X"]
        _CACHED_TREE_Y = data["y"]
        print(f"[NeuralPlayer] ✅ Experto cacheado ({data['n_samples']} muestras)")
    if _CACHED_TREE is False:
        return None, None, None
    return _CACHED_TREE, _CACHED_TREE_X, _CACHED_TREE_Y


def _crear_modelo(state_dict: dict, use_fp16: bool) -> nn.Module:
    model = nn.Sequential(
        nn.Linear(N_FEATURES, 512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, 256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256, N_ACTIONS),
    )
    model.load_state_dict(state_dict)
    model.eval()
    if use_fp16:
        model = model.half()
    return model


def norm(name):
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")


def extract_compact(feats_full: np.ndarray) -> np.ndarray:
    """Reduce 582 dims a 17 dims (idéntico a build_expert_index.py)."""
    turn = feats_full[0]
    hp = feats_full[1:5]
    status = feats_full[5:9]
    fainted = feats_full[9:13]

    def get_species_idx(block):
        return int(block.argmax()) if block.max() > 0 else -1

    s_p1a = get_species_idx(feats_full[N_FIXED:N_FIXED + MAX_SPECIES])
    s_p1b = get_species_idx(feats_full[N_FIXED + MAX_SPECIES:N_FIXED + MAX_SPECIES * 2])
    s_p2a = get_species_idx(feats_full[N_FIXED + MAX_SPECIES * 2:N_FIXED + MAX_SPECIES * 3])
    s_p2b = get_species_idx(feats_full[N_FIXED + MAX_SPECIES * 3:N_FIXED + MAX_SPECIES * 4])

    species_norm = np.array([s_p1a, s_p1b, s_p2a, s_p2b], dtype=np.float32) / max(1, MAX_SPECIES - 1)

    return np.concatenate([[turn], hp, status, fainted, species_norm])


class NeuralPlayer(SimpleHeuristicsPlayer):
    def __init__(self, team: str, *args, model_path: str | Path | None = None, **kwargs):
        super().__init__(*args, team=team, **kwargs)
        self._model_path = Path(model_path) if model_path else MODEL_PATH
        self._load_model()
        self._load_expert()
        self._battle_buffer = {}
        self._seen_keys = {}

    def _load_model(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        ckpt = _get_cached_ckpt(self._model_path)
        self.species_vocab = ckpt["species_vocab"]
        self.move_vocab = ckpt["move_vocab"]
        self.idx_to_move = {v: k for k, v in self.move_vocab.items()}
        self.use_fp16 = self.device.type == "cuda"
        self.model = _crear_modelo(ckpt["state_dict"], self.use_fp16).to(self.device)

    def _load_expert(self):
        self.expert_tree, self.expert_X, self.expert_y = _get_cached_expert()

    # ============================================================
    # EXPERT LOOKUP
    # ============================================================
    def _buscar_experto(self, feats_full: np.ndarray) -> tuple:
        if self.expert_tree is None:
            return None, float("inf")

        compact = extract_compact(feats_full).reshape(1, -1)
        dist, idx = self.expert_tree.query(compact, k=1)
        d = float(dist[0][0])

        if d <= EXPERT_DISTANCE_THRESHOLD:
            action = int(self.expert_y[idx[0][0]])
            return action, d
        return None, d

    # ============================================================
    # HOOK DE FIN DE BATALLA
    # ============================================================
    def _battle_finished_callback(self, battle):
        try:
            tag = battle.battle_tag
            datos = self._battle_buffer.pop(tag, None)
            self._seen_keys.pop(tag, None)

            if battle.won and datos:
                with WINNER_LOGS.open("a", encoding="utf-8") as f:
                    for feats, action in datos:
                        f.write(json.dumps({"f": feats, "a": action}) + "\n")
        except Exception:
            pass

    def _log_state_action(self, battle, feats: np.ndarray):
        """Guarda (estado, acción_EXPERTO) si existe un vecino cercano."""
        try:
            tag = battle.battle_tag
            if tag not in self._battle_buffer:
                self._battle_buffer[tag] = []
                self._seen_keys[tag] = set()

            key = (battle.turn, int(feats[26]))
            if key in self._seen_keys[tag]:
                return
            self._seen_keys[tag].add(key)

            action, dist = self._buscar_experto(feats)
            if action is None:
                _EXPERT_STATS["misses"] += 1
                return

            _EXPERT_STATS["hits"] += 1
            n = _EXPERT_STATS["hits"]
            _EXPERT_STATS["avg_distance"] = (
                _EXPERT_STATS["avg_distance"] * (n - 1) + dist
            ) / n

            self._battle_buffer[tag].append((feats.tolist(), action))
        except Exception:
            pass

    # ============================================================
    # FEATURES
    # ============================================================
    def _moves_seen_pokemon(self, pokemon):
        if pokemon is None:
            return set()
        try:
            return {norm(m.id) for m in pokemon.moves.values() if m is not None}
        except Exception:
            return set()

    def _extract_features(self, battle, acting_slot: int) -> np.ndarray:
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
        active_list = list(battle.active_pokemon) if battle.active_pokemon else []
        if slot >= len(active_list) or active_list[slot] is None:
            return None

        pokemon = active_list[slot]
        movimientos = list(pokemon.moves.values())
        if not movimientos:
            return None

        disponibles_ids = set()
        try:
            if slot == 0:
                disponibles_ids = {norm(m.id) for m in battle.available_moves}
            else:
                disponibles_ids = {norm(m.id) for m in movimientos}
        except Exception:
            disponibles_ids = {norm(m.id) for m in movimientos}

        feats = self._extract_features(battle, slot)
        with torch.no_grad():
            x = torch.tensor(feats, dtype=torch.float32).unsqueeze(0).to(self.device)
            if self.use_fp16:
                x = x.half()
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1).squeeze(0).float().cpu().numpy()

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

        if best_move is None and movimientos:
            best_move = movimientos[0]

        if best_move is not None:
            self._log_state_action(battle, feats)

        return best_move

    def choose_move(self, battle):
        try:
            active_list = list(battle.active_pokemon) if battle.active_pokemon else []
            n_actives = len(active_list)

            if n_actives <= 1:
                move = self._choose_for_slot(battle, 0)
                if move is not None:
                    return self.create_order(move)
                return super().choose_move(battle)

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

            if order1 is not None and order2 is not None:
                return DoubleBattleOrder(first_order=order1, second_order=order2)

            return super().choose_move(battle)

        except Exception:
            return super().choose_move(battle)