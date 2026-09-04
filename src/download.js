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

const MAX_ATTEMPTS = Number(env("MAX_ATTEMPTS", "5"));
const BATCH_SIZE = Number(env("BATCH_SIZE", "2"));
const BATCH_PAUSE_MS = Number(env("BATCH_PAUSE_MS", "4000"));
const PAUSE_BETWEEN_INSTRUMENTS_MS = Number(env("INSTRUMENT_PAUSE_MS", "30000"));

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

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

const isRateLimit = (error) => {
  const message = String(error?.message || error || "");
  return message.includes("429") || /too many requests/i.test(message);
};

async function fetchWithRetry(instrument) {
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      return await getHistoricalRates({
        instrument,
        dates: { from, to },
        timeframe,
        priceType,
        volumes,
        format,
        utcOffset: 0,
        retryCount: 10,
        pauseBetweenRetriesMs: 15000,
        useCache: true,
        cacheFolderPath: ".dukascopy-cache",
        batchSize: BATCH_SIZE,
        pauseBetweenBatchesMs: BATCH_PAUSE_MS,
      });
    } catch (error) {
      const rateLimited = isRateLimit(error);
      const last = attempt === MAX_ATTEMPTS;

      console.error(
        `تلاش ${attempt}/${MAX_ATTEMPTS} برای ${instrument} شکست خورد` +
          `${rateLimited ? " (429 - rate limit)" : ""}: ${error?.message || error}`
      );

      if (last) throw error;

      const waitMs = attempt * attempt * 60000;
      console.error(`${Math.round(waitMs / 1000)} ثانیه صبر می‌کنیم...`);
      await sleep(waitMs);
    }
  }
}

async function run() {
  await fs.mkdir(outDir, { recursive: true });
  console.log(`بازه: ${iso(from)} -> ${iso(to)} | تایم‌فریم: ${timeframe}`);

  for (const [index, instrument] of instruments.entries()) {
    if (index > 0) {
      console.log(`${PAUSE_BETWEEN_INSTRUMENTS_MS / 1000} ثانیه وقفه بین نمادها...`);
      await sleep(PAUSE_BETWEEN_INSTRUMENTS_MS);
    }

    try {
      console.log(`دانلود ${instrument} ...`);
      const data = await fetchWithRetry(instrument);

      const ext = format === "csv" ? "csv" : "json";
      const file = path.join(
        outDir,
        `${instrument}_${timeframe}_${iso(from)}_${iso(to)}.${ext}`
      );
      const body = typeof data === "string" ? data : JSON.stringify(data);
      await fs.writeFile(file, body, "utf8");

      const bytes = Buffer.byteLength(body, "utf8");
      console.log(`${file} (${(bytes / 1024 / 1024).toFixed(2)} MB)`);
    } catch (error) {
      console.error(`خطا در ${instrument}:`, error?.message || error);
      process.exitCode = 1;
    }
  }
}

run();
