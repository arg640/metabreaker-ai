# src/config.py
"""
Configuración central del proyecto MetaBreaker AI.
Cualquier módulo que necesite una constante o un path la importa de acá.

Ventajas:
- Un solo lugar para cambiar MAX_SPECIES, MAX_ACTIONS, N_FEATURES, etc.
- Si cambiás una dimensión, se propaga a bc_train, neural_player y expert_index.
- Los paths se resuelven a partir del root del proyecto (no hardcodeados).
"""
import os
from pathlib import Path

# ============================================================
# RUTAS BASE
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = DATA_DIR / "ga_logs"
MODELS_DIR = PROJECT_ROOT / "models_bc"

for _d in (RAW_DIR, PROCESSED_DIR, LOGS_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ============================================================
# ARCHIVOS DE DATOS
# ============================================================
PIKALYTICS_FULL = RAW_DIR / "pikalytics_full.json"
BASE_STATS_FILE = RAW_DIR / "base_stats.json"
VALID_ABILITIES_FILE = RAW_DIR / "valid_abilities.json"
VALID_ITEMS_FILE = RAW_DIR / "valid_items.json"
SPECIES_FULL_FILE = RAW_DIR / "species_full.json"

POOL_FILE = PROCESSED_DIR / "pool_data.json"
SAMPLE_TEAMS_FILE = PROCESSED_DIR / "sample_teams.json"
GA_RESULT_FILE = PROCESSED_DIR / "ga_result.json"
GA_HISTORY_FILE = PROCESSED_DIR / "ga_history.json"
GA_ELITES_FILE = PROCESSED_DIR / "ga_elites.json"
CHECKPOINT_FILE = PROCESSED_DIR / "checkpoint.json"

# ============================================================
# MODELOS
# ============================================================
# Agente principal (primer BC)
MODEL_PATH = MODELS_DIR / "bc_model.pt"
# Agente secundario (segundo BC, distinto seed) → elimina sesgo de self-play
MODEL_PATH_2 = MODELS_DIR / "bc_model_2.pt"
# Índice KDTree del experto humano (DAgger)
EXPERT_INDEX_PATH = MODELS_DIR / "expert_index.pkl"

# ============================================================
# LOGS DAgger
# ============================================================
WINNER_LOGS = LOGS_DIR / "winner_logs.jsonl"

# ============================================================
# DATASET HUMANO (replays)
# ============================================================
# Configurable por variable de entorno. Si movés el repo, no hay que tocar código.
HUMAN_LOGS_PATH = Path(os.environ.get(
    "METABREAKER_HUMAN_LOGS",
    "C:/vgc-projects/battle_logs/logs_gen9championsvgc2026regmc.json",
))

# ============================================================
# FORMATO DE BATALLA
# ============================================================
BATTLE_FORMAT = "gen9championsvgc2026regmc"
SHOWDOWN_WS_URL = "ws://localhost:8000/showdown/websocket"

# ============================================================
# DIMENSIONES DE FEATURES
# (idénticas en bc_train, neural_player y build_expert_index)
# ============================================================
MAX_SPECIES = 100
MAX_ACTIONS = 150
N_FIXED = 28
N_SPECIES_BLOCK = MAX_SPECIES * 4
N_MOVES_BLOCK = MAX_ACTIONS
N_COUNT_BLOCK = 4
N_FEATURES = N_FIXED + N_SPECIES_BLOCK + N_MOVES_BLOCK + N_COUNT_BLOCK
N_ACTIONS = MAX_ACTIONS

# ============================================================
# ALGORITMO GENÉTICO
# ============================================================
EQUIPO_SIZE = 6

# Island model
N_ISLAS = 5
POP_POR_ISLA = 10
GENERACIONES_POR_CICLO = 5
N_MIGRANTES = 3

# Evolución
N_GEN = 30
CXPB = 0.65
MUTPB = 0.35

# Rivales FIJOS (ancla al meta real)
N_RIVALES_FIJOS = 5
N_BATALLAS_FIJOS = 5

# Co-evolución (rivales de la población)
N_RIVALES_POBLACION = 5
N_BATALLAS_COEVOLUCION = 3

# Pesos del fitness (suman 1.0)
PESO_WINRATE_FIJO = 0.35
PESO_WINRATE_POBLACION = 0.30
PESO_ROLES = 0.15
PESO_COBERTURA = 0.10
PESO_SINERGIA = 0.10

# Diversidad (Jaccard)
LAMBDA_DIVERSIDAD = 1.2
UMBRAL_SIMILITUD = 0.40

# Warm start (apagado: arrancamos limpio sin elites del run buggeado)
USE_WARM_START = True
WARM_START_N = 3

# Semilla global
SEED = 47

# ============================================================
# SIMULADOR PERSISTENTE
# ============================================================
MAX_CONCURRENT_BATTLES = 5

# ============================================================
# EVALUACIÓN FINAL DEL TOP 5
# ============================================================
TOP_CANDIDATOS = 20
TOP_EVAL_FIJOS = 5
TOP_EVAL_FIJOS_BATALLAS = 3
TOP_EVAL_POB = 5
TOP_EVAL_POB_BATALLAS = 2