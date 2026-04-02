#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Fetch YouTube transcript via TranscriptAPI (same as TranscriptAPI docs).
 * Usage (from agent-lab root) — **URL or id is required** (no default video):
 *   node scripts/fetch-transcriptapi-transcript.mjs "https://youtu.be/VIDEO_ID"
 *   node scripts/fetch-transcriptapi-transcript.mjs --quiet "URL"
 *   node scripts/fetch-transcriptapi-transcript.mjs dQw4w9WgXcQ
 *
 * Always writes:
 *   data/transcripts/youtube/<video_id>.txt   (timestamped lines)
 *   data/transcripts/youtube/<video_id>.json  (raw API: transcript array + meta)
 *
 * Uses TRANSCRIPT_API_KEY or API_KEY from the environment, or reads agent-lab/.env
 * for those keys (no npm dotenv required).
 */
function loadEnvFile(envPath) {
  if (!fs.existsSync(envPath)) return;
  const raw = fs.readFileSync(envPath, "utf8");
  for (const line of raw.split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const eq = t.indexOf("=");
    if (eq < 1) continue;
    const k = t.slice(0, eq).trim();
    let v = t.slice(eq + 1).trim();
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    if (!process.env[k]) process.env[k] = v;
  }
}

loadEnvFile(path.join(__dirname, "..", ".env"));

const args = process.argv.slice(2);
const quiet = args.includes("--quiet");
const posArgs = args.filter((a) => a !== "--quiet");
const API_KEY = process.env.TRANSCRIPT_API_KEY || process.env.API_KEY;
const rawTarget = posArgs[0];

if (!rawTarget || rawTarget.startsWith("-")) {
  console.error(
    "Usage: node scripts/fetch-transcriptapi-transcript.mjs [--quiet] <youtube-url|video-id>"
  );
  console.error(
    "  No default video — you must pass a URL or 11-character id (costs one TranscriptAPI request per run)."
  );
  process.exit(1);
}

/** Normalize bare 11-char id to watch URL for the API. */
function toVideoUrl(target) {
  const t = String(target).trim();
  if (/^[a-zA-Z0-9_-]{11}$/.test(t)) {
    return `https://www.youtube.com/watch?v=${t}`;
  }
  return t;
}

const videoUrl = toVideoUrl(rawTarget);

function youtubeVideoIdFromUrl(input) {
  try {
    const u = new URL(input);
    if (u.hostname === "youtu.be") return u.pathname.slice(1).split("/")[0] || null;
    if (u.searchParams.get("v")) return u.searchParams.get("v");
  } catch {
    /* ignore */
  }
  const m = String(input).match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  return m ? m[1] : null;
}

if (!API_KEY) {
  console.error("Set TRANSCRIPT_API_KEY or API_KEY in the environment.");
  process.exit(1);
}

const url =
  "https://transcriptapi.com/api/v2/youtube/transcript?" +
  new URLSearchParams({ video_url: videoUrl, format: "json" });

const res = await fetch(url, {
  headers: { Authorization: `Bearer ${API_KEY}` },
  signal: AbortSignal.timeout(180_000),
});

const text = await res.text();
if (!res.ok) {
  console.error("HTTP", res.status, text);
  process.exit(1);
}

let data;
try {
  data = JSON.parse(text);
} catch {
  console.error("Non-JSON response:", text.slice(0, 500));
  process.exit(1);
}

const transcript = data.transcript;
if (!Array.isArray(transcript)) {
  console.error("Unexpected shape:", Object.keys(data));
  process.exit(1);
}

function fmt(seconds) {
  const s = Math.floor(Number(seconds));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  if (h > 0) return `${String(h).padStart(2, "0")}:${String(mm).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  return `${String(mm).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

const linesOut = [];
for (const entry of transcript) {
  const line = String(entry.text ?? "").replace(/\n/g, " ");
  linesOut.push(`[${fmt(entry.start)}] ${line}`);
}

const videoId = youtubeVideoIdFromUrl(videoUrl) || "unknown_id";
const outDir = path.join(__dirname, "..", "data", "transcripts", "youtube");
fs.mkdirSync(outDir, { recursive: true });
const base = path.join(outDir, videoId);
const txtPath = `${base}.txt`;
const jsonPath = `${base}.json`;

fs.writeFileSync(txtPath, linesOut.join("\n") + "\n", "utf8");
fs.writeFileSync(
  jsonPath,
  JSON.stringify(
    {
      video_id: videoId,
      video_url: videoUrl,
      fetched_at: new Date().toISOString(),
      line_count: transcript.length,
      transcript,
    },
    null,
    2
  ),
  "utf8"
);

console.error(`Saved: ${txtPath}`);
console.error(`Saved: ${jsonPath}`);
console.error(`--- lines: ${transcript.length}`);
if (!quiet) {
  for (const L of linesOut) console.log(L);
}
