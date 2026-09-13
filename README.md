# MetaBreaker AI 🎮🤖

IA que genera equipos anti-meta para Pokémon Champions (Reg M-C), usando datos reales de Pikalytics, simulación con Pokémon Showdown y algoritmos genéticos.

## 📋 Descripción

Este proyecto construye un sistema que:
1. Extrae estadísticas de uso del meta actual desde Pikalytics.
2. Identifica las debilidades compartidas del Top 20.
3. Genera equipos optimizados para explotar esas debilidades.
4. Evalúa los equipos simulando batallas contra equipos reales del meta.
5. Evoluciona los equipos con un algoritmo genético.

## Fases
- [x] Fase 0: Configuración del entorno
- [x] Fase 1: Extracción y análisis del meta
- [x] Fase 2: Representación y simulación
- [x] Fase 3: Algoritmo genético funcional
- [x] Fase 4: Fitness anti-meta + heurísticas
- [ ] Fase 5: Refinamiento y validación

## Resultados destacados

### Fase 4 — Equipo anti-meta (66.7% winrate vs 3 rivales top)
- Arcanine-Hisui, Annihilape, Whimsicott, Incineroar, Glimmora-Mega, Scovillain-Mega
- 3 Pokémon con Fire (satura debilidad del meta)
- 1 con Fighting (segundo tipo clave)
- Sintetizado por el GA en 3 generaciones

## 🛠️ Stack tecnológico

- **Python 3.13**: Lenguaje principal
- **poke-env**: Cliente Python para Pokémon Showdown
- **pandas**: Análisis de datos
- **BeautifulSoup**: Web scraping
- **DEAP**: Algoritmos genéticos (pendiente)
- **Pokémon Showdown (local)**: Simulador de batallas

## 📁 Estructura del proyecto
