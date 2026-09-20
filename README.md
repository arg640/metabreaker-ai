# MetaBreaker AI 🎮🤖

**Sistema de IA que genera equipos anti-meta para Pokémon Champions (Reg M-C) usando Algoritmos Genéticos con Co-evolución y Fitness Híbrido.**

## 📋 Descripción

MetaBreaker AI es un sistema completo de optimización combinatoria que:
1. Extrae datos reales del meta desde Pikalytics (270 Pokémon con stats, moves, items y usage).
2. Identifica las debilidades compartidas del Top 20 del meta.
3. Genera equipos optimizados con un **Algoritmo Genético** de islas múltiples.
4. Evalúa los equipos simulando miles de batallas con `poke-env`.
5. Evoluciona los equipos con fitness **híbrido** (rivales fijos + co-evolución).

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│  DATOS: Pikalytics API (270 Pokémon) + Showdown (stats base)│
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  POOL: 135 Pokémon filtrados por usage + forma común        │
│  + habilidades válidas del Dex de Showdown                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  ALGORITMO GENÉTICO v2.1:                                   │
│  - Inicialización ponderada por usage                       │
│  - 4 islas × 12 individuos + migración                      │
│  - Fitness HÍBRIDO:                                         │
│      * 40% winrate vs rivales fijos (ancla)                │
│      * 30% winrate vs población (co-evolución)             │
│      * 15% score de roles (coherencia TR/Tailwind)         │
│      * 10% cobertura defensiva                              │
│      * 5% sinergia ofensiva                                 │
│  - Diversidad Jaccard entre individuos                      │
│  - Checkpoint por generación                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT: Top 5 equipos exportables a Showdown               │
└─────────────────────────────────────────────────────────────┘
```

## 🗺️ Fases del proyecto

- [x] **Fase 0**: Configuración de entorno (poke-env + Showdown local)
- [x] **Fase 1**: Extracción y análisis del meta (Pikalytics)
- [x] **Fase 2**: Representación de equipos y simulación
- [x] **Fase 3**: Algoritmo genético funcional
- [x] **Fase 4**: Fitness anti-meta con SimpleHeuristicsPlayer
- [x] **Fase 5**: Sistema de guardado + warm start
- [x] **Fase 6**: Ampliación del pool a 139 Pokémon
- [x] **Fase v2.0**: Co-evolución + detección de roles
- [x] **Fase v2.1**: Fitness híbrido + fixes (EVs, species_key, roles)
- [ ] **Fase 7**: Validación en Showdown real
- [ ] **Fase 8**: AdvancedHeuristicsPlayer (política de batalla mejorada)

## 🛠️ Stack tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.13 |
| Simulación | poke-env + Pokémon Showdown (local) |
| Algoritmo | DEAP (Distributed Evolutionary Algorithms) |
| Datos | pandas + requests + BeautifulSoup |
| Fuente de datos | Pikalytics API + Showdown Dex |
| Persistencia | JSON (checkpoint, elites, historial) |

## 📁 Estructura del proyecto

```
metabreaker-ai/
├── data/
│   ├── raw/                     # Datos crudos (gitignored)
│   │   ├── pikalytics_full.json
│   │   ├── base_stats.json
│   │   └── valid_abilities.json
│   └── processed/
│       ├── pool_data.json       # Pool de 135 Pokémon
│       ├── sample_teams.json    # 20 equipos rivales del meta
│       ├── ga_result.json       # Resultado del último GA
│       ├── ga_history.json      # Historial de corridas
│       └── ga_elites.json       # Top históricos para warm start
├── src/
│   ├── ga.py                    # Algoritmo Genético principal
│   ├── simulator.py             # Simulación de batallas
│   ├── team_player.py           # Player de poke-env
│   ├── pokemon_pool.py          # Pool + limpieza de equipos
│   ├── pokemon_set.py           # Representación de sets
│   ├── fit.py                   # Componentes de fitness
│   ├── roles.py                 # Detección de roles
│   ├── type_chart.py            # Tabla de efectividad de tipos
│   ├── export_team.py           # Exportar Top 5 a Showdown
│   ├── rebuild_elites.py        # Reconstruir elites si crashea
│   ├── scraper_pikalytics.py    # Scraper de equipos rivales
│   ├── scraper_full.py          # Scraper completo (270 Pokémon)
│   ├── parse_html.py            # Parser de rivales
│   └── parse_api.py             # Parser del pool
├── scripts_fetch_abilities.js   # Extrae habilidades del Dex
├── scripts_fetch_base_stats.js  # Extrae stats base del Dex
├── pokemon-showdown/            # Servidor local (gitignored)
└── venv/                        # Entorno virtual
```

## 🚀 Setup

### Requisitos
- Python 3.10+
- Node.js 18+
- Git

### Instalación

```bash
# 1. Clonar el repo
git clone https://github.com/arg640/metabreaker-ai.git
cd metabreaker-ai

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate      # macOS/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Clonar servidor de Showdown
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown
npm install
cp config/config-example.js config/config.js
```

### Preparar datos

```bash
# 1. Scraper de Pikalytics (270 Pokémon)
python src/scraper_full.py
python src/parse_api.py

