# src/ga.py
"""
Algoritmo Genético con:
- Island model (3 islas independientes con migración)
- Penalización por similitud (diversidad)
- Mutación alta (0.5)
- Warm start con elites
- Top 5 final ordenado por fitness recalculado
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
# ============ CONFIGURACIÓN ============
EQUIPO_SIZE = 6

# Island model
N_ISLAS = 3
POP_POR_ISLA = 8
GENERACIONES_POR_CICLO = 3
N_MIGRANTES = 2                # <- AÑADIR si falta

# Evolución
N_GEN = 9
CXPB = 0.6
MUTPB = 0.5

# Evaluación
N_BATALLAS_POR_RIVAL = 3       # mi recomendación (era 3)
N_RIVALES = 10
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

# Pesos
PESO_WINRATE = 0.85
PESO_COBERTURA = 0.05
PESO_SINERGIA = 0.05
PESO_DIVERSIDAD = 0.05

# Penalización por similitud (diversidad)
LAMBDA_DIVERSIDAD = 0.5          # 0 = sin penalización, 1 = máxima
UMBRAL_SIMILITUD = 0.3           # a partir de aquí empieza a penalizar

# Warm start
USE_WARM_START = True
WARM_START_N = 3

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


def _gen_aleatorio_libre(keys_usados: set, ya_incluidos: list[int]) -> int | None:
    disponibles = [
        i for i in range(N_POOL)
        if POOL[i]["species_key"] not in keys_usados and i not in ya_incluidos
    ]
    if not disponibles:
        return None
    return random.choice(disponibles)


def _deduplicar(genes: list[int]) -> list[int]:
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


def evaluar_base(individuo):
    """Fitness sin penalización de diversidad."""
    equipo = [POOL[i] for i in individuo]
    winrates = []
    for rival in RIVALES:
        wr = simular_enfrentamiento(equipo, rival, n_batallas=N_BATALLAS_POR_RIVAL)
        winrates.append(wr)
    winrate_meta = sum(winrates) / len(winrates) if winrates else 0.0
    cob = cobertura_defensiva(equipo)
    sin = sinergia_ofensiva(equipo)
    div = diversidad_de_tipos(equipo)
    return PESO_WINRATE * winrate_meta + PESO_COBERTURA * cob + PESO_SINERGIA * sin + PESO_DIVERSIDAD * div


def similitud_jaccard(a: list, b: list) -> float:
    """Similitud de Jaccard entre dos genomas (0 = distintos, 1 = idénticos)."""
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


def aplicar_diversidad(poblacion):
    """
    Ajusta el fitness de cada individuo según su similitud con el resto.
    Modifica fitness.values in-place.
    """
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

        # Penalización: a partir de UMBRAL_SIMILITUD, reducir el fitness
        exceso = max(0.0, sim_promedio - UMBRAL_SIMILITUD)
        factor = max(0.3, 1.0 - LAMBDA_DIVERSIDAD * exceso)

        base = ind.fitness.values[0]
        ind.fitness.values = (base * factor,)


def migrar(islas: list[list], n_migrantes: int):
    """
    Los n mejores de cada isla migran a la siguiente isla (rotación).
    Devuelve la lista de islas modificada.
    """
    migrantes = []
    for isla in islas:
        top = tools.selBest(isla, n_migrantes)
        migrantes.append([creator.Individual(ind) for ind in top])

    # Reasignar: los migrantes de isla i van a isla i+1
    for i, isla in enumerate(islas):
        origen = migrantes[i]
        destino = islas[(i + 1) % len(islas)]
        # Reemplazar los peores n de la isla destino
        peores_idx = sorted(range(len(destino)), key=lambda k: destino[k].fitness.values[0])[:n_migrantes]
        for k, migrante in zip(peores_idx, origen):
            destino[k] = migrante

    return islas


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

    # Crear islas
    islas = [toolbox.population(n=POP_POR_ISLA) for _ in range(N_ISLAS)]

    # Warm start: distribuir elites entre islas
    ruta_elites = Path("data/processed/ga_elites.json")
    if ruta_elites.exists() and USE_WARM_START:
        elites_data = json.loads(ruta_elites.read_text(encoding="utf-8"))
        n_reinyectar = min(len(elites_data), WARM_START_N)
        for k in range(n_reinyectar):
            genoma = elites_data[k]["genoma"]
            if len(genoma) == EQUIPO_SIZE and all(0 <= g < N_POOL for g in genoma):
                isla_destino = islas[k % N_ISLAS]
                isla_destino[k // N_ISLAS] = creator.Individual(genoma)
        print(f"🔥 Warm start: {n_reinyectar} elites reinyectados\n")

    hof = tools.HallOfFame(5)
    logbook = tools.Logbook()
    logbook.header = ["gen", "isla", "nevals", "avg", "max"]

    # Ciclo principal
    gen_global = 0
    for ciclo in range(N_GEN // GENERACIONES_POR_CICLO):
        for gen_local in range(GENERACIONES_POR_CICLO):
            for idx_isla, isla in enumerate(islas):
                # Evaluar
                fitnesses = list(map(evaluar_base, isla))
                for ind, fit in zip(isla, fitnesses):
                    ind.fitness.values = (fit,)

                # Aplicar penalización por diversidad
                aplicar_diversidad(isla)

                # Registrar stats
                avg = sum(ind.fitness.values[0] for ind in isla) / len(isla)
                mx = max(ind.fitness.values[0] for ind in isla)
                logbook.record(gen=gen_global, isla=idx_isla, nevals=len(isla), avg=avg, max=mx)

                hof.update(isla)

                # Siguiente generación (si no es la última del ciclo)
                if gen_local < GENERACIONES_POR_CICLO - 1 or ciclo < (N_GEN // GENERACIONES_POR_CICLO) - 1:
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

                    # Elitismo dentro de cada isla
                    elite = tools.selBest(isla, 1)
                    offspring[-1:] = [toolbox.clone(ind) for ind in elite]

                    islas[idx_isla] = offspring

            gen_global += 1

        # Migración al final del ciclo
        if ciclo < (N_GEN // GENERACIONES_POR_CICLO) - 1:
            islas = migrar(islas, N_MIGRANTES)
            print(f"🔄 Migración tras gen {gen_global}")

    print(logbook.stream)

    # Población combinada final
    pop_final = [ind for isla in islas for ind in isla]
    # Actualizar hof con la población final
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
            "fitness_evolucion": ind.fitness.values[0],
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
    (out_dir / "ga_result.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

    ruta_hist = out_dir / "ga_history.json"
    historial = json.loads(ruta_hist.read_text(encoding="utf-8")) if ruta_hist.exists() else []
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
    ruta_hist.write_text(json.dumps(historial, indent=2, ensure_ascii=False), encoding="utf-8")

    ruta_elites = out_dir / "ga_elites.json"
    elites_previos = json.loads(ruta_elites.read_text(encoding="utf-8")) if ruta_elites.exists() else []
    nuevos = [
        {"genoma": list(ind), "fitness": ind.fitness.values[0],
         "nombres": [POOL[i]["pokemon"] for i in ind]}
        for ind in tools.selBest(pop_final, 5)
    ]
    todos = elites_previos + nuevos
    todos.sort(key=lambda x: x["fitness"], reverse=True)
    ruta_elites.write_text(json.dumps(todos[:10], indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ Resultado: {out_dir / 'ga_result.json'}")
    print(f"✅ Historial: {ruta_hist} ({len(historial)} corridas)")
    print(f"✅ Elites: {ruta_elites}")


if __name__ == "__main__":
    main()