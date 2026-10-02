"""Construye un índice de estados humanos con sus acciones (expert lookup)."""
import json
import pickle
import re
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.neighbors import KDTree

# Paths
LOGS_PATH = Path("C:/vgc-projects/battle_logs/logs_gen9championsvgc2026regmc.json")
MODEL_PATH = Path("models_bc/bc_model.pt")
OUTPUT_INDEX = Path("models_bc/expert_index.pkl")

# Configuración (idéntica a bc_train.py v7)
MAX_SPECIES = 100
MAX_ACTIONS = 150
N_FIXED = 28
N_SPECIES_BLOCK = MAX_SPECIES * 4
N_MOVES_BLOCK = MAX_ACTIONS
N_COUNT_BLOCK = 4
N_FEATURES = N_FIXED + N_SPECIES_BLOCK + N_MOVES_BLOCK + N_COUNT_BLOCK
N_ACTIONS = MAX_ACTIONS

# Cargar vocabularios del modelo actual
print("📖 Cargando vocabularios del modelo...")
ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
SPECIES_VOCAB = ckpt["species_vocab"]
MOVE_VOCAB = ckpt["move_vocab"]
print(f"  Species: {len(SPECIES_VOCAB)} | Moves: {len(MOVE_VOCAB)}")


def norm(name):
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")


def species_one_hot(sp_name, buf, off):
    idx = SPECIES_VOCAB.get(sp_name, -1)
    if idx >= 0:
        buf[off + idx] = 1.0


def extract_compact(feats_full):
    """Reduce 582 dims a 17 dims para KDTree (turn + HP + status + fainted + species)."""
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


def parse_log_humano(log):
    """Parsea un replay humano → lista de (feats, action)."""
    pairs = []
    p1_active = [None, None]
    p2_active = [None, None]
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

        if t == "turn":
            try:
                turno = int(parts[2])
            except ValueError:
                pass
        elif t in ("switch", "drag"):
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                sp_name = norm(side.split(": ")[1].strip().split(",")[0])
                hp_match = re.search(r"(\d+)/(\d+)", parts[3]) if len(parts) > 3 else None
                hp_frac = (int(hp_match.group(1)) / max(1, int(hp_match.group(2)))) if hp_match else 1.0
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
        elif t in ("-damage", "-heal"):
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                hp_match = re.search(r"(\d+)/(\d+)", parts[3]) if len(parts) > 3 else None
                if hp_match:
                    hp_frac = int(hp_match.group(1)) / max(1, int(hp_match.group(2)))
                    slot_idx = 0 if slot_str.endswith("a") else 1
                    if slot_str.startswith("p1"):
                        p1_hp[slot_idx] = hp_frac
                    else:
                        p2_hp[slot_idx] = hp_frac
        elif t == "-status":
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                slot_idx = 0 if slot_str.endswith("a") else 1
                if slot_str.startswith("p1"):
                    p1_status[slot_idx] = 1
                else:
                    p2_status[slot_idx] = 1
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
        elif t == "-sidestart" and "tailwind" in line.lower():
            if parts[2] == "p1":
                tailwind_p1 = 1
            else:
                tailwind_p2 = 1
        elif t == "-fieldstart" and "trickroom" in line.lower():
            trick_room = 1
        elif t == "-weather":
            w = line.lower()
            weather = [0, 0, 0, 0, 0]
            if "sunnyday" in w: weather[1] = 1
            elif "raindance" in w: weather[2] = 1
            elif "sandstorm" in w: weather[3] = 1
            elif "snow" in w or "hail" in w: weather[4] = 1
            else: weather[0] = 1
        elif t == "-fieldstart" and "terrain" in line.lower():
            f = line.lower()
            terrain = [0, 0, 0, 0, 0]
            if "electric" in f: terrain[1] = 1
            elif "grassy" in f: terrain[2] = 1
            elif "psychic" in f: terrain[3] = 1
            elif "misty" in f: terrain[4] = 1
            else: terrain[0] = 1
        elif t == "move":
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                move_name = norm(parts[3].strip())
                if slot_str.startswith("p1"):
                    action_id = MOVE_VOCAB.get(move_name, -1)
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

                        species_one_hot(p1_active[0] or "", feats, N_FIXED)
                        species_one_hot(p1_active[1] or "", feats, N_FIXED + MAX_SPECIES)
                        species_one_hot(p2_active[0] or "", feats, N_FIXED + MAX_SPECIES * 2)
                        species_one_hot(p2_active[1] or "", feats, N_FIXED + MAX_SPECIES * 3)

                        moves_off = N_FIXED + N_SPECIES_BLOCK
                        for mv in moves_seen[slot_str]:
                            idx = MOVE_VOCAB.get(mv, -1)
                            if idx >= 0:
                                feats[moves_off + idx] = 1.0

                        counts_off = moves_off + N_MOVES_BLOCK
                        feats[counts_off + 0] = min(len(moves_seen["p1a"]) / 4.0, 1.0)
                        feats[counts_off + 1] = min(len(moves_seen["p1b"]) / 4.0, 1.0)
                        feats[counts_off + 2] = min(len(moves_seen["p2a"]) / 4.0, 1.0)
                        feats[counts_off + 3] = min(len(moves_seen["p2b"]) / 4.0, 1.0)

                        compact = extract_compact(feats)
                        pairs.append((compact, action_id))

                if slot_str in moves_seen:
                    moves_seen[slot_str].add(move_name)

    return pairs


def main():
    print(f"\n📂 Cargando replays humanos desde {LOGS_PATH}...")
    with open(LOGS_PATH, encoding="utf-8") as f:
        logs = json.load(f)
    print(f"  {len(logs)} replays cargados")

    print(f"\n🔨 Extrayendo pares (estado_compacto, acción)...")
    all_compact = []
    all_actions = []

    for i, (_, (_, log)) in enumerate(logs.items()):
        if i % 2000 == 0:
            print(f"  {i}/{len(logs)}")
        pairs = parse_log_humano(log)
        for compact, action in pairs:
            all_compact.append(compact)
            all_actions.append(action)

    print(f"\n  ✅ Total pares: {len(all_compact)}")

    X = np.array(all_compact, dtype=np.float32)
    y = np.array(all_actions, dtype=np.int32)
    print(f"  Shape X: {X.shape} | Shape y: {y.shape}")

    print(f"\n🌲 Construyendo KDTree (17 dims)...")
    tree = KDTree(X, leaf_size=40)
    print(f"  ✅ KDTree construido")

    print(f"\n💾 Guardando índice en {OUTPUT_INDEX}...")
    with OUTPUT_INDEX.open("wb") as f:
        pickle.dump({
            "tree": tree,
            "X": X,
            "y": y,
            "n_samples": len(X),
        }, f)
    print(f"  ✅ Guardado")

    # Test rápido: consultar el primer estado
    print(f"\n🔍 Test de consulta:")
    test_state = X[0]
    dist, idx = tree.query(test_state.reshape(1, -1), k=3)
    print(f"  Estado de prueba (primeros 5 dims): {test_state[:5]}")
    print(f"  Vecinos más cercanos: dist={dist[0]}, idx={idx[0]}")
    print(f"  Acciones de esos vecinos: {y[idx[0]]}")


if __name__ == "__main__":
    main()