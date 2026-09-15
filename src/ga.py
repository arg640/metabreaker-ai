# src/ga.py
"""
Algoritmo Genético con:
- Island model (múltiples islas + migración)
- Diversidad por similitud (Jaccard)
- Checkpoint tras cada generación
- Warm start con elites
- Progreso en tiempo real por individuo
"""
import json
import random
from datetime import datetime
from pathlib import Path

from deap import base, creator, tools

from src.pokemon_pool import construir_pool
from src.simulator import simular_enfrentamiento
from src.fitness_components import (
    cobertura_defensiva,
    sinergia_ofensiva,
    diversidad_de_tipos,
)


# ============ CONFIGURACIÓN ============
EQUIPO_SIZE = 6

# Island model
N_ISLAS = 3
POP_POR_ISLA = 8
GENERACIONES_POR_CICLO = 3
N_MIGRANTES = 2

# Evolución
N_GEN = 9
CXPB = 0.6
MUTPB = 0.5

# Evaluación
N_BATALLAS_POR_RIVAL = 3
N_RIVALES = 20
SEED = 42

# Pesos
PESO_WINRATE = 0.85
PESO_COBERTURA = 0.05
PESO_SINERGIA = 0.05
PESO_DIVERSIDAD = 0.05

# Diversidad
LAMBDA_DIVERSIDAD = 0.5
UMBRAL_SIMILITUD = 0.3

# Warm start
USE_WARM_START = True
WARM_START_N = 3

# Archivos
CHECKPOINT_FILE = Path("data/processed/checkpoint.json")
ELITES_FILE = Path("data/processed/ga_elites.json")
RESULT_FILE = Path("data/processed/ga_result.json")
HISTORY_FILE = Path("data/processed/ga_history.json")

random.seed(SEED)


# ============ DATOS GLOBALES ============
POOL = construir_pool()
N_POOL = len(POOL)

with open("data/processed/sample_teams.json", encoding="utf-8") as f:
    EQUIPOS_META = json.load(f)
RIVALES = EQUIPOS_META[:N_RIVALES]


# ============ GENOMA Y FITNESS ============
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)


def crear_individuo():
    seleccionados = []
    keys_usados = set()
    intentos = 0
    while len(seleccionados) < EQUIPO_SIZE and intentos < 1000:
        idx = random.randrange(N_POOL)
        key = POOL[idx]["species_key"]
        if key not in keys_usados:
            keys_usados.add(key)
            seleccionados.append(idx)
        intentos += 1
    return creator.Individual(seleccionados)


def _gen_aleatorio_libre(keys_usados, ya_incluidos):
    disponibles = [
        i for i in range(N_POOL)
        if POOL[i]["species_key"] not in keys_usados and i not in ya_incluidos
    ]
    if not disponibles:
        return None
    return random.choice(disponibles)


def _deduplicar(genes):
    resultado = []
    keys_usados = set()
    for g in genes:
        key = POOL[g]["species_key"]
        if key not in keys_usados:
            keys_usados.add(key)
            resultado.append(g)
        else:
            nuevo = _gen_aleatorio_libre(keys_usados, resultado)
            if nuevo is not None:
                keys_usados.add(POOL[nuevo]["species_key"])
                resultado.append(nuevo)
    while len(resultado) < EQUIPO_SIZE:
        nuevo = _gen_aleatorio_libre(keys_usados, resultado)
        if nuevo is None:
            break
        keys_usados.add(POOL[nuevo]["species_key"])
        resultado.append(nuevo)
    return resultado


def cruzar(ind1, ind2):
    hijo1, hijo2 = [], []
    for i in range(EQUIPO_SIZE):
        if i < EQUIPO_SIZE // 2:
            hijo1.append(ind1[i])
            hijo2.append(ind2[i])
        else:
            hijo1.append(ind2[i])
            hijo2.append(ind1[i])
    ind1[:] = _deduplicar(hijo1)
    ind2[:] = _deduplicar(hijo2)
    return ind1, ind2


def mutar(individuo, indpb=0.5):
    keys_actuales = {POOL[g]["species_key"] for g in individuo}
    for i in range(len(individuo)):
        if random.random() < indpb:
            key_vieja = POOL[individuo[i]]["species_key"]
            keys_restantes = keys_actuales - {key_vieja}
            nuevo = _gen_aleatorio_libre(keys_restantes, list(individuo))
            if nuevo is not None:
                keys_actuales.discard(key_vieja)
                keys_actuales.add(POOL[nuevo]["species_key"])
                individuo[i] = nuevo
    return (individuo,)


