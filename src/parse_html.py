# src/parse_html.py
"""
Parsea el HTML de Pikalytics y produce tres archivos:
1. data/processed/meta_top20.csv      -> Top 20 con % de uso
2. data/processed/sample_teams.json   -> Equipos de muestra (JSON)
3. data/processed/pokemon_freq.csv    -> Frecuencia de cada Pokémon en equipos
"""
import json
from pathlib import Path
from collections import Counter
import pandas as pd
from bs4 import BeautifulSoup

HTML_PATH = Path("data/raw/pikalytics_regmc.html")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_top20(soup: BeautifulSoup) -> pd.DataFrame:
    """Extrae el Top 20 de Pokémon con rank y % de uso."""
    registros = []
    for card in soup.find_all("a", class_="tournament-top20-card"):
        rank = card.find("span", class_="tournament-top20-rank")
        name = card.find("span", class_="tournament-top20-name")
        usage = card.find("span", class_="tournament-top20-usage")
        if not (rank and name and usage):
            continue
        registros.append({
            "rank": int(rank.text.strip()),
            "pokemon": name.text.strip(),
            "usage_pct": float(usage.text.strip().rstrip("%")),
        })
    return pd.DataFrame(registros).sort_values("rank").reset_index(drop=True)


def parse_team_card(card) -> dict | None:
    """Extrae un Pokémon completo de un team-pokemon-card."""
    name_el = card.find(class_="team-pokemon-name")
    if not name_el:
        return None

    # Nombre: el texto directo del <a>, no el del avatar
    nombre = name_el.get_text(strip=True)

    # Tipos
    tipos = [t.text.strip() for t in card.find_all(class_="team-pokemon-types")[0].find_all("span")] \
            if card.find(class_="team-pokemon-types") else []

    # Props (Ability, Item)
    ability, item = None, None
    for row in card.find_all(class_="team-pokemon-prop-row"):
        label = row.find(class_="team-prop-label")
        val = row.find(class_="team-prop-val-text")
        if not (label and val):
            continue
        label_txt = label.text.strip().lower()
        if label_txt == "ability":
            ability = val.text.strip()
        elif label_txt == "item":
            item = val.text.strip()

    # Movimientos
    moves = []
    for entry in card.find_all(class_="team-move-entry"):
        m_name = entry.find(class_="team-move-name")
        m_type = entry.find(class_="team-move-type")
        if m_name:
            moves.append({
                "name": m_name.text.strip(),
                "type": m_type.text.strip().lower() if m_type else None,
            })

    return {
        "pokemon": nombre,
        "types": tipos,
        "ability": ability,
        "item": item,
        "moves": moves,
    }


def parse_sample_teams(soup: BeautifulSoup) -> list[list[dict]]:
    """Extrae todos los equipos de muestra. Cada equipo tiene 6 Pokémon."""
    # Cada equipo de muestra está en un contenedor padre de team-pokemon-card.
    # En Pikalytics suelen ser 20 equipos de 6 Pokémon = 120 cards.
    all_cards = soup.find_all("div", class_="team-pokemon-card")
    print(f"Total de team-pokemon-card encontrados: {len(all_cards)}")

    equipos = []
    # Agrupamos de 6 en 6 (asumiendo que vienen en orden)
    # Más robusto: buscar contenedores padre. Probamos por ahora el agrupamiento simple.
    for i in range(0, len(all_cards), 6):
        bloque = all_cards[i:i + 6]
        equipo = [parse_team_card(c) for c in bloque]
        equipo = [p for p in equipo if p]  # limpia None
        if len(equipo) == 6:
            equipos.append(equipo)

    return equipos


def main():
    html = HTML_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # 1) Top 20
    df_top20 = parse_top20(soup)
    ruta_top20 = OUT_DIR / "meta_top20.csv"
    df_top20.to_csv(ruta_top20, index=False, encoding="utf-8")
    print(f"✅ Top 20 guardado en {ruta_top20}")
    print(df_top20.to_string(index=False))

    # 2) Equipos de muestra
    equipos = parse_sample_teams(soup)
    ruta_teams = OUT_DIR / "sample_teams.json"
    ruta_teams.write_text(json.dumps(equipos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ {len(equipos)} equipos guardados en {ruta_teams}")

    # 3) Frecuencia de Pokémon en equipos
    freq = Counter()
    for equipo in equipos:
        for p in equipo:
            freq[p["pokemon"]] += 1
    df_freq = pd.DataFrame(
        [{"pokemon": k, "apariciones": v} for k, v in freq.most_common()],
    )
    ruta_freq = OUT_DIR / "pokemon_freq.csv"
    df_freq.to_csv(ruta_freq, index=False, encoding="utf-8")
    print(f"\n✅ Frecuencia guardada en {ruta_freq}")
    print(df_freq.head(15).to_string(index=False))


if __name__ == "__main__":
    main()