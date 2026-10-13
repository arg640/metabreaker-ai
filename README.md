# MetaBreaker AI 🎮🤖

**Sistema de IA que genera equipos anti-meta para Pokémon Champions (Reg M-C) usando Algoritmos Genéticos con Co-evolución, Fitness Híbrido y Behavior Cloning.**

## 📋 Descripción

MetaBreaker AI es un sistema de optimización combinatoria que busca equipos competitivos para el meta de Pokémon Champions Reg M-C. Combina:

1. **Scraping de datos** del meta actual desde Pikalytics + Dex de Showdown.
2. **Behavior Cloning (BC)**: dos agentes entrenados sobre ~15k replays humanos.
3. **Expert lookup (DAgger)**: KDTree de 139k estados humanos para captura de datos on-policy.
4. **Algoritmo Genético** de islas múltiples con fitness híbrido (rivales fijos + co-evolución).
5. **BattleArena persistente**: event loop único + batallas paralelas para acelerar la simulación.
6. **Exportación** de equipos a formato Showdown.

## 🎯 Estado del proyecto

| Componente | Estado |
|---|---|
| Pipeline de datos (scrapers + parsers) | ✅ Funcional |
| Modelo BC (agente A, seed 47) | ⚠️ Entrenado pero limitado (val_acc ~0.46) |
| Modelo BC (agente B, seed 123) | ⚠️ Entrenado pero limitado (val_acc ~0.46) |
| Expert index (KDTree) | ✅ Funcional (139k estados) |
| Algoritmo Genético (30 gens, 5 islas) | ✅ Corrido completo |
| Resultados del GA | ⚠️ Equipos con buen fitness interno pero no viables en VGC real |
| Tests pytest | ✅ 31/31 passing |
| Configuración central + Makefile | ✅ Completo |

**Problema conocido principal**: el modelo BC usa Protect + Fake Out en ~60% de las decisiones, por lo que el GA aprende a "explotar" al modelo en vez de generar equipos anti-meta reales. Ver sección "Limitaciones" y "Roadmap".

## 🏗️ Arquitectura
┌──────────────────────────────────────────────────────────────┐
│ DATOS: Pikalytics API + Showdown Dex + 15k replays humanos │
└──────────────────────┬───────────────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────────────┐
│ BC TRAINING: 2 modelos independientes (seed 47, seed 123) │
│ + expert_index.pkl (KDTree de estados humanos) │
│ + species_full.json + learnsets.json + valid_items.json │
└──────────────────────┬───────────────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────────────┐
│ ALGORITMO GENÉTICO v2.2: │
│ - Inicialización ponderada por usage │
│ - 5 islas × 10 individuos + migración cada 5 gens │
│ - Fitness HÍBRIDO: │
│ * 35% winrate vs rivales fijos (ancla) │
│ * 30% winrate vs población (co-evolución) │
│ * 15% score de roles (coherencia TR/Tailwind) │
│ * 10% cobertura defensiva │
│ * 10% sinergia ofensiva │
│ - Diversidad Jaccard + elitismo por isla │
│ - BattleArena persistente (event loop único + 5 paralelas) │
│ - Item Clause + Mega Clause (máx 2 megas con piedra) │
│ - Checkpoint por generación │
└──────────────────────┬───────────────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────────────┐
│ OUTPUT: Top 5 equipos exportables a Showdown │
└──────────────────────────────────────────────────────────────┘

## 🗺️ Fases del proyecto

- [x] **Fase 0**: Configuración de entorno (poke-env + Showdown local)
- [x] **Fase 1**: Extracción y análisis del meta (Pikalytics)
- [x] **Fase 2**: Representación de equipos y simulación
- [x] **Fase 3**: Algoritmo genético funcional
- [x] **Fase 4**: Fitness anti-meta con BC + co-evolución
- [x] **Fase 5**: Sistema de guardado + warm start + checkpoint
- [x] **Fase 6**: Ampliación del pool a ~300 Pokémon + 81 megas inyectadas
- [x] **Fase v2.0**: Co-evolución + detección de roles
- [x] **Fase v2.1**: Fitness híbrido + Stat Points de Champions
- [x] **Fase v2.2**: BattleArena persistente + dos agentes independientes
- [x] **Fase v3.0**: Sistema de arquetipos + Item Clause + Mega Clause
- [x] **Fase v3.1**: log_parser unificado + config central + tests + Makefile
- [x] **Fase v3.2**: Validador de learnsets + species resolution (Indeedee-F, Vivillon-*)
- [ ] **Fase 4.0**: Mejora del modelo BC (features + rebalanceo + LSTM) ← **bloqueante**
- [ ] **Fase 5.0**: Validación en Showdown real contra humanos
- [ ] **Fase 6.0**: RL fine-tuning (opcional, a largo plazo)

