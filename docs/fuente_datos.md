# Fuente de datos: Pikalytics

## URL del meta actual
https://www.pikalytics.com/pokedex

## Formato de la Regulación
Pokémon Champions VGC 2026 Regulation Set M-C

## Endpoint JSON
❌ No existe.

## Estructura del HTML (confirmada)
- Top 20: `<a class="tournament-top20-card" data-name="...">` con rank, nombre y % de uso.
- Equipos de muestra: `<div class="team-pokemon-card">` con moves, item, ability, EVs.
- NO hay `<table>`; todo es `<div>` + clases CSS.

## Estrategia
1. Parsear la página principal → Top 20 + equipos de muestra.
2. Scrapear páginas individuales `/pokedex/gen9championsvgc2026regmc/{Pokemon}` para stats detalladas (opcional, fase 1.5).

## Estado
- [x] Investigación de red.
- [x] Confirmado HTML con datos.
- [x] Scraper funcional.
- [x] Primera inspección del HTML.
- [ ] Parser definitivo del HTML → CSV.