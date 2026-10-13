# tests/test_type_chart.py
"""Tests de la tabla de efectividad de tipos."""
from src.type_chart import TYPES, debilidades, multiplicador


def test_ice_vs_garchomp_4x():
    """Ice vs Dragon/Ground = 4x (el clásico)."""
    assert multiplicador("ice", ["dragon", "ground"]) == 4.0


def test_electric_vs_ground_immune():
    """Electric vs Ground = 0x (inmunidad)."""
    assert multiplicador("electric", ["ground"]) == 0.0


def test_water_vs_water_grass():
    """Water vs Water/Grass = 0.25x."""
    assert multiplicador("water", ["water", "grass"]) == 0.25


def test_fighting_vs_ghost_immune():
    """Fighting vs Ghost = 0x."""
    assert multiplicador("fighting", ["ghost"]) == 0.0


def test_fairy_vs_dragon_2x():
    assert multiplicador("fairy", ["dragon"]) == 2.0


def test_normal_vs_steel_rock():
    """Normal vs Steel/Rock = 0.25x."""
    assert multiplicador("normal", ["steel", "rock"]) == 0.25


def test_case_insensitive():
    assert multiplicador("FIRE", ["GRASS"]) == 2.0


def test_debilidades_returns_dict():
    d = debilidades(["fire", "flying"])
    assert isinstance(d, dict)
    assert "rock" in d
    assert d["rock"] >= 2.0


def test_all_types_have_entry():
    for atk in TYPES:
        for dfn in TYPES:
            assert isinstance(multiplicador(atk, [dfn]), float)