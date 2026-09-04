import { getHistoricalRates } from "dukascopy-node";
import fs from "node:fs/promises";
import path from "node:path";
import { DEFAULT_INSTRUMENTS } from "./instruments.js";

const env = (key, fallback) => process.env[key]?.trim() || fallback;

const instruments = env("INSTRUMENTS", DEFAULT_INSTRUMENTS.join(","))
  .split(",")
  .map((item) => item.trim().toLowerCase())
  .filter(Boolean);

const timeframe = env("TIMEFRAME", "tick");
const format = env("FORMAT", "csv");
const priceType = env("PRICE_TYPE", "bid");
const volumes = env("VOLUMES", "true") === "true";
const outDir = env("OUT_DIR", "data");

// اگر بازه داده نشود، دیروز (UTC) دانلود می‌شود
function defaultRange() {
  const to = new Date();
  to.setUTCHours(0, 0, 0, 0);
  const from = new Date(to);
  from.setUTCDate(from.getUTCDate() - 1);
  return { from, to };
}

const fromEnv = env("FROM");
const toEnv = env("TO");
const { from, to } =
  fromEnv && toEnv
    ? { from: new Date(fromEnv), to: new Date(toEnv) }
    : defaultRange();

const iso = (value) => value.toISOString().slice(0, 10);

async function run() {
  await fs.mkdir(outDir, { recursive: true });
  console.log(`بازه: ${iso(from)} → ${iso(to)} | تایم‌فریم: ${timeframe}`);

  for (const instrument of instruments) {
    try {
      console.log(`⬇️  دانلود ${instrument} ...`);
      const data = await getHistoricalRates({
        instrument,
        dates: { from, to },
        timeframe,
        priceType,
        volumes,
        format,
        utcOffset: 0,
        retryCount: 5,
        pauseBetweenRetriesMs: 3000,
        useCache: true,
        cacheFolderPath: ".dukascopy-cache",
        batchSize: 5,
        pauseBetweenBatchesMs: 1500,
      });

      const ext = format === "csv" ? "csv" : "json";
      const file = path.join(
        outDir,
        `${instrument}_${timeframe}_${iso(from)}_${iso(to)}.${ext}`
      );
      const body = typeof data === "string" ? data : JSON.stringify(data);
      await fs.writeFile(file, body, "utf8");

      const bytes = Buffer.byteLength(body, "utf8");
      console.log(`✅ ${file} (${(bytes / 1024 / 1024).toFixed(2)} MB)`);
    } catch (error) {
      console.error(`❌ خطا در ${instrument}:`, error?.message || error);
      process.exitCode = 1;
    }
  }
}

run();