# 2. Scraper de equipos rivales
python src/scraper_pikalytics.py
python src/parse_html.py

# 3. Con el servidor de Showdown corriendo:
node scripts_fetch_abilities.js
node scripts_fetch_base_stats.js
```

### Ejecutar el GA

**Terminal 1** (servidor Showdown):
```bash
cd pokemon-showdown
node pokemon-showdown start --no-security
```

**Terminal 2** (GA):
```bash
.\venv\Scripts\activate
$env:PYTHONIOENCODING = "utf-8"
python -u -m src.ga
```

### Exportar equipos

```bash
python -m src.export_team
```

Genera `data/processed/equipo_final_1.txt` ... `equipo_final_5.txt` listos para importar en Showdown.

## 📊 Resultados destacados

| Versión | Mejor winrate | Diversidad Top 5 |
|---|---|---|
| v1.0 (rivales fijos) | 81.7% | 2-3 cores |
| v2.0 (co-evolución) | 85.0% | 4 cores distintos |
| v2.1 (híbrido) | En curso | Esperado: 4-5 |

## 🧠 Conceptos clave

### Co-evolución
Los individuos pelean contra rivales aleatorios de la población actual, no contra rivales fijos. Esto mantiene diversidad pero impide convergencia (Efecto Reina Roja).

### Fitness híbrido
Combina un **ancla absoluta** (rivales fijos) con **co-evolución** (rivales de la población) para tener lo mejor de ambos: convergencia real + diversidad.

### Detección de roles
Analiza los movimientos de cada Pokémon para detectar roles (atacante, soporte, tanque, speed control) y verifica coherencia (Trick Room requiere Pokémon lentos, Tailwind requiere rápidos).

## ⚠️ Limitaciones conocidas

- **Rivales de Pikalytics pueden estar desactualizados** (snapshot de mayo 2026).
- **SimpleHeuristicsPlayer** no usa óptimamente Trick Room, Tailwind o setups.
- **Sin roles "avanzados"**: el sistema no distingue pivot, wallbreaker, cleaner.
- **Solo 20 rivales fijos** en sample_teams.json (limitado).

## 🗺️ Roadmap

1. **AdvancedHeuristicsPlayer** con lógica custom (Tailwind, TR, Fake Out).
2. **Fitness con roles avanzados** (pivot, wallbreaker, cleaner).
3. **Rivales dinámicos** desde Smogon Stats (chaos.json).
4. **Validación en Showdown real** con cuentas secundarias.
5. **Análisis de logs de batalla** para entender decisiones del GA.

## 📜 Licencia

Proyecto académico. Pokémon es una marca registrada de Nintendo/Game Freak/The Pokémon Company.

## 👤 Autor

**Alvaro Rizo** ([@arg640](https://github.com/arg640)) — Estudiante de Ciencia de Datos