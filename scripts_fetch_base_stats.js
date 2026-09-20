// scripts_fetch_base_stats.js
// Extrae stats base de cada Pokémon desde el Dex de Showdown (incluye Megas).
const fs = require("fs");
const path = require("path");

const { Dex } = require("./pokemon-showdown");

const dex = Dex.mod("champions");

const result = {};

for (const species of dex.species.all()) {
    if (!species.exists) continue;
    if (!species.baseStats) continue;

    result[species.name] = {
        hp: species.baseStats.hp,
        atk: species.baseStats.atk,
        def: species.baseStats.def,
        spa: species.baseStats.spa,
        spd: species.baseStats.spd,
        spe: species.baseStats.spe,
    };
}

const outputPath = path.join("data", "raw", "base_stats.json");
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf-8");

console.log(`✅ Guardado: ${outputPath}`);
console.log(`   Total: ${Object.keys(result).length} especies`);
console.log(`   Gengar: ${JSON.stringify(result.Gengar)}`);
console.log(`   Gengar-Mega: ${JSON.stringify(result["Gengar-Mega"])}`);
console.log(`   Metagross-Mega: ${JSON.stringify(result["Metagross-Mega"])}`);