## 🛠️ Stack tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.10+ |
| Simulación | poke-env + Pokémon Showdown (local) |
| Algoritmo | DEAP |
| Modelo | PyTorch (BC) |
| Expert lookup | scikit-learn KDTree |
| Datos | pandas + requests + BeautifulSoup |
| Fuente de datos | Pikalytics API + Showdown Dex (mod champions) |
| Gráficas | matplotlib |
| Persistencia | JSON (checkpoint, elites, historial) |
| Tests | pytest |

## 📁 Estructura del proyecto
metabreaker-ai/
├── data/
│ ├── raw/ # Datos crudos
│ │ ├── pikalytics_full.json
│ │ ├── base_stats.json
│ │ ├── valid_abilities.json
│ │ ├── valid_items.json # Items del mod champions
│ │ ├── species_full.json # Species + abilities + requiredItem + baseStats
│ │ └── learnsets.json # Moves legales por species
│ └── processed/
│ ├── pool_data.json # Pool filtrado
│ ├── sample_teams.json # Rivales fijos del meta
│ ├── ga_result.json # Resultado del último GA
│ ├── ga_history.json # Historial de corridas
│ ├── ga_elites.json # Top históricos para warm start
│ └── plots/ # PNGs generados por plot_ga_progress
├── models_bc/ # Checkpoints de PyTorch
│ ├── bc_model.pt # Agente A (seed 47)
│ ├── bc_model_2.pt # Agente B (seed 123)
│ └── expert_index.pkl # KDTree de estados humanos
├── scripts/ # Scripts de entrenamiento / análisis
│ ├── init.py
│ ├── bc_train.py # CLI para entrenar BC
│ ├── build_expert_index.py # Construye KDTree para DAgger
│ ├── dagger_check.py # Diagnóstico de datos DAgger
│ ├── dagger_retrain.py # Fine-tuning con DAgger
│ ├── analyze_winner_logs.py # Análisis de moves elegidos por el modelo
│ └── plot_ga_progress.py # Gráficas del GA
├── src/ # Núcleo del proyecto
│ ├── config.py # ⭐ Configuración central
│ ├── ga.py # Algoritmo Genético principal
│ ├── simulator.py # BattleArena persistente
│ ├── neural_player.py # Player con BC + expert lookup
│ ├── log_parser.py # Parser unificado de replays
│ ├── pokemon_pool.py # Pool + limpieza (Species/Item/Mega Clause)
│ ├── pokemon_set.py # PokemonSet + Stat Points de Champions
│ ├── fit.py # Componentes de fitness
│ ├── roles.py # Detección de roles VGC
│ ├── type_chart.py # Tabla de efectividad de tipos
│ ├── export_team.py # Exportar Top 5 a Showdown
│ ├── rebuild_elites.py # Reconstruir elites si el GA crashea
│ ├── scraper_full.py # Scraper Pikalytics (Pikalytics API)
│ ├── scraper_pikalytics.py # Scraper Pikalytics HTML
│ ├── parse_html.py # Parser de rivales del HTML
│ └── parse_api.py # Parser del pool
├── tests/ # Tests con pytest (31 passing)
│ ├── test_type_chart.py
│ ├── test_pokemon_pool.py
│ ├── test_pokemon_set.py
│ └── test_roles.py
├── scripts_fetch_abilities.js # Extrae habilidades válidas del Dex
├── scripts_fetch_base_stats.js # Extrae stats base del Dex
├── scripts_fetch_species_full.js # Extrae abilities + requiredItem + stats
├── scripts_fetch_valid_items.js # Extrae items del mod champions
├── scripts_fetch_learnsets.js # Extrae learnsets por species
├── pokemon-showdown/ # Servidor local (gitignored)
├── pyproject.toml
├── Makefile
├── requirements.txt
└── README.md


## 🚀 Setup

### Requisitos
- Python 3.10+
- Node.js 18+
- Git
- ~15 GB de espacio libre (dataset de replays + modelos)

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
pip install -e .                # Instala src y scripts como paquetes

# 4. Clonar servidor de Showdown
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown
npm install
cp config/config-example.js config/config.js
cd ..
Configurar path de replays humanos
El proyecto usa ~15k replays del meta Champions. Configurá la ruta en variable de entorno:

powershell
# Windows
$env:METABREAKER_HUMAN_LOGS = "C:/ruta/a/tus/replays.json"

# Linux/Mac
export METABREAKER_HUMAN_LOGS="/ruta/a/tus/replays.json"
O editá el default en src/config.py (HUMAN_LOGS_PATH).

Preparar datos
bash
# Con el servidor de Showdown corriendo en otra terminal
python src/scraper_full.py
python src/parse_api.py
python src/scraper_pikalytics.py
python src/parse_html.py

