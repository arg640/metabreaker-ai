// scripts_fetch_species_full.js
// Extrae TODO lo que necesitamos de cada species del mod champions:
// abilities válidas, item requerido, base stats.
const fs = require("fs");
const path = require("path");

const { Dex } = require("./pokemon-showdown");

const dex = Dex.mod("champions");
const result = {};

for (const species of dex.species.all()) {
    if (!species.exists) continue;

    const ns = species.isNonstandard;
    if (ns === "Past" || ns === "Future" || ns === "CAP"
        || ns === "Custom" || ns === "Unobtainable") {
        continue;
    }

    const abilities = [];
    if (species.abilities) {
        for (const key of ["0", "1", "H", "S"]) {
            if (species.abilities[key]) {
                abilities.push(species.abilities[key]);
            }
        }
    }

    result[species.name] = {
        abilities: abilities,
        requiredItem: species.requiredItem || null,
        baseSpecies: species.baseSpecies || species.name,
        baseStats: species.baseStats ? {
            hp: species.baseStats.hp,
            atk: species.baseStats.atk,
            def: species.baseStats.def,
            spa: species.baseStats.spa,
            spd: species.baseStats.spd,
            spe: species.baseStats.spe,
        } : null,
    };
}

const outputPath = path.join("data", "raw", "species_full.json");
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf-8");

console.log(`✅ Guardado: ${outputPath}`);
console.log(`   Total: ${Object.keys(result).length} species\n`);
console.log("Ejemplos clave:");
for (const nombre of ["Raichu", "Raichu-Mega-Y", "Gengar", "Gengar-Mega", "Charizard", "Charizard-Mega-Y"]) {
    if (result[nombre]) {
        console.log(`  ${nombre}:`, JSON.stringify(result[nombre], null, 2));
    } else {
        console.log(`  ${nombre}: ⚠️ NO EXISTE en el Dex`);
    }
}