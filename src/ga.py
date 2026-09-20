# src/ga.py
"""
Algoritmo Genético v2.1 con:
- Inicialización ponderada por usage
- Fitness HÍBRIDO: rivales fijos (ancla) + co-evolución (diversidad)
- Score de roles (con coherencia TR/Tailwind)
- Modelo de islas + migración
- Checkpoint y warm start
- Prints de progreso en cada evaluación
"""
import json
import random
from datetime import datetime
from pathlib import Path

from deap import base, creator, tools

from src.pokemon_pool import construir_pool
from src.simulator import simular_enfrentamiento
from src.fit import (
    cobertura_defensiva,
    sinergia_ofensiva,
    diversidad_de_tipos,
)
from src.roles import score_roles


# ============ CONFIGURACIÓN ============
EQUIPO_SIZE = 6

# Island model
N_ISLAS = 4
POP_POR_ISLA = 12
GENERACIONES_POR_CICLO = 3
N_MIGRANTES = 3

# Evolución
N_GEN = 20
CXPB = 0.6
MUTPB = 0.5

# Rivales FIJOS (ancla al meta real)
N_RIVALES_FIJOS = 5
N_BATALLAS_FIJOS = 2

# Co-evolución (rivales de la población)
N_RIVALES_POBLACION = 12
N_BATALLAS_COEVOLUCION = 1

# Pesos del fitness (suman 1.0)
PESO_WINRATE_FIJO = 0.40
PESO_WINRATE_POBLACION = 0.30
PESO_ROLES = 0.15
PESO_COBERTURA = 0.10
PESO_SINERGIA = 0.05

# Diversidad (Jaccard)
LAMBDA_DIVERSIDAD = 0.8
UMBRAL_SIMILITUD = 0.2

# Warm start
USE_WARM_START = True
WARM_START_N = 0    # 0 = no reinyectar elites (evita dominancia)

# Archivos
CHECKPOINT_FILE = Path("data/processed/checkpoint.json")
ELITES_FILE = Path("data/processed/ga_elites.json")
RESULT_FILE = Path("data/processed/ga_result.json")
HISTORY_FILE = Path("data/processed/ga_history.json")

SEED = 47
random.seed(SEED)


# ============ DATOS GLOBALES ============
POOL = construir_pool()
N_POOL = len(POOL)

with open("data/processed/sample_teams.json", encoding="utf-8") as f:
    RIVALES_FIJOS = json.load(f)


# ============ GENOMA Y FITNESS ============
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)


def crear_individuo():
    """Crea un equipo aleatorio PONDERADO POR USAGE."""
    pesos = [max(p.get("usage_pct", 0), 0.1) + 0.5 for p in POOL]
    seleccionados = []
    keys_usados = set()
    intentos = 0

    while len(seleccionados) < EQUIPO_SIZE and intentos < 200:
        idx = random.choices(range(N_POOL), weights=pesos, k=1)[0]
        key = POOL[idx]["species_key"]
        if key not in keys_usados:
            keys_usados.add(key)
            seleccionados.append(idx)
        intentos += 1

    while len(seleccionados) < EQUIPO_SIZE:
        idx = random.randrange(N_POOL)
        if POOL[idx]["species_key"] not in keys_usados:
            keys_usados.add(POOL[idx]["species_key"])
            seleccionados.append(idx)

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


def evaluar_hibrido(individuo, poblacion, verbose=False):
    """
    Fitness v2.1 HÍBRIDO:
      - winrate vs rivales fijos (ancla al meta real)
      - winrate vs población (co-evolución)
      - score_roles + estructura
    """
    equipo = [POOL[i] for i in individuo]

    # --- 1. Rivales FIJOS ---
    n_fijos = min(N_RIVALES_FIJOS, len(RIVALES_FIJOS))
    rivales_fijos = random.sample(RIVALES_FIJOS, n_fijos)
    winrates_fijos = []
    for rival in rivales_fijos:
        wr = simular_enfrentamiento(equipo, rival, n_batallas=N_BATALLAS_FIJOS)
        winrates_fijos.append(wr)
    wr_fijo = sum(winrates_fijos) / len(winrates_fijos) if winrates_fijos else 0.0

    # --- 2. Rivales de POBLACIÓN (co-evolución) ---
    rivales_disp = [p for p in poblacion if list(p) != list(individuo)]
    if len(rivales_disp) < N_RIVALES_POBLACION:
        rivales_pob = rivales_disp
    else:
        rivales_pob = random.sample(rivales_disp, N_RIVALES_POBLACION)

    winrates_pob = []
    for rival_ind in rivales_pob:
        rival_eq = [POOL[i] for i in rival_ind]
        wr = simular_enfrentamiento(equipo, rival_eq, n_batallas=N_BATALLAS_COEVOLUCION)
        winrates_pob.append(wr)
    wr_pob = sum(winrates_pob) / len(winrates_pob) if winrates_pob else 0.0

    # --- 3. Componentes estructurales ---
    roles_score = score_roles(equipo)
    cob = cobertura_defensiva(equipo)
    sin = sinergia_ofensiva(equipo)

    fitness = (
        PESO_WINRATE_FIJO * wr_fijo
        + PESO_WINRATE_POBLACION * wr_pob
        + PESO_ROLES * roles_score
        + PESO_COBERTURA * cob
        + PESO_SINERGIA * sin
    )

    if verbose:
        print(f"      wr_fijo={wr_fijo:.1%} | wr_pob={wr_pob:.1%} | "
              f"roles={roles_score:.2f} | cob={cob:.2f} | sin={sin:.2f}")

    return fitness


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
        print(f"⚠️  Checkpoint corrupto: {e}")
        return None


