// scripts_fetch_learnsets.js
// Extrae los moves legales de cada species del mod champions.
const fs = require("fs");
const path = require("path");

const { Dex } = require("./pokemon-showdown");
const dex = Dex.mod("champions");

const result = {};

for (const species of dex.species.all()) {
    if (!species.exists) continue;
    const ns = species.isNonstandard;
    if (ns === "Past" || ns === "Future" || ns === "CAP"
        || ns === "Custom" || ns === "Unobtainable") continue;

    const learnset = dex.data.Learnsets[species.id];
    if (!learnset) continue;

    const moves = Object.keys(learnset.learnset || {});
    if (moves.length > 0) {
        result[species.name] = moves;
    }
}

const outputPath = path.join("data", "raw", "learnsets.json");
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf-8");

console.log(`✅ Guardado: ${outputPath}`);
console.log(`   Total: ${Object.keys(result).length} species`);
console.log(`   Indeedee (♂): ${result["Indeedee"]?.length || 0} moves`);
console.log(`   Indeedee-F (♀): ${result["Indeedee-F"]?.length || 0} moves`);
console.log(`   Follow Me en Indeedee: ${result["Indeedee"]?.includes("followme")}`);
console.log(`   Follow Me en Indeedee-F: ${result["Indeedee-F"]?.includes("followme")}`);