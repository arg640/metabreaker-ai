// scripts_fetch_abilities.js
// Extrae las habilidades válidas de cada Pokémon desde el Dex de Showdown.
// Escribe directamente el JSON en UTF-8 (evita el BOM de PowerShell).
const fs = require("fs");
const path = require("path");

const { Dex } = require("./pokemon-showdown");

const dex = Dex.mod("champions");

const result = {};

for (const species of dex.species.all()) {
    if (!species.exists) continue;

    const abilities = [];
    if (species.abilities) {
        for (const key of ["0", "1", "H", "S"]) {
            if (species.abilities[key]) {
                abilities.push(species.abilities[key]);
            }
        }
    }

    if (abilities.length > 0) {
        result[species.name] = abilities;
    }
}

const outputPath = path.join("data", "raw", "valid_abilities.json");
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf-8");

console.log(`✅ Guardado: ${outputPath}`);
console.log(`   Total: ${Object.keys(result).length} especies`);
console.log(`   Rillaboom: ${JSON.stringify(result.Rillaboom)}`);
console.log(`   Basculegion: ${JSON.stringify(result.Basculegion)}`);
console.log(`   Golisopod: ${JSON.stringify(result.Golisopod)}`);