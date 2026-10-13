# tests/test_roles.py
"""Tests de detección de roles y score."""
from src.roles import detectar_roles, score_roles


def _mk(nombre, moves):
    return {"pokemon": nombre, "moves": [{"name": m} for m in moves]}


def test_fake_out_es_soporte():
    p = _mk("Incineroar", ["Fake Out", "Flare Blitz", "Knock Off", "Parting Shot"])
    roles = detectar_roles(p)
    assert "soporte" in roles
    assert "atacante" in roles


def test_tailwind_es_speed_control():
    p = _mk("Talonflame", ["Tailwind", "Brave Bird", "Flare Blitz", "Protect"])
    roles = detectar_roles(p)
    assert "speed_control" in roles


def test_trick_room_es_speed_control():
    p = _mk("Porygon2", ["Trick Room", "Ice Beam", "Recover", "Thunderbolt"])
    roles = detectar_roles(p)
    assert "speed_control" in roles


def test_tanque_protect_mas_recovery():
    p = _mk("Corviknight", ["Roost", "Protect", "Brave Bird", "Body Press"])
    roles = detectar_roles(p)
    assert "tanque" in roles


def test_sin_moves_no_roles():
    p = {"pokemon": "Rillaboom", "moves": []}
    assert detectar_roles(p) == set()


def test_score_roles_equipo_vacio():
    """Equipo sin soporte ni speed control debe puntuar bajo."""
    equipo = [
        _mk(f"Fake{i}", ["Tackle", "Tackle", "Tackle", "Tackle"])
        for i in range(6)
    ]
    score = score_roles(equipo)
    assert 0.0 <= score <= 0.5, f"Score inesperado: {score}"


def test_score_roles_equipo_coherente():
    """Equipo con soporte + TR + lentos debe puntuar más alto."""
    equipo = [
        _mk("Incineroar", ["Fake Out", "Flare Blitz", "Knock Off", "Parting Shot"]),
        _mk("Porygon2", ["Trick Room", "Ice Beam", "Recover", "Thunderbolt"]),
        _mk("Iron Hands", ["Fake Out", "Drain Punch", "Wild Charge", "Detect"]),
        _mk("Amoonguss", ["Spore", "Rage Powder", "Pollen Puff", "Protect"]),
        _mk("Ursaluna", ["Headlong Rush", "Facade", "Protect", "Swords Dance"]),
        _mk("Torkoal", ["Eruption", "Heat Wave", "Protect", "Yawn"]),
    ]
    score = score_roles(equipo)
    assert score >= 0.4, f"Score demasiado bajo: {score}"