# Scripts de Dex (Node)
node scripts_fetch_abilities.js
node scripts_fetch_base_stats.js
node scripts_fetch_species_full.js
node scripts_fetch_valid_items.js
node scripts_fetch_learnsets.js
Entrenar los dos agentes
bash
# Terminal 1 — servidor Showdown
cd pokemon-showdown
node pokemon-showdown start --no-security

# Terminal 2 — entrenamiento
python -m scripts.bc_train --seed 47  --output models_bc/bc_model.pt
python -m scripts.bc_train --seed 123 --output models_bc/bc_model_2.pt
python -m scripts.build_expert_index
Correr el GA
bash
# Encoding UTF-8 (Windows)
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Lanzar
python -u -m src.ga 2>&1 | Tee-Object -FilePath data\processed\ga_run.log
Exportar equipos y generar gráficas
bash
python -m src.export_team
python -m scripts.plot_ga_progress
Los equipos quedan en data/processed/equipo_final_1.txt ... equipo_final_5.txt, listos para importar en Showdown.

Tests
bash
pytest -v
🧠 Conceptos clave
Behavior Cloning (BC)
Los agentes se entrenan supervisadamente sobre ~139k pares (estado, acción) extraídos de 15k replays humanos del meta Champions. Features: HP, status, fainted, tailwind, TR, weather, terrain, species one-hot, moves vistos, counts.

Expert lookup (DAgger)
Un KDTree sobre 139k estados humanos permite detectar si un estado del bot es "similar" a uno ya visto. Si lo es, se loggea como par DAgger para fine-tuning posterior.

Co-evolución
Los individuos pelean contra rivales aleatorios de la población actual, no solo contra rivales fijos. Mantiene diversidad pero puede llevar a ciclos infinitos (Efecto Reina Roja). Por eso se combina con rivales fijos.

Fitness híbrido
Combina un ancla absoluta (rivales fijos, 35%) con co-evolución (rivales de la población, 30%) para tener convergencia real + diversidad.

Dos agentes independientes
En vez de que un mismo agente se enfrente a sí mismo (self-play, que sesga el fitness), se entrenan dos modelos BC con seeds distintos. El GA enfrenta bc_model.pt contra bc_model_2.pt.

Sistema de Stat Points (Champions)
Champions usa 66 stat points totales, 32 máx por stat. Diferente a EVs clásicos (510 total). Los spreads se asignan por arquetipo detectado: fast_phys, bulky_spec, tr_phys, support, wall_phys, etc.

Item Clause + Mega Clause
Máximo 1 de cada item por equipo.

Máximo 2 megas con piedra por equipo (los no-mega con item requerido no cuentan).

Items requeridos forzados para megas (ej: Raichunite Y para Raichu-Mega-Y).

Species resolution
Pikalytics mezcla formas (Indeedee, Vivillon-, Meowstic-, etc.). El pipeline resuelve:

Indeedee → Indeedee-F o Indeedee-M según los moves aprendidos.

Vivillon-Marine, Vivillon-Fancy, etc. → todos cuentan como la misma especie.

📊 Resultados obtenidos (última corrida)
Configuración final:

Pool: 299 Pokémon (con 81 megas)

5 islas × 10 individuos = 50 por generación

30 generaciones, migración cada 5

5 rivales fijos × 5 batallas + 5 rivales población × 3 batallas

Top 1 (fitness interno 0.711, WR_Fijo 86.7%):

Glimmora / Chandelure / Hydreigon / Kommo-o / Cofagrigus / Sceptile
⚠️ Los equipos generados tienen buen fitness interno pero NO son viables en VGC real. Ver sección de Limitaciones.

⚠️ Limitaciones conocidas
1. El modelo BC es débil y explotable
val_acc ≈ 0.46 (predice el move correcto menos de la mitad de las veces).

Protect (35%) + Fake Out (25%) = 60% de todas las decisiones. El modelo colapsó a "no morir" en vez de "jugar VGC".

Features incompletas: no incluye speed de los activos, matchup type chart, ni historial de turnos.

Arquitectura MLP simple (sin memoria ni atención).

Consecuencia: el GA aprende a explotar los vicios del modelo (equipos raros que "engañan" al BC) en vez de generar equipos que ganen al meta real.

2. Rivales fijos limitados
sample_teams.json tiene ~20 equipos. Con 30 gens × 50 individuos = ~15,000 evaluaciones contra el mismo set, el GA memoriza y sobreajusta.

3. El fitness no castiga la incoherencia VGC
No penaliza múltiples 4x weaknesses al mismo tipo.

No exige respuesta a tipos clave del meta (Fairy, Water, Fire, Ground).

score_roles mira roles pero no arquetipo completo.

4. Sin validación contra humanos
No se ha subido ningún equipo del Top 5 a ladder real. El winrate que reporta el GA es contra otros agentes BC, no contra jugadores.

