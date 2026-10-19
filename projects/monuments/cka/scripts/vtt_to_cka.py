"""Convert a YouTube auto-caption VTT + info.json into a CKA transcripts_corrected file.

Usage: vtt_to_cka.py VTT INFO_JSON SEQ CANDACE_EP OUT_DIR [--block 30]
Words keep their caption timing; paragraphs start a new [mm:ss] block about every BLOCK seconds
(at a sentence end when possible) and at every chapter start. Music cues are dropped. No words are invented.
"""
import argparse, html, json, re
from pathlib import Path

TS = r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})"


def secs(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def words_from_plain_vtt(text):
    """Cues with distinct text and no word timing: spread each cue's words from its start to the next cue's start."""
    cues = []
    for cue in re.split(r"\n\n+", text):
        m = re.search(TS + r" --> " + TS, cue)
        if not m:
            continue
        body = " ".join(l.strip() for l in cue.split("\n")[1:] if l.strip())
        body = re.sub(r"<[^>]+>", "", body)
        cues.append((secs(*m.groups()[:4]), secs(*m.groups()[4:]), body))
    out = []
    for i, (s, e, body) in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else e
        ws = body.split()
        span = max(nxt - s, 0.1)
        out.extend((s + span * k / max(len(ws), 1), w) for k, w in enumerate(ws))
    return out


def words_from_vtt(text):
    if "<c>" not in text:
        out = words_from_plain_vtt(text)
        return [(t, html.unescape(w)) for t, w in out if not re.fullmatch(r"\[(?:Music|Applause|Laughter|music|applause|laughter)\]", w)]
    out = []
    for cue in re.split(r"\n\n+", text):
        m = re.search(TS + r" --> " + TS, cue)
        if not m:
            continue
        start = secs(*m.groups()[:4])
        lines = cue.split("\n")[1:]
        timed = [l for l in lines if "<c>" in l]
        if not timed:
            continue
        line = timed[-1]
        first = re.match(r"^([^<]*)", line).group(1).strip()
        if first:
            out.extend((start, w) for w in first.split())
        for t, w in re.findall(r"<" + r"(\d{2}:\d{2}:\d{2}\.\d{3})" + r"><c>([^<]*)</c>", line):
            h, mi, rest = t.split(":"); s, ms = rest.split(".")
            for ww in w.split():
                out.append((secs(h, mi, s, ms), ww))
    words = []
    for t, w in out:
        w = html.unescape(w)
        if re.fullmatch(r"\[(?:Music|Applause|Laughter)\]", w, re.I):
            continue
        words.append((t, w))
    return words


def mmss(t):
    t = int(t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]" if h else f"[{m:02d}:{s:02d}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vtt"); ap.add_argument("info"); ap.add_argument("seq", type=int); ap.add_argument("ep")
    ap.add_argument("out"); ap.add_argument("--block", type=int, default=30); ap.add_argument("--note", default="")
    a = ap.parse_args()
    info = json.load(open(a.info))
    words = words_from_vtt(Path(a.vtt).read_text(encoding="utf-8"))
    chapters = info.get("chapters") or [{"start_time": 0, "title": "Start."}]
    starts = [c["start_time"] for c in chapters]
    dur = info["duration_string"]
    date = f"{info['upload_date'][:4]}-{info['upload_date'][4:6]}-{info['upload_date'][6:]}"
    title = info["title"]
    yid = info["id"]
    body, ci, block, bstart = [], -1, [], None

    def flush():
        if block:
            body.append(f"{mmss(bstart)}\n\n" + " ".join(block) + "\n")

    for t, w in words:
        while ci + 1 < len(starts) and t >= starts[ci + 1]:
            flush(); block = []; bstart = None
            ci += 1
            body.append(f"## {chapters[ci]['title']}\n")
        if bstart is None:
            bstart = t
        elif t - bstart >= a.block and block and re.search(r"[.?!]\"?$", block[-1]):
            flush(); block = []; bstart = t
        elif t - bstart >= a.block * 2:
            flush(); block = []; bstart = t
        block.append(w)
    flush()
    fm = [
        "---", f'title: "{title}"', f"cka_seq: {a.seq}", f"monument_ep: {a.seq}", "batch_ep: 1", "host: Candace Owens",
        "channel: @RealCandaceO", f"upload_date: {date}", f'duration: "{dur}"', f"youtube_id: {yid}",
        f"url: https://www.youtube.com/watch?v={yid}", "caption_source: auto:en",
        "source: YouTube auto captions (word timing kept; music cues dropped)", "---", "",
        f"# {title}", "", f"CKA {a.seq} · Monument Ep {a.seq} · Batch 1 · Candace Owens · {date} · {dur}",
        f"https://www.youtube.com/watch?v={yid}",
        "Source: auto:en; paragraph merge only (no lexicon pass yet; name corrections are applied by apply_name_corrections.py). Music cues dropped. No invented words." + (f" {a.note}" if a.note else ""),
        "", "## Chapters", "",
    ] + [f"- {mmss(c['start_time'])} {c['title']}" for c in chapters] + [""]
    out = Path(a.out) / f"episode_{a.seq:03d}_{yid}.md"
    out.write_text("\n".join(fm) + "\n" + "\n".join(body), encoding="utf-8")
    print(out, len(words), "words")


if __name__ == "__main__":
    main()