# ============ MAIN ============
def main():
    print(f"Pool: {N_POOL} Pokémon")
    print(f"Islas: {N_ISLAS} × {POP_POR_ISLA} = {N_ISLAS * POP_POR_ISLA} individuos")
    print(f"Generaciones: {N_GEN} | Migración cada {GENERACIONES_POR_CICLO} gen")
    print(f"Rivales fijos: {N_RIVALES_FIJOS} × {N_BATALLAS_FIJOS} batallas")
    print(f"Co-evolución: {N_RIVALES_POBLACION} × {N_BATALLAS_COEVOLUCION} batallas")
    print(f"Pesos: FIJ={PESO_WINRATE_FIJO}, POB={PESO_WINRATE_POBLACION}, "
          f"ROL={PESO_ROLES}, COB={PESO_COBERTURA}, SIN={PESO_SINERGIA}")
    print()

    toolbox = base.Toolbox()
    toolbox.register("individual", crear_individuo)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", cruzar)
    toolbox.register("mutate", mutar)
    toolbox.register("select", tools.selTournament, tournsize=3)

    logbook = tools.Logbook()
    logbook.header = ["gen", "isla", "nevals", "avg", "max"]

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

        if WARM_START_N > 0 and ELITES_FILE.exists():
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

    while gen_global < N_GEN:
        poblacion_snapshot = [ind for isla in islas for ind in isla]

        for idx_isla, isla in enumerate(islas):
            print(f"\n=== Gen {gen_global} | Isla {idx_isla} | Evaluando {len(isla)} ===")

            # ===== Evaluación de la población (padres) =====
            sin_evaluar = [ind for ind in isla if not ind.fitness.valid]
            if sin_evaluar:
                for k, ind in enumerate(sin_evaluar, 1):
                    fit = evaluar_hibrido(ind, poblacion_snapshot)
                    ind.fitness.values = (fit,)
                    equipo = [POOL[i] for i in ind]
                    nombres = ", ".join(p["pokemon"] for p in equipo[:3])
                    print(f"    [Isla {idx_isla}] {k}/{len(sin_evaluar)} | fit={fit:.3f} | {nombres}...")

            aplicar_diversidad(isla)

            avg = sum(ind.fitness.values[0] for ind in isla) / len(isla)
            mx = max(ind.fitness.values[0] for ind in isla)
            logbook.record(gen=gen_global, isla=idx_isla, nevals=len(isla), avg=avg, max=mx)

            # ===== Evolución =====
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

            # ===== Evaluación de hijos =====
            nuevos = [ind for ind in offspring if not ind.fitness.valid]
            if nuevos:
                for j, ind in enumerate(nuevos, 1):
                    fit = evaluar_hibrido(ind, poblacion_snapshot)
                    ind.fitness.values = (fit,)
                    equipo = [POOL[i] for i in ind]
                    nombres = ", ".join(p["pokemon"] for p in equipo[:3])
                    print(f"    [Isla {idx_isla}] hijo {j}/{len(nuevos)} | fit={fit:.3f} | {nombres}...")

            islas[idx_isla] = offspring

            # ===== Resumen isla =====
            validos = [ind for ind in offspring if ind.fitness.valid]
            if validos:
                avg_isla = sum(ind.fitness.values[0] for ind in validos) / len(validos)
                mx_isla = max(ind.fitness.values[0] for ind in validos)
                print(f"    → Isla {idx_isla}: avg={avg_isla:.3f}, max={mx_isla:.3f}")

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
    candidatos = tools.selBest(pop_final, min(10, len(pop_final)))

    print("\n" + "=" * 60)
    print("🏆 TOP 5 EQUIPOS ENCONTRADOS")
    print("=" * 60)

    resultados_top5 = []
    for ind in candidatos:
        equipo = [POOL[i] for i in ind]

        rivales_eval = random.sample(RIVALES_FIJOS, min(len(RIVALES_FIJOS), 10))
        winrates = []
        for rival in rivales_eval:
            wr = simular_enfrentamiento(equipo, rival, n_batallas=3)
            winrates.append(wr)
        wr_fijo = sum(winrates) / len(winrates) if winrates else 0.0

        rivales_pob_eval = random.sample(
            [p for p in pop_final if list(p) != list(ind)],
            min(10, len(pop_final) - 1)
        )
        winrates_pob = []
        for rival_ind in rivales_pob_eval:
            rival_eq = [POOL[i] for i in rival_ind]
            wr = simular_enfrentamiento(equipo, rival_eq, n_batallas=2)
            winrates_pob.append(wr)
        wr_pob = sum(winrates_pob) / len(winrates_pob) if winrates_pob else 0.0

        roles_score = score_roles(equipo)
        cob = cobertura_defensiva(equipo)
        sin = sinergia_ofensiva(equipo)

        fitness_recalculado = (
            PESO_WINRATE_FIJO * wr_fijo
            + PESO_WINRATE_POBLACION * wr_pob
            + PESO_ROLES * roles_score
            + PESO_COBERTURA * cob
            + PESO_SINERGIA * sin
        )

        resultados_top5.append({
            "equipo": equipo,
            "fitness": fitness_recalculado,
            "fitness_evolucion": ind.fitness.values[0],
            "desglose": {
                "winrate_fijo": wr_fijo,
                "winrate_poblacion": wr_pob,
                "score_roles": roles_score,
                "cobertura_defensiva": cob,
                "sinergia_ofensiva": sin,
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
        print(f"  WR_Fijo: {d['winrate_fijo']:.1%} | WR_Pob: {d['winrate_poblacion']:.1%} | "
              f"Roles: {d['score_roles']:.2f} | Cob: {d['cobertura_defensiva']:.2f} | "
              f"Sin: {d['sinergia_ofensiva']:.2f}")
        print(f"  FITNESS rec: {r['fitness']:.3f} | FITNESS evo: {r['fitness_evolucion']:.3f}")

    mejor = resultados_top5[0]

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
            "N_RIVALES_FIJOS": N_RIVALES_FIJOS, "N_BATALLAS_FIJOS": N_BATALLAS_FIJOS,
            "N_RIVALES_POBLACION": N_RIVALES_POBLACION,
            "N_BATALLAS_COEVOLUCION": N_BATALLAS_COEVOLUCION,
            "PESO_WINRATE_FIJO": PESO_WINRATE_FIJO,
            "PESO_WINRATE_POBLACION": PESO_WINRATE_POBLACION,
            "PESO_ROLES": PESO_ROLES,
            "PESO_COBERTURA": PESO_COBERTURA,
            "PESO_SINERGIA": PESO_SINERGIA,
            "LAMBDA_DIVERSIDAD": LAMBDA_DIVERSIDAD, "SEED": SEED,
        },
        "logbook": [dict(r) for r in logbook],
    }
    RESULT_FILE.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

    historial = json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []
    historial.append({
        "timestamp": resultado["timestamp"],
        "fitness": mejor["fitness"],
        "winrate_fijo": mejor["desglose"]["winrate_fijo"],
        "config": resultado["config"],
        "top5_nombres": [
            {"rank": r["rank"], "equipo": [p["pokemon"] for p in r["equipo"]], "fitness": r["fitness"]}
            for r in resultados_top5
        ],
    })
    HISTORY_FILE.write_text(json.dumps(historial, indent=2, ensure_ascii=False), encoding="utf-8")

    elites_previos = json.loads(ELITES_FILE.read_text(encoding="utf-8")) if ELITES_FILE.exists() else []
    candidatos_validos = [ind for ind in pop_final if ind.fitness.valid and len(ind.fitness.values) > 0]
    top_validos = tools.selBest(candidatos_validos, min(5, len(candidatos_validos)))
    nuevos = [
        {"genoma": list(ind), "fitness": ind.fitness.values[0],
         "nombres": [POOL[i]["pokemon"] for i in ind]}
        for ind in top_validos
    ]
    todos = elites_previos + nuevos
    todos.sort(key=lambda x: x["fitness"], reverse=True)
    ELITES_FILE.write_text(json.dumps(todos[:10], indent=2, ensure_ascii=False), encoding="utf-8")

    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    print(f"\n✅ Resultado: {RESULT_FILE}")
    print(f"✅ Historial: {HISTORY_FILE}")
    print(f"✅ Elites: {ELITES_FILE}")
    print(f"💡 Checkpoint borrado (corrida terminada)")


if __name__ == "__main__":
    main()