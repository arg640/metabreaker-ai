# tests/test_pokemon_set.py
"""Tests de PokemonSet: spreads, natures, formato Showdown."""
from src.pokemon_set import (
    PokemonSet,
    _clasificar_arquetipo,
    _spread_de,
)


def _mk(nombre, moves):
    return {"pokemon": nombre, "moves": [{"name": m} for m in moves]}


def test_spread_total_66_sp():
    """Todos los spreads deben sumar exactamente 66 stat points."""
    ejemplos = [
        _mk("Rillaboom", ["Grassy Glide", "Wood Hammer", "U-turn", "Fake Out"]),
        _mk("Flutter Mane", ["Moonblast", "Shadow Ball", "Icy Wind", "Protect"]),
        _mk("Iron Hands", ["Fake Out", "Drain Punch", "Wild Charge", "Detect"]),
        _mk("Porygon2", ["Trick Room", "Ice Beam", "Recover", "Thunderbolt"]),
        _mk("Amoonguss", ["Spore", "Rage Powder", "Pollen Puff", "Protect"]),
        _mk("Incineroar", ["Fake Out", "Flare Blitz", "Knock Off", "Parting Shot"]),
    ]
    for p in ejemplos:
        sp, _ = _spread_de(p)
        total = sum(sp.values())
        assert total == 66, f"{p['pokemon']} tiene {total} SP, debería ser 66"


def test_trick_room_arquetipo():
    """Porygon2 con TR debe clasificar como tr_* (lento + special)."""
    p = _mk("Porygon2", ["Trick Room", "Ice Beam", "Recover", "Thunderbolt"])
    arq = _clasificar_arquetipo(p)
    assert arq.startswith("tr_"), f"Esperaba tr_*, obtuve {arq}"


def test_fast_phys_arquetipo():
    """Rillaboom (Atk alto + Velocidad decente) -> fast_phys."""
    p = _mk("Rillaboom", ["Grassy Glide", "Wood Hammer", "U-turn", "Fake Out"])
    arq = _clasificar_arquetipo(p)
    assert arq in ("fast_phys", "bulky_phys")


def test_to_showdown_format():
    s = PokemonSet(
        species="Rillaboom",
        moves=["Grassy Glide", "Wood Hammer"],
        item="Assault Vest",
        ability="Grassy Surge",
        nature="Adamant",
        stat_points={"HP": 32, "Atk": 32, "SpD": 2},
    )
    txt = s.to_showdown()
    assert "Rillaboom @ Assault Vest" in txt
    assert "Ability: Grassy Surge" in txt
    assert "Adamant Nature" in txt
    assert "- Grassy Glide" in txt
    assert "- Wood Hammer" in txt
    assert "EVs:" in txt


def test_from_dict_basico():
    data = {
        "pokemon": "Flutter Mane",
        "types": ["fairy", "ghost"],
        "moves": [
            {"name": "Moonblast", "type": "fairy"},
            {"name": "Shadow Ball", "type": "ghost"},
        ],
        "item": "Booster Energy",
        "ability": "Protosynthesis",
    }
    s = PokemonSet.from_dict(data)
    assert s.species == "Flutter Mane"
    assert s.item == "Booster Energy"
    assert s.ability == "Protosynthesis"
    assert "Moonblast" in s.moves
    assert sum(s.stat_points.values()) == 66


def test_nombre_truncado():
    """Nombres >18 chars se truncan para Showdown."""
    s = PokemonSet(
        species="AReallyLongSpeciesNameHere",
        moves=["Tackle"],
    )
    txt = s.to_showdown()
    first_line = txt.split("\n")[0]
    # El nombre (sin item) debe ser <= 18
    assert len(first_line) <= 18