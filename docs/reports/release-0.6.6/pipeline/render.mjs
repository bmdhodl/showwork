// Renders scene.html to PNG frames at 2560x1440 through headless system Edge.
//
// playwright-core is not a repo dependency. Install it in a scratch dir:
//   npm init -y && npm i playwright-core
//   PWCORE_DIR=<that dir> ASSETS_DIR=<assets dir> node render.mjs <outDir> [start] [end]
//
// ASSETS_DIR holds fonts/ (Inter Regular, Medium and Bold; JetBrains Mono
// Regular and Bold, as TTF) and ambients/circuit.jpg, a dark background photo.
// A local server maps /assets/* to it, so the scene never reaches the network.

import { createRequire } from "node:module";
import { createServer } from "node:http";
import { mkdirSync, readFileSync, existsSync } from "node:fs";
import { dirname, join, resolve, normalize, extname } from "node:path";
import { fileURLToPath } from "node:url";

const sceneDir = dirname(fileURLToPath(import.meta.url));
const pwDir = process.env.PWCORE_DIR;
const assetsDir = process.env.ASSETS_DIR;
const outDir = process.argv[2];
if (!pwDir || !assetsDir || !outDir) {
  console.error("usage: PWCORE_DIR=... ASSETS_DIR=... node render.mjs <outDir> [start] [end]");
  process.exit(1);
}
const require = createRequire(join(resolve(pwDir), "noop.js"));
const { chromium } = require("playwright-core");
mkdirSync(outDir, { recursive: true });

const TYPES = { ".html": "text/html", ".ttf": "font/ttf", ".jpg": "image/jpeg" };
const server = createServer((req, res) => {
  const path = decodeURIComponent(new URL(req.url, "http://x").pathname);
  // The browser asks for a favicon on its own; the scene has none.
  if (path === "/favicon.ico") { res.writeHead(204).end(); return; }
  const file = path.startsWith("/assets/")
    ? normalize(join(assetsDir, path.slice("/assets/".length)))
    : normalize(join(sceneDir, path));
  if (!(file.startsWith(normalize(assetsDir)) || file.startsWith(normalize(sceneDir))) || !existsSync(file)) {
    res.writeHead(404).end();
    console.error(`404 ${path}`);
    return;
  }
  res.writeHead(200, { "content-type": TYPES[extname(file)] || "application/octet-stream" });
  res.end(readFileSync(file));
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const port = server.address().port;

const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
const failed = [];
page.on("requestfailed", (r) => failed.push(r.url()));
page.on("response", (r) => { if (r.status() >= 400) failed.push(`${r.status()} ${r.url()}`); });
await page.goto(`http://127.0.0.1:${port}/scene.html?render=1`, { waitUntil: "networkidle" });

const USED_FONTS = ['400 22px "Inter"', '500 22px "Inter"', '700 22px "Inter"',
                    '400 22px "JetBrains Mono"', '700 22px "JetBrains Mono"'];
const fontsOk = await page.evaluate(async (fonts) => {
  await Promise.all(fonts.map((f) => document.fonts.load(f)));
  await document.fonts.ready;
  return fonts.every((f) => document.fonts.check(f));
}, USED_FONTS);
if (!fontsOk || failed.length) {
  console.error("Fonts or assets failed to load; no frames rendered.", failed);
  await browser.close(); server.close();
  process.exit(1);
}

const total = await page.evaluate(() => window.TOTAL_FRAMES);
const start = Number(process.argv[3] ?? 0);
const end = Number(process.argv[4] ?? total - 1);
const stage = page.locator("#stage");
const t0 = Date.now();
for (let i = start; i <= end; i++) {
  await page.evaluate((f) => window.seek(f), i);
  const path = join(outDir, `f${String(i).padStart(4, "0")}.png`);
  try {
    await stage.screenshot({ path, animations: "disabled", timeout: 60_000 });
  } catch {
    await stage.screenshot({ path, animations: "disabled", timeout: 60_000 });
  }
  if (i % 100 === 0 || i === end) console.log(`frame ${i}/${end} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
}
await browser.close();
server.close();
console.log("done");
