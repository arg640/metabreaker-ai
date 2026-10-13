// scripts_fetch_valid_items.js
// Extrae los ítems válidos del mod "champions" de Showdown.
// Escribe el JSON en UTF-8 (evita el BOM de PowerShell).
const fs = require("fs");
const path = require("path");

const { Dex } = require("./pokemon-showdown");

const dex = Dex.mod("champions");

const result = [];

for (const item of dex.items.all()) {
    if (!item.exists) continue;
    const ns = item.isNonstandard;
    if (ns === "Past" || ns === "Future" || ns === "CAP"
        || ns === "Custom" || ns === "Unobtainable") {
        continue;
    }
    result.push(item.name);
}

result.sort();

const outputPath = path.join("data", "raw", "valid_items.json");
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf-8");

console.log(`✅ Guardado: ${outputPath}`);
console.log(`   Total: ${result.length} ítems`);
console.log(`   Assault Vest está? ${result.includes("Assault Vest")}`);
console.log(`   Sitrus Berry está? ${result.includes("Sitrus Berry")}`);
console.log(`   Life Orb está?     ${result.includes("Life Orb")}`);
console.log(`   Focus Sash está?   ${result.includes("Focus Sash")}`);
console.log(`   Booster Energy está? ${result.includes("Booster Energy")}`);