from src.pokemon_set import PokemonSet

test = {
    "pokemon": "Floette-Eternal",
    "types": ["fairy"],
    "ability": "Flower Veil",
    "item": "Floettite",
    "moves": [
        {"name": "Moonblast", "type": "fairy"},
        {"name": "Dazzling Gleam", "type": "fairy"},
        {"name": "Calm Mind", "type": "psychic"},
        {"name": "Protect", "type": "normal"},
    ],
}

ps = PokemonSet.from_dict(test)
print(ps.to_showdown())