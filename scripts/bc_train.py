"""Behavior Cloning v3 - features ricas + slot (para dobles)."""
import json
import re
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

LOGS_PATH = Path("C:/vgc-projects/battle_logs/logs_gen9championsvgc2026regmc.json")
OUTPUT_DIR = Path("models_bc")
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_SPECIES = 200
MAX_ACTIONS = 200

SPECIES_VOCAB = {}
MOVE_VOCAB = {}

N_FIXED = 28
N_FEATURES = N_FIXED + (MAX_SPECIES * 4)
N_ACTIONS = MAX_ACTIONS


def norm(name):
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")


def build_vocabs(logs):
    species_count = {}
    move_count = {}
    for _, (_, log) in logs.items():
        for line in log.split("\n"):
            parts = line.split("|")
            if len(parts) < 3:
                continue
            if parts[1] == "poke" and len(parts) > 3:
                s = norm(parts[3].split(",")[0].strip())
                species_count[s] = species_count.get(s, 0) + 1
            elif parts[1] == "move" and len(parts) > 3:
                m = norm(parts[3].strip())
                move_count[m] = move_count.get(m, 0) + 1

    top_species = sorted(species_count.items(), key=lambda x: -x[1])[:MAX_SPECIES]
    top_moves = sorted(move_count.items(), key=lambda x: -x[1])[:MAX_ACTIONS]

    global SPECIES_VOCAB, MOVE_VOCAB
    SPECIES_VOCAB = {s: i for i, (s, _) in enumerate(top_species)}
    MOVE_VOCAB = {m: i for i, (m, _) in enumerate(top_moves)}

    print(f"Vocab especies: {len(SPECIES_VOCAB)}")
    print(f"Vocab moves: {len(MOVE_VOCAB)}")


def species_one_hot(species_name, out_buffer, offset):
    idx = SPECIES_VOCAB.get(species_name, -1)
    if idx >= 0:
        out_buffer[offset + idx] = 1.0


def parse_log(log):
    pairs = []
    p1_active = [None, None]
    p2_active = [None, None]
    p1_hp = [0.0, 0.0]
    p2_hp = [0.0, 0.0]
    p1_status = [0, 0]
    p2_status = [0, 0]
    p1_fainted = [0, 0]
    p2_fainted = [0, 0]

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

        elif t == "-sideend" and "tailwind" in line.lower():
            if parts[2] == "p1":
                tailwind_p1 = 0
            else:
                tailwind_p2 = 0

        elif t == "-fieldstart" and "trickroom" in line.lower():
            trick_room = 1
        elif t == "-fieldend" and "trickroom" in line.lower():
            trick_room = 0

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
            if ": " in side and side.startswith("p1"):
                move_name = norm(parts[3].strip())
                action_id = MOVE_VOCAB.get(move_name, -1)
                if action_id < 0:
                    continue

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
                # Slot del Pokémon que actúa (0 = "a", 1 = "b")
                slot = 0 if side.split(":")[0].endswith("a") else 1
                feats[26] = slot

                species_one_hot(p1_active[0] or "", feats, N_FIXED)
                species_one_hot(p1_active[1] or "", feats, N_FIXED + MAX_SPECIES)
                species_one_hot(p2_active[0] or "", feats, N_FIXED + MAX_SPECIES * 2)
                species_one_hot(p2_active[1] or "", feats, N_FIXED + MAX_SPECIES * 3)

                pairs.append((feats, action_id))

    return pairs


def main():
    with open(LOGS_PATH, encoding="utf-8") as f:
        logs = json.load(f)

    print("Construyendo vocabularios...")
    build_vocabs(logs)

    print(f"\nProcesando {len(logs)} replays...")
    all_states = []
    all_actions = []
    for i, (_, (_, log)) in enumerate(logs.items()):
        if i % 200 == 0:
            print(f"  {i}/{len(logs)}")
        for state, action in parse_log(log):
            all_states.append(state)
            all_actions.append(action)

    print(f"\nTotal pairs: {len(all_states)}")
    if len(all_states) < 1000:
        print("⚠️ Muy pocos datos.")
        return

    X = torch.tensor(np.array(all_states), dtype=torch.float32)
    y = torch.tensor(all_actions, dtype=torch.long)
    print(f"Dataset: X={X.shape}, y={y.shape}")

    model = nn.Sequential(
        nn.Linear(N_FEATURES, 512),
        nn.ReLU(),
        nn.Dropout(0.2),
        nn.Linear(512, 256),
        nn.ReLU(),
        nn.Dropout(0.2),
        nn.Linear(256, N_ACTIONS),
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    loader = DataLoader(TensorDataset(X, y), batch_size=128, shuffle=True)

    EPOCHS = 50
    for epoch in range(EPOCHS):
        total_loss = 0.0
        correct = 0
        total = 0
        for bx, by in loader:
            optimizer.zero_grad()
            logits = model(bx)
            loss = criterion(logits, by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            correct += (logits.argmax(1) == by).sum().item()
            total += len(by)
        acc = correct / total
        print(f"Epoch {epoch+1}/{EPOCHS}: loss={total_loss/len(loader):.4f} acc={acc:.3f}")

    torch.save({
        "state_dict": model.state_dict(),
        "species_vocab": SPECIES_VOCAB,
        "move_vocab": MOVE_VOCAB,
        "n_features": N_FEATURES,
        "n_actions": N_ACTIONS,
    }, OUTPUT_DIR / "bc_model.pt")
    print(f"\n✅ Modelo guardado en {OUTPUT_DIR / 'bc_model.pt'}")


if __name__ == "__main__":
    main()