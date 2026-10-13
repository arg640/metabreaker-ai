# src/log_parser.py
"""
Parser UNIFICADO de replays humanos / logs de Showdown.

Extrae pares (features_full, action_id) que alimentan al modelo BC.

Es usado por:
  - src/bc_train.py           (entrenamiento desde 0)
  - src/dagger_retrain.py     (fine-tuning con DAgger)
  - src/build_expert_index.py (índice KDTree para expert lookup)

Cualquier cambio acá debe mantenerse consistente con:
  - src/neural_player.py::_extract_features
  - src/config.py (MAX_SPECIES, MAX_ACTIONS, N_FIXED, N_FEATURES)
"""
import re

import numpy as np

from src.config import (
    MAX_ACTIONS,
    MAX_SPECIES,
    N_FIXED,
    N_FEATURES,
    N_MOVES_BLOCK,
    N_SPECIES_BLOCK,
)


# ============================================================
# UTILIDADES
# ============================================================
def norm(name: str) -> str:
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")


def species_one_hot(sp_name: str, buf: np.ndarray, off: int, species_vocab: dict) -> None:
    idx = species_vocab.get(sp_name, -1)
    if idx >= 0:
        buf[off + idx] = 1.0


def extract_compact(feats_full: np.ndarray) -> np.ndarray:
    """
    Reduce N_FEATURES dims a 17 dims para KDTree del expert lookup.
    Dims compactas: turn + HP(4) + status(4) + fainted(4) + species_idx(4).
    """
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

    species_norm = np.array(
        [s_p1a, s_p1b, s_p2a, s_p2b], dtype=np.float32
    ) / max(1, MAX_SPECIES - 1)

    return np.concatenate([[turn], hp, status, fainted, species_norm])


# ============================================================
# VOCABULARIOS
# ============================================================
def build_vocabs(logs: dict, max_species: int = MAX_SPECIES,
                 max_moves: int = MAX_ACTIONS) -> tuple[dict, dict]:
    """
    Construye los vocabularios de species y moves a partir de los replays.

    Los replays deben ser un dict cuyo formato sea:
        { battle_id: (meta, log_str), ... }
    (formato del dump crudo de poke-env / Showdown).
    """
    species_count: dict[str, int] = {}
    move_count: dict[str, int] = {}

    for _, (_, log) in logs.items():
        for line in log.split("\n"):
            parts = line.split("|")
            if len(parts) < 4:
                continue
            if parts[1] == "poke":
                s = norm(parts[3].split(",")[0].strip())
                species_count[s] = species_count.get(s, 0) + 1
            elif parts[1] == "move":
                m = norm(parts[3].strip())
                move_count[m] = move_count.get(m, 0) + 1

    top_species = sorted(species_count.items(), key=lambda x: -x[1])[:max_species]
    top_moves = sorted(move_count.items(), key=lambda x: -x[1])[:max_moves]

    species_vocab = {s: i for i, (s, _) in enumerate(top_species)}
    move_vocab = {m: i for i, (m, _) in enumerate(top_moves)}
    return species_vocab, move_vocab