def evaluar_base(individuo, idx=None, total=None, isla_id=None):
    equipo = [POOL[i] for i in individuo]
    winrates = []
    for rival in RIVALES:
        wr = simular_enfrentamiento(equipo, rival, n_batallas=N_BATALLAS_POR_RIVAL)
        winrates.append(wr)
    winrate_meta = sum(winrates) / len(winrates) if winrates else 0.0
    cob = cobertura_defensiva(equipo)
    sin = sinergia_ofensiva(equipo)
    div = diversidad_de_tipos(equipo)

    if idx is not None and total is not None:
        nombres = ", ".join(p["pokemon"] for p in equipo[:3])
        print(f"    [Isla {isla_id}] {idx+1}/{total} | wr={winrate_meta:.1%} | {nombres}...")

    return (
        PESO_WINRATE * winrate_meta
        + PESO_COBERTURA * cob
        + PESO_SINERGIA * sin
        + PESO_DIVERSIDAD * div
    )


def similitud_jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


def aplicar_diversidad(poblacion):
    n = len(poblacion)
    if n < 2:
        return
    for i, ind in enumerate(poblacion):
        similitudes = []
        for j, otro in enumerate(poblacion):
            if i == j:
                continue
            similitudes.append(similitud_jaccard(ind, otro))
        sim_promedio = sum(similitudes) / len(similitudes) if similitudes else 0.0
        exceso = max(0.0, sim_promedio - UMBRAL_SIMILITUD)
        factor = max(0.3, 1.0 - LAMBDA_DIVERSIDAD * exceso)
        base = ind.fitness.values[0]
        ind.fitness.values = (base * factor,)


def _fitness_seguro(ind):
    if ind.fitness.valid and len(ind.fitness.values) > 0:
        return ind.fitness.values[0]
    return float("-inf")


def _clonar_con_fitness(ind):
    nuevo = creator.Individual(list(ind))
    if ind.fitness.valid and len(ind.fitness.values) > 0:
        nuevo.fitness.values = ind.fitness.values
    return nuevo


def migrar(islas, n_migrantes):
    migrantes = []
    for isla in islas:
        validos = [ind for ind in isla if ind.fitness.valid and len(ind.fitness.values) > 0]
        if not validos:
            migrantes.append([])
            continue
        top = tools.selBest(validos, min(n_migrantes, len(validos)))
        migrantes.append([_clonar_con_fitness(ind) for ind in top])

    for i, isla in enumerate(islas):
        origen = migrantes[i]
        if not origen:
            continue
        destino = islas[(i + 1) % len(islas)]
        peores_idx = sorted(range(len(destino)), key=lambda k: _fitness_seguro(destino[k]))[:n_migrantes]
        for k, migrante in zip(peores_idx, origen):
            destino[k] = _clonar_con_fitness(migrante)
    return islas


# ============ CHECKPOINT ============
def guardar_checkpoint(gen_global, ciclo, gen_local, islas):
    estado = {
        "gen_global": gen_global,
        "ciclo": ciclo,
        "gen_local": gen_local,
        "islas": [
            [
                {
                    "genoma": list(ind),
                    "fitness": ind.fitness.values[0]
                    if ind.fitness.valid and len(ind.fitness.values) > 0
                    else None,
                }
                for ind in isla
            ]
            for isla in islas
        ],
    }
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(json.dumps(estado, indent=2), encoding="utf-8")


def cargar_checkpoint():
    if not CHECKPOINT_FILE.exists():
        return None
    try:
        estado = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        islas = []
        for isla_data in estado["islas"]:
            isla = []
            for ind_data in isla_data:
                ind = creator.Individual(ind_data["genoma"])
                if ind_data["fitness"] is not None:
                    ind.fitness.values = (ind_data["fitness"],)
                isla.append(ind)
            islas.append(isla)
        return {
            "gen_global": estado["gen_global"],
            "ciclo": estado["ciclo"],
            "gen_local": estado["gen_local"],
            "islas": islas,
        }
    except Exception as e:
        print(f"⚠️  Checkpoint corrupto, ignorando: {e}")
        return None