5. Inestabilidad del servidor Showdown
Con MAX_CONCURRENT_BATTLES=5, tras ~10k batallas el servidor se satura (handshake timeout).

Ocasionalmente aparece WinError 10055 (búfer de sockets agotado) en Windows.

Solución: reiniciar el servidor cada ~10 gens, o bajar MAX_CONCURRENT_BATTLES a 3.

6. Bugs de poke-env con Open Team Sheets
Con accept_open_team_sheet=True, aparece IndexError: list index out of range cuando hay megas en el equipo. Workaround actual: usar accept_open_team_sheet=False.

🗺️ Roadmap
Etapa 1 (inmediata) — Arreglar el modelo BC
Duración: 2-3 días + 2h cómputo.

□ Rebalanceo de clases en bc_train.py: weight = 1/sqrt(freq) en CrossEntropyLoss.
□ Features nuevas (~15 dims): speed de los 4 activos, moves disponibles del Pokémon que actúa, matchup type chart entre los 4 activos.
□ Reentrenar bc_model.pt y bc_model_2.pt.
Métrica de éxito: val_acc de 0.46 → 0.55+, y en moves_histogram.png Protect baja de 35% a 20-25%.

Etapa 2 — Mejorar la arquitectura
Duración: 3-5 días + 3h cómputo.

□ Cambiar MLP por LSTM (2 capas, hidden=256) para capturar secuencia.
□ Data augmentation: espejar replays (p1↔p2) duplica el dataset.
□ Más features: historial de últimos 3 moves, estado de side conditions.
Métrica de éxito: val_acc a 0.60+.

Etapa 3 — Correr el GA con el modelo mejorado
□ Sin tocar el fitness, correr 30 gens con bc_model_v2.
□ Esperado: equipos con Pokémon del meta real (Incineroar, Rillaboom, Flutter Mane, etc.).
□ Ajustar sample_teams.json con 20-30 rivales más del meta actual.
Etapa 4 (opcional, largo plazo) — RL fine-tuning
□ PPO con reward shaping (daño hecho - daño recibido + bonus por KO).
□ Self-play contra pool de oponentes (BC + versiones previas).
□ Requiere GPU con VRAM decente. Duración estimada: 3-6 semanas.
Etapa 5 — Validación real
□ Subir Top 1-3 a una cuenta secundaria de Showdown.
□ Jugar 20-30 partidas en ladder Champions Reg M-C.
□ Reportar winrate real.
❓ Preguntas abiertas de investigación
¿Cuál es el mejor balance entre rivales fijos y co-evolución? Actualmente 35/30. Se probó 40/30, 30/35. No hay conclusión empírica todavía.

¿El BC es suficiente como oponente del GA, o hace falta RL? Hipótesis actual: con BC de val_acc ≥ 0.60, el GA produce equipos viables. Sin datos todavía.

¿Cómo evaluar "VGC viability" sin jugar contra humanos? Propuesta: subir equipos a Showdown y medir winrate real. Falta implementación.

¿Es posible el reward shaping efectivo para VGC dobles con RL? Sin precedentes conocidos.

📜 Licencia
Proyecto académico. Pokémon es una marca registrada de Nintendo / Game Freak / The Pokémon Company.

👤 Autor
Alvaro Rizo (@arg640) — Estudiante de Ciencia de Datos


---

## 📌 Notas para el commit

1. **Revisá que el `gitignore` cubra**:
data/raw/*
data/processed/*
!data/processed/.gitkeep
models_bc/.pt
models_bc/.pkl
pokemon-showdown/
venv/
pycache/
.pytest_cache/
*.pyc


2. **Archivos que SÍ deberían ir al commit**:
- Todo `src/`, `scripts/`, `tests/`
- Los 5 `scripts_fetch_*.js`
- `pyproject.toml`, `Makefile`, `requirements.txt`, `README.md`
- `.gitignore`

3. **Mensaje de commit sugerido**:
refactor: reorganización completa del pipeline + mejoras de robustez

Config central (src/config.py) + Makefile + pyproject.toml

log_parser unificado (elimina duplicación en bc_train, dagger, expert_index)

BattleArena persistente (event loop único + batallas paralelas)

Dos agentes BC independientes (elimina sesgo de self-play)

Sistema de Stat Points de Champions + arquetipos

Item Clause + Mega Clause (máx 2) + validación contra Dex

Species resolution (Indeedee-F, Vivillon-*)

Tests pytest (31 passing)

Script de gráficas del GA

Estado: pipeline completo y funcional. Modelo BC tiene limitaciones
conocidas (val_acc ~0.46, Protect/Fake Out dominan 60% de decisiones).
Roadmap en README para mejora del modelo (Etapas 1-2).