# ============================================================
# PARSEO DE UN LOG
# ============================================================
def parse_log(
    log: str,
    species_vocab: dict,
    move_vocab: dict,
) -> list[tuple[np.ndarray, int]]:
    """
    Parsea un replay humano y devuelve [(features_full, action_id), ...].

    Solo emite pares para el lado p1 (jugador). Cada acción es un move.
    Las features del estado se construyen ANTES de registrar el move
    actual -> sin leakage.
    """
    pairs: list[tuple[np.ndarray, int]] = []

    p1_active: list[str | None] = [None, None]
    p2_active: list[str | None] = [None, None]
    p1_hp = [0.0, 0.0]
    p2_hp = [0.0, 0.0]
    p1_status = [0, 0]
    p2_status = [0, 0]
    p1_fainted = [0, 0]
    p2_fainted = [0, 0]

    moves_seen = {"p1a": set(), "p1b": set(), "p2a": set(), "p2b": set()}

    tailwind_p1 = 0
    tailwind_p2 = 0
    trick_room = 0
    weather = [0, 0, 0, 0, 0]
    terrain = [0, 0, 0, 0, 0]
    turno = 0

    for line in log.split("\n"):
        parts = line.split("|")
        if len(parts) < 3:
            continue
        t = parts[1]

        # -------- TURNO --------
        if t == "turn":
            try:
                turno = int(parts[2])
            except ValueError:
                pass

        # -------- SWITCH / DRAG --------
        elif t in ("switch", "drag"):
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                sp_name = norm(side.split(": ")[1].strip().split(",")[0])
                hp_match = (
                    re.search(r"(\d+)/(\d+)", parts[3]) if len(parts) > 3 else None
                )
                hp_frac = (
                    int(hp_match.group(1)) / max(1, int(hp_match.group(2)))
                    if hp_match else 1.0
                )
                slot_idx = 0 if slot_str.endswith("a") else 1
                if slot_str in moves_seen:
                    moves_seen[slot_str] = set()
                if slot_str.startswith("p1"):
                    p1_active[slot_idx] = sp_name
                    p1_hp[slot_idx] = hp_frac
                    p1_status[slot_idx] = 0
                    p1_fainted[slot_idx] = 0
                else:
                    p2_active[slot_idx] = sp_name
                    p2_hp[slot_idx] = hp_frac
                    p2_status[slot_idx] = 0
                    p2_fainted[slot_idx] = 0

        # -------- DAÑO / CURACIÓN --------
        elif t in ("-damage", "-heal"):
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                hp_match = (
                    re.search(r"(\d+)/(\d+)", parts[3]) if len(parts) > 3 else None
                )
                if hp_match:
                    hp_frac = int(hp_match.group(1)) / max(1, int(hp_match.group(2)))
                    slot_idx = 0 if slot_str.endswith("a") else 1
                    if slot_str.startswith("p1"):
                        p1_hp[slot_idx] = hp_frac
                    else:
                        p2_hp[slot_idx] = hp_frac

        # -------- STATUS --------
        elif t == "-status":
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                slot_idx = 0 if slot_str.endswith("a") else 1
                if slot_str.startswith("p1"):
                    p1_status[slot_idx] = 1
                else:
                    p2_status[slot_idx] = 1

        # -------- FAINT --------
        elif t == "faint":
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                slot_idx = 0 if slot_str.endswith("a") else 1
                if slot_str.startswith("p1"):
                    p1_hp[slot_idx] = 0.0
                    p1_fainted[slot_idx] = 1
                else:
                    p2_hp[slot_idx] = 0.0
                    p2_fainted[slot_idx] = 1

        # -------- TAILWIND --------
        elif t == "-sidestart" and "tailwind" in line.lower():
            if parts[2] == "p1":
                tailwind_p1 = 1
            else:
                tailwind_p2 = 1
        elif t == "-sideend" and "tailwind" in line.lower():
            if parts[2] == "p1":
                tailwind_p1 = 0
            else:
                tailwind_p2 = 0

        # -------- TRICK ROOM --------
        elif t == "-fieldstart" and "trickroom" in line.lower():
            trick_room = 1
        elif t == "-fieldend" and "trickroom" in line.lower():
            trick_room = 0

        # -------- WEATHER --------
        elif t == "-weather":
            w = line.lower()
            weather = [0, 0, 0, 0, 0]
            if "sunnyday" in w:
                weather[1] = 1
            elif "raindance" in w:
                weather[2] = 1
            elif "sandstorm" in w:
                weather[3] = 1
            elif "snow" in w or "hail" in w:
                weather[4] = 1
            else:
                weather[0] = 1

        # -------- TERRAIN --------
        elif t == "-fieldstart" and "terrain" in line.lower():
            f = line.lower()
            terrain = [0, 0, 0, 0, 0]
            if "electric" in f:
                terrain[1] = 1
            elif "grassy" in f:
                terrain[2] = 1
            elif "psychic" in f:
                terrain[3] = 1
            elif "misty" in f:
                terrain[4] = 1
            else:
                terrain[0] = 1

        # -------- MOVE --------
        elif t == "move":
            side = parts[2]
            if ": " not in side:
                continue

            slot_str = side.split(":")[0]
            move_name = norm(parts[3].strip())

            # 1) Construir features ANTES del move actual (sin leakage)
            if slot_str.startswith("p1"):
                action_id = move_vocab.get(move_name, -1)
                if action_id >= 0:
                    feats = np.zeros(N_FEATURES, dtype=np.float32)
                    feats[0] = turno / 20.0
                    feats[1:5] = [p1_hp[0], p1_hp[1], p2_hp[0], p2_hp[1]]
                    feats[5:9] = [p1_status[0], p1_status[1], p2_status[0], p2_status[1]]
                    feats[9:13] = [p1_fainted[0], p1_fainted[1], p2_fainted[0], p2_fainted[1]]
                    feats[13] = tailwind_p1
                    feats[14] = tailwind_p2
                    feats[15] = trick_room
                    feats[16:21] = weather
                    feats[21:26] = terrain
                    feats[26] = 0 if slot_str.endswith("a") else 1
                    # índice 27 queda en 0 (reservado)

                    species_one_hot(p1_active[0] or "", feats, N_FIXED, species_vocab)
                    species_one_hot(p1_active[1] or "", feats, N_FIXED + MAX_SPECIES, species_vocab)
                    species_one_hot(p2_active[0] or "", feats, N_FIXED + MAX_SPECIES * 2, species_vocab)
                    species_one_hot(p2_active[1] or "", feats, N_FIXED + MAX_SPECIES * 3, species_vocab)

                    moves_off = N_FIXED + N_SPECIES_BLOCK
                    for mv in moves_seen[slot_str]:
                        idx = move_vocab.get(mv, -1)
                        if idx >= 0:
                            feats[moves_off + idx] = 1.0

                    counts_off = moves_off + N_MOVES_BLOCK
                    feats[counts_off + 0] = min(len(moves_seen["p1a"]) / 4.0, 1.0)
                    feats[counts_off + 1] = min(len(moves_seen["p1b"]) / 4.0, 1.0)
                    feats[counts_off + 2] = min(len(moves_seen["p2a"]) / 4.0, 1.0)
                    feats[counts_off + 3] = min(len(moves_seen["p2b"]) / 4.0, 1.0)

                    pairs.append((feats, action_id))

            # 2) Registrar el move DESPUÉS de construir features
            if slot_str in moves_seen:
                moves_seen[slot_str].add(move_name)

    return pairs