# ============ ALGORITMO PRINCIPAL ============
def main():
    print(f"Pool: {N_POOL} Pokémon")
    print(f"Rivales: {N_RIVALES} | Batallas por par: {N_BATALLAS_POR_RIVAL}")
    print(f"Islas: {N_ISLAS} × {POP_POR_ISLA} = {N_ISLAS * POP_POR_ISLA} individuos")
    print(f"Generaciones totales: {N_GEN} | Migración cada {GENERACIONES_POR_CICLO} gen")
    print(f"Mutación: {MUTPB} | Diversidad: λ={LAMBDA_DIVERSIDAD}, umbral={UMBRAL_SIMILITUD}")
    print()

    toolbox = base.Toolbox()
    toolbox.register("individual", crear_individuo)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", cruzar)
    toolbox.register("mutate", mutar)
    toolbox.register("select", tools.selTournament, tournsize=3)

    hof = tools.HallOfFame(5)
    logbook = tools.Logbook()
    logbook.header = ["gen", "isla", "nevals", "avg", "max"]

    # Checkpoint
    estado = cargar_checkpoint()
    if estado and USE_WARM_START:
        islas = estado["islas"]
        gen_global = estado["gen_global"]
        ciclo = estado["ciclo"]
        gen_local = estado["gen_local"]
        print(f"📂 Checkpoint cargado: gen {gen_global}, ciclo {ciclo}, gen_local {gen_local}\n")
    else:
        islas = [toolbox.population(n=POP_POR_ISLA) for _ in range(N_ISLAS)]
        gen_global = 0
        ciclo = 0
        gen_local = 0

        if USE_WARM_START and ELITES_FILE.exists():
            try:
                elites_data = json.loads(ELITES_FILE.read_text(encoding="utf-8"))
                n_reinyectar = min(len(elites_data), WARM_START_N)
                for k in range(n_reinyectar):
                    genoma = elites_data[k]["genoma"]
                    if len(genoma) == EQUIPO_SIZE and all(0 <= g < N_POOL for g in genoma):
                        isla_destino = islas[k % N_ISLAS]
                        isla_destino[k // N_ISLAS] = creator.Individual(genoma)
                print(f"🔥 Warm start: {n_reinyectar} elites reinyectados\n")
            except Exception as e:
                print(f"⚠️  No se pudieron cargar elites: {e}\n")

    # Bucle principal
    while gen_global < N_GEN:
        for idx_isla, isla in enumerate(islas):
            print(f"\n=== Gen {gen_global} | Isla {idx_isla} | Evaluando {len(isla)} ===")

            for k, ind in enumerate(isla):
                fit = evaluar_base(ind, idx=k, total=len(isla), isla_id=idx_isla)
                ind.fitness.values = (fit,)

            aplicar_diversidad(isla)

            avg = sum(ind.fitness.values[0] for ind in isla) / len(isla)
            mx = max(ind.fitness.values[0] for ind in isla)
            logbook.record(gen=gen_global, isla=idx_isla, nevals=len(isla), avg=avg, max=mx)
            hof.update(isla)

            # Evolución
            offspring = toolbox.select(isla, len(isla))
            offspring = [toolbox.clone(ind) for ind in offspring]

            for c1, c2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < CXPB:
                    toolbox.mate(c1, c2)
                    del c1.fitness.values
                    del c2.fitness.values

            for mutant in offspring:
                if random.random() < MUTPB:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values

            elite = tools.selBest(isla, 1)
            offspring[-1:] = [toolbox.clone(ind) for ind in elite]

            islas[idx_isla] = offspring

        gen_global += 1
        gen_local += 1

        guardar_checkpoint(gen_global, ciclo, gen_local, islas)
        print(f"\n💾 Checkpoint guardado (gen {gen_global})")

        if gen_local >= GENERACIONES_POR_CICLO and gen_global < N_GEN:
            islas = migrar(islas, N_MIGRANTES)
            print(f"🔄 Migración tras gen {gen_global}")
            ciclo += 1
            gen_local = 0
            guardar_checkpoint(gen_global, ciclo, gen_local, islas)

    print()
    print(logbook.stream)

    # ============ RESULTADO FINAL ============
    pop_final = [ind for isla in islas for ind in isla]
    hof.update(pop_final)

    candidatos = tools.selBest(pop_final, min(10, len(pop_final)))

    print("\n" + "=" * 60)
    print("🏆 TOP 5 EQUIPOS ENCONTRADOS")
    print("=" * 60)

    resultados_top5 = []
    for ind in candidatos:
        equipo = [POOL[i] for i in ind]
        winrates_rivales = []
        for rival in RIVALES:
            wr = simular_enfrentamiento(equipo, rival, n_batallas=N_BATALLAS_POR_RIVAL)
            winrates_rivales.append(wr)
        wr_meta = sum(winrates_rivales) / len(winrates_rivales) if winrates_rivales else 0.0
        cob = cobertura_defensiva(equipo)
        sin = sinergia_ofensiva(equipo)
        div = diversidad_de_tipos(equipo)
        fitness_recalculado = (
            PESO_WINRATE * wr_meta
            + PESO_COBERTURA * cob
            + PESO_SINERGIA * sin
            + PESO_DIVERSIDAD * div
        )
        resultados_top5.append({
            "equipo": equipo,
            "fitness": fitness_recalculado,
            "fitness_evolucion": ind.fitness.values[0] if ind.fitness.valid else 0.0,
            "desglose": {
                "winrate_meta": wr_meta,
                "cobertura_defensiva": cob,
                "sinergia_ofensiva": sin,
                "diversidad_tipos": div,
            },
        })

    resultados_top5.sort(key=lambda x: x["fitness"], reverse=True)
    resultados_top5 = resultados_top5[:5]

    for i, r in enumerate(resultados_top5, 1):
        r["rank"] = i
        equipo = r["equipo"]
        d = r["desglose"]
        print(f"\n--- #{i} ---")
        for j, p in enumerate(equipo):
            tipos = "/".join(p["types"])
            print(f"  {j+1}. {p['pokemon']:<25} [{tipos}]")
        print(f"  Winrate: {d['winrate_meta']:.1%} | Cob: {d['cobertura_defensiva']:.2f} | "
              f"Sin: {d['sinergia_ofensiva']:.2f} | Div: {d['diversidad_tipos']:.2f}")
        print(f"  FITNESS rec: {r['fitness']:.3f} | FITNESS evo: {r['fitness_evolucion']:.3f}")

    mejor = resultados_top5[0]

    # ============ GUARDAR ============
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    resultado = {
        "timestamp": datetime.now().isoformat(),
        "equipo": mejor["equipo"],
        "fitness": mejor["fitness"],
        "top5": resultados_top5,
        "desglose": mejor["desglose"],
        "config": {
            "N_ISLAS": N_ISLAS, "POP_POR_ISLA": POP_POR_ISLA,
            "N_GEN": N_GEN, "GENERACIONES_POR_CICLO": GENERACIONES_POR_CICLO,
            "N_MIGRANTES": N_MIGRANTES, "CXPB": CXPB, "MUTPB": MUTPB,
            "N_RIVALES": N_RIVALES, "N_BATALLAS_POR_RIVAL": N_BATALLAS_POR_RIVAL,
            "LAMBDA_DIVERSIDAD": LAMBDA_DIVERSIDAD, "SEED": SEED,
        },
        "logbook": [dict(r) for r in logbook],
    }
    RESULT_FILE.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

    historial = json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []
    historial.append({
        "timestamp": resultado["timestamp"],
        "fitness": mejor["fitness"],
        "winrate_meta": mejor["desglose"]["winrate_meta"],
        "config": resultado["config"],
        "top5_nombres": [
            {"rank": r["rank"], "equipo": [p["pokemon"] for p in r["equipo"]], "fitness": r["fitness"]}
            for r in resultados_top5
        ],
    })
    HISTORY_FILE.write_text(json.dumps(historial, indent=2, ensure_ascii=False), encoding="utf-8")

    elites_previos = json.loads(ELITES_FILE.read_text(encoding="utf-8")) if ELITES_FILE.exists() else []
        # Solo individuos con fitness válido
    candidatos_validos = [
        ind for ind in pop_final
        if ind.fitness.valid and len(ind.fitness.values) > 0
    ]
    top_validos = tools.selBest(candidatos_validos, min(5, len(candidatos_validos)))
    nuevos = [
        {"genoma": list(ind), "fitness": ind.fitness.values[0],
         "nombres": [POOL[i]["pokemon"] for i in ind]}
        for ind in top_validos
    ]
    todos = elites_previos + nuevos
    todos.sort(key=lambda x: x["fitness"], reverse=True)
    ELITES_FILE.write_text(json.dumps(todos[:10], indent=2, ensure_ascii=False), encoding="utf-8")

    # Borrar checkpoint al terminar (para que la próxima corrida empiece limpia)
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    print(f"\n✅ Resultado: {RESULT_FILE}")
    print(f"✅ Historial: {HISTORY_FILE} ({len(historial)} corridas)")
    print(f"✅ Elites: {ELITES_FILE}")
    print(f"💡 Checkpoint borrado (corrida terminada)")


if __name__ == "__main__":
    main()