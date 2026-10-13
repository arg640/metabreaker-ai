# tests/test_pokemon_pool.py
"""Tests de limpieza de equipo: Species Clause, Item Clause, Mega Clause."""
from collections import Counter

from src.pokemon_pool import (
    _es_mega_stone,
    construir_pool,
    limpiar_equipo,
    species_key,
)


def _mk(nombre, types=None, item="", moves=None, ability=""):
    return {
        "pokemon": nombre,
        "types": types or ["normal"],
        "item": item,
        "moves": moves or [{"name": "Tackle", "type": "normal"}],
        "ability": ability,
    }


def test_species_clause():
    equipo = [_mk("Rillaboom"), _mk("Rillaboom"), _mk("Incineroar")]
    resultado = limpiar_equipo(equipo)
    assert len(resultado) == 2
    nombres = [p["pokemon"] for p in resultado]
    assert nombres == ["Rillaboom", "Incineroar"]


def test_species_key_colapsa_sexo():
    """Las formas -M / -F deben colapsar al mismo species_key."""
    assert species_key("Indeedee-F") == species_key("Indeedee-M")


def test_pool_sin_duplicados_de_species_key():
    """
    Verifica que el pool real (data/processed/pool_data.json) no tenga dos
    Pokémon con el mismo species_key. Si esto falla, el GA podría meter
    duplicados en un mismo equipo sin darse cuenta.
    """
    pool = construir_pool()
    keys = [species_key(p["pokemon"]) for p in pool]
    dup = {k: c for k, c in Counter(keys).items() if c > 1}
    assert not dup, f"species_key duplicados en el pool: {dup}"


def test_item_clause_basico():
    equipo = [
        _mk("Rillaboom", item="Sitrus Berry"),
        _mk("Incineroar", item="Sitrus Berry"),
    ]
    resultado = limpiar_equipo(equipo)
    items = [p.get("item", "") for p in resultado if p.get("item")]
    assert len(items) == len(set(items)), f"Items repetidos: {items}"


def test_item_obligatorio_si_falta():
    equipo = [_mk("Rillaboom"), _mk("Incineroar")]
    resultado = limpiar_equipo(equipo)
    for p in resultado:
        assert p.get("item"), f"{p['pokemon']} sin item asignado"


def test_mega_stone_detection():
    assert _es_mega_stone("Gengarite")
    assert _es_mega_stone("Charizardite Y")
    assert _es_mega_stone("Metagrossite")
    assert not _es_mega_stone("Sitrus Berry")
    assert not _es_mega_stone("")
    assert not _es_mega_stone("Assault Vest")


def test_mega_clause_max_dos():
    """Máximo 2 megas con piedra por equipo."""
    equipo = [
        _mk("Charizard-Mega-Y", item="Charizardite Y"),
        _mk("Gengar-Mega", item="Gengarite"),
    ]
    resultado = limpiar_equipo(equipo)
    megas = [p for p in resultado if _es_mega_stone(p.get("item", ""))]
    assert len(megas) <= 2, f"Hay {len(megas)} megas, debería ser ≤2"


def test_mega_clause_descarta_tercera():
    """Si hay 3 megas, la tercera se descarta entera."""
    equipo = [
        _mk("Charizard-Mega-Y", item="Charizardite Y"),
        _mk("Gengar-Mega", item="Gengarite"),
        _mk("Raichu-Mega-Y", item="Raichunite Y"),
    ]
    resultado = limpiar_equipo(equipo)
    nombres = [p["pokemon"] for p in resultado]
    assert "Raichu-Mega-Y" not in nombres, (
        f"Raichu-Mega-Y debería haberse descartado (ya había 2 megas): {nombres}"
    )


def test_equipo_vacio():
    assert limpiar_equipo([]) == []