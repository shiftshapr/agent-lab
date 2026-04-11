#!/usr/bin/env python3
"""
Build a static HTML report comparing raw vs transcripts_corrected episode files.

Aligns raw vs corrected by **timestamp segments** (consecutive lines sharing the
same `[MM:SS]` / `[H:MM:SS]` cue), not by line index — so line-count drift between
files cannot pair unrelated timestamps in one hunk.

Groups change hunks by heuristic confidence (how likely the correction is sound).
Does not call external APIs.

Usage:
  python3 scripts/transcript_raw_vs_corrected_report.py
  python3 scripts/transcript_raw_vs_corrected_report.py --out reports/transcript_diff_review.html
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import re
from difflib import SequenceMatcher
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT / "transcripts"
CORR_DIR = PROJECT / "transcripts_corrected"
OUT_DEFAULT = PROJECT / "reports" / "transcript_raw_vs_corrected_review.html"

# Filler / disfluency tokens often stripped in corrected pass
_FILLER_RE = re.compile(
    r"\b(uh|um|erm|er|ah|hmm|hm|like)\b",
    re.IGNORECASE,
)

# episode_001_<11-char YouTube id> filenames
_YT_FROM_LABEL = re.compile(r"^episode_\d+_([a-zA-Z0-9_-]{11})$")
_TS_IN_LINE = re.compile(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]")


def _youtube_id_from_label(label: str) -> str | None:
    m = _YT_FROM_LABEL.match(label.strip())
    return m.group(1) if m else None


def _first_timestamp_seconds(lines: list[str]) -> int | None:
    """First [MM:SS] or [H:MM:SS] in any line → seconds (for YouTube start=)."""
    for line in lines:
        m = _TS_IN_LINE.search(line)
        if not m:
            continue
        g1, g2, g3 = m.group(1), m.group(2), m.group(3)
        if g3 is not None:
            return int(g1) * 3600 + int(g2) * 60 + int(g3)
        return int(g1) * 60 + int(g2)
    return None


def _format_ts_human(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _safe_dom_id(label: str, hunk_index: int) -> str:
    raw = f"{label}__{hunk_index}"
    return "h-" + re.sub(r"[^A-Za-z0-9_-]", "-", raw)


def _line_body(line: str) -> str:
    """Text after [MM:SS] or [H:MM:SS] prefix."""
    m = re.match(r"^\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]\s*(.*)$", line.rstrip("\n"))
    if m:
        return (m.group(4) or "").strip()
    return line.strip()


def _similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _confidence_tier(
    raw_lines: list[str],
    corr_lines: list[str],
) -> tuple[str, int, str]:
    """
    Returns (tier, score_0_100, reason_snippet).
    tier: high | medium | low
    """
    raw_text = " ".join(_line_body(x) for x in raw_lines)
    corr_text = " ".join(_line_body(x) for x in corr_lines)
    sim = _similarity(raw_text, corr_text)

    raw_fillers = len(_FILLER_RE.findall(raw_text))
    corr_fillers = len(_FILLER_RE.findall(corr_text))
    filler_removed = raw_fillers > corr_fillers

    len_r = len(raw_text)
    len_c = len(corr_text)
    ratio = len_c / len_r if len_r else 1.0

    # Score blend
    score = int(sim * 70 + (20 if filler_removed and sim > 0.7 else 0) + (10 if ratio > 0.85 else 0))
    score = max(0, min(100, score))

    if sim >= 0.92 and (filler_removed or abs(len_c - len_r) <= max(8, len_r // 50)):
        tier = "high"
        why = "Very similar strings"
        if filler_removed:
            why += "; filler/disfluency reduced in corrected"
    elif sim >= 0.75 or (filler_removed and sim >= 0.65):
        tier = "medium"
        why = "Moderate edit; check if meaning preserved"
        if ratio < 0.55:
            why += "; corrected text much shorter — possible over-truncation"
    else:
        tier = "low"
        why = "Large divergence — human review recommended"
        if ratio < 0.6:
            why += "; substantial shortening in corrected"

    return tier, score, why


def _collect_pairs() -> list[tuple[str, Path, Path]]:
    out: list[tuple[str, Path, Path]] = []
    for corr in sorted(CORR_DIR.glob("episode_*.txt")):
        raw = RAW_DIR / corr.name
        if raw.is_file():
            label = corr.stem
            out.append((label, raw, corr))
    return out


_HEAD_BRACKET = re.compile(r"^(\[\d{1,2}:\d{2}(?::\d{2})?\])")


def _bracket_token_to_seconds(tok: str) -> int:
    """'[MM:SS]' or '[H:MM:SS]' → total seconds (same rules as transcript cues)."""
    inner = tok[1:-1]
    parts = [int(x) for x in inner.split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return parts[0] * 60 + parts[1]


def _opening_bracket_token(line: str) -> str | None:
    m = _HEAD_BRACKET.match(line)
    return m.group(1) if m else None


def _ts_segments(lines: list[str]) -> list[dict]:
    """
    Group consecutive lines that share the same opening timestamp token.
    Lines without a leading cue attach to the previous segment if any.
    """
    segments: list[dict] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        tok = _opening_bracket_token(line)
        if tok is None:
            if segments:
                segments[-1]["lines"].append(line)
                segments[-1]["line_end"] = i + 1
            else:
                segments.append(
                    {
                        "sec": -1,
                        "tok": "",
                        "lines": [line],
                        "line_start": i + 1,
                        "line_end": i + 1,
                    }
                )
            i += 1
            continue
        sec = _bracket_token_to_seconds(tok)
        start_ln = i + 1
        chunk = [line]
        i += 1
        while i < n:
            tok2 = _opening_bracket_token(lines[i])
            if tok2 == tok:
                chunk.append(lines[i])
                i += 1
            else:
                break
        segments.append(
            {
                "sec": sec,
                "tok": tok,
                "lines": chunk,
                "line_start": start_ln,
                "line_end": start_ln + len(chunk) - 1,
            }
        )
    return segments


def _hunks(raw_lines: list[str], corr_lines: list[str]) -> list[dict]:
    """
    Diff by timestamp segment (same cue time on both sides), not by line index.
    """
    Rs = _ts_segments(raw_lines)
    Cs = _ts_segments(corr_lines)
    hunks: list[dict] = []
    i = j = 0
    while i < len(Rs) and j < len(Cs):
        r, c = Rs[i], Cs[j]
        if r["sec"] == c["sec"]:
            if r["lines"] != c["lines"]:
                tier, score, why = _confidence_tier(r["lines"], c["lines"])
                hunks.append(
                    {
                        "tag": "replace",
                        "raw_start": r["line_start"],
                        "raw_end": r["line_end"],
                        "corr_start": c["line_start"],
                        "corr_end": c["line_end"],
                        "raw_lines": r["lines"],
                        "corr_lines": c["lines"],
                        "tier": tier,
                        "score": score,
                        "why": why,
                    }
                )
            i += 1
            j += 1
        elif r["sec"] < c["sec"]:
            tier, score, why = _confidence_tier(r["lines"], [])
            cs = c["line_start"]
            hunks.append(
                {
                    "tag": "delete",
                    "raw_start": r["line_start"],
                    "raw_end": r["line_end"],
                    "corr_start": cs,
                    "corr_end": cs,
                    "raw_lines": r["lines"],
                    "corr_lines": [],
                    "tier": tier,
                    "score": score,
                    "why": why,
                }
            )
            i += 1
        else:
            tier, score, why = _confidence_tier([], c["lines"])
            rs = r["line_start"]
            hunks.append(
                {
                    "tag": "insert",
                    "raw_start": rs,
                    "raw_end": rs,
                    "corr_start": c["line_start"],
                    "corr_end": c["line_end"],
                    "raw_lines": [],
                    "corr_lines": c["lines"],
                    "tier": tier,
                    "score": score,
                    "why": why,
                }
            )
            j += 1
    tail_corr = len(corr_lines) if corr_lines else 1
    tail_raw = len(raw_lines) if raw_lines else 1
    while i < len(Rs):
        r = Rs[i]
        tier, score, why = _confidence_tier(r["lines"], [])
        hunks.append(
            {
                "tag": "delete",
                "raw_start": r["line_start"],
                "raw_end": r["line_end"],
                "corr_start": tail_corr,
                "corr_end": tail_corr,
                "raw_lines": r["lines"],
                "corr_lines": [],
                "tier": tier,
                "score": score,
                "why": why,
            }
        )
        i += 1
    while j < len(Cs):
        c = Cs[j]
        tier, score, why = _confidence_tier([], c["lines"])
        hunks.append(
            {
                "tag": "insert",
                "raw_start": tail_raw,
                "raw_end": tail_raw,
                "corr_start": c["line_start"],
                "corr_end": c["line_end"],
                "raw_lines": [],
                "corr_lines": c["lines"],
                "tier": tier,
                "score": score,
                "why": why,
            }
        )
        j += 1
    return hunks


# Static client script for the review page (selection, export, lazy YouTube).
COMPARE_PAGE_SCRIPT = """
<script>
(function () {
  'use strict';
  var LS = 'bride-transcript-compare-v3';
  var saveTimer = null;
  var persistClearTimer = null;

  function b64ToUtf8(b64) {
    var binary = atob(b64);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new TextDecoder('utf-8').decode(bytes);
  }

  /** Debounced typing — silent so the status line does not flash every keystroke. */
  function saveState() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      saveTimer = null;
      flushSave(true);
    }, 80);
  }

  function persistHint(msg) {
    var el = document.getElementById('persist-status');
    if (!el) return;
    if (persistClearTimer) clearTimeout(persistClearTimer);
    el.textContent = msg;
    persistClearTimer = setTimeout(function () {
      el.textContent = '';
    }, 2500);
  }

  function restoreState() {
    var raw = null;
    try { raw = localStorage.getItem(LS); } catch (e) {}
    if (!raw) return;
    var state = {};
    try { state = JSON.parse(raw); } catch (e) { return; }
    document.querySelectorAll('article.hunk').forEach(function (art) {
      var key = art.getAttribute('data-hunk-key');
      if (!key || !state[key]) return;
      var cb = art.querySelector('.impl-chk');
      var ta = art.querySelector('textarea.impl-text');
      if (cb) cb.checked = !!state[key].c;
      if (ta && typeof state[key].t === 'string') ta.value = state[key].t;
    });
  }

  function ensureIframe(details) {
    if (details.dataset.loaded === '1') return;
    var vid = details.dataset.videoId;
    var start = details.dataset.start || '0';
    var mount = details.querySelector('.iframe-mount');
    if (!mount || !vid) return;
    var iframe = document.createElement('iframe');
    iframe.width = '560';
    iframe.height = '315';
    iframe.title = 'YouTube video';
    iframe.loading = 'lazy';
    iframe.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    iframe.setAttribute('allowfullscreen', '');
    iframe.setAttribute(
      'allow',
      'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share'
    );
    iframe.tabIndex = 0;
    iframe.src =
      'https://www.youtube-nocookie.com/embed/' +
      encodeURIComponent(vid) +
      '?start=' +
      encodeURIComponent(start) +
      '&rel=0';
    mount.appendChild(iframe);
    iframe.addEventListener('load', function once() {
      iframe.removeEventListener('load', once);
      try {
        iframe.focus({ preventScroll: false });
      } catch (e) {}
    });
    details.dataset.loaded = '1';
  }

  function originalFromTextarea(ta) {
    if (!ta) return null;
    var b64 = ta.getAttribute('data-orig-b64');
    if (!b64) return null;
    try {
      return b64ToUtf8(b64);
    } catch (e) {
      try {
        return atob(b64);
      } catch (e2) {
        return null;
      }
    }
  }

  function textareaIsEdited(ta) {
    if (!ta) return false;
    var cur = ta.value;
    var orig = originalFromTextarea(ta);
    if (orig === null) return cur.length > 0;
    return cur !== orig;
  }

  /** Include checked rows OR any row where the textarea was edited (never drop edits). */
  function exportPayload() {
    var items = [];
    var nChecked = 0;
    var nEditedOnly = 0;
    document.querySelectorAll('article.hunk').forEach(function (art) {
      var cb = art.querySelector('.impl-chk');
      var ta = art.querySelector('textarea.impl-text');
      var checked = !!(cb && cb.checked);
      var edited = textareaIsEdited(ta);
      if (!checked && !edited) return;
      if (checked) nChecked++;
      if (edited && !checked) nEditedOnly++;
      var key = art.getAttribute('data-hunk-key');
      var ep = art.getAttribute('data-episode');
      var tier = art.getAttribute('data-tier');
      var det = art.querySelector('details.hunk-video');
      var youtubeId =
        (det && det.dataset.videoId) || art.dataset.youtubeId || null;
      var startSeconds = null;
      if (det && det.dataset.start != null && det.dataset.start !== '') {
        startSeconds = parseInt(det.dataset.start, 10);
      } else if (
        art.dataset.blockStart != null &&
        art.dataset.blockStart !== ''
      ) {
        startSeconds = parseInt(art.dataset.blockStart, 10);
      }
      items.push({
        episode: ep,
        hunkKey: key,
        tier: tier,
        implement: checked,
        editedFromReportOriginal: edited,
        implementText: ta ? ta.value : '',
        youtubeId: youtubeId,
        startSeconds: startSeconds
      });
    });
    return {
      source: 'transcript_raw_vs_corrected_review',
      itemCount: items.length,
      checkedCount: nChecked,
      editedButUncheckedCount: nEditedOnly,
      items: items
    };
  }

  function flushSave(silent) {
    if (saveTimer) {
      clearTimeout(saveTimer);
      saveTimer = null;
    }
    var state = {};
    document.querySelectorAll('article.hunk').forEach(function (art) {
      var key = art.getAttribute('data-hunk-key');
      if (!key) return;
      var cb = art.querySelector('.impl-chk');
      var ta = art.querySelector('textarea.impl-text');
      state[key] = { c: !!(cb && cb.checked), t: ta ? ta.value : '' };
    });
    try {
      localStorage.setItem(LS, JSON.stringify(state));
      if (!silent) persistHint('Saved to this browser — safe to refresh.');
    } catch (e) {
      if (!silent)
        persistHint('Could not save (storage full or blocked). Use Download JSON.');
    }
  }

  document.querySelectorAll('details.hunk-video').forEach(function (d) {
    d.addEventListener('toggle', function () {
      if (d.open) ensureIframe(d);
    });
  });

  document.body.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    if (t.classList && t.classList.contains('reset-impl')) {
      var art = t.closest('article.hunk');
      var ta = art && art.querySelector('textarea.impl-text');
      var b64 = ta && ta.getAttribute('data-orig-b64');
      if (ta && b64) {
        try {
          ta.value = b64ToUtf8(b64);
        } catch (e) {
          ta.value = atob(b64);
        }
        flushSave(false);
      }
      return;
    }
    if (t.classList && t.classList.contains('focus-yt')) {
      var det = t.closest('details.hunk-video');
      if (!det) return;
      if (!det.open) det.open = true;
      ensureIframe(det);
      var iframe = det.querySelector('.iframe-mount iframe');
      if (iframe) {
        setTimeout(function () {
          try {
            iframe.focus();
          } catch (e) {}
        }, 400);
      }
    }
  });

  document.addEventListener('change', function (e) {
    if (e.target && e.target.classList && e.target.classList.contains('impl-chk')) saveState();
  });
  document.addEventListener('input', function (e) {
    if (e.target && e.target.classList && e.target.classList.contains('impl-text')) saveState();
  });
  document.addEventListener(
    'focusout',
    function (e) {
      if (
        e.target &&
        e.target.classList &&
        e.target.classList.contains('impl-text')
      )
        flushSave(false);
    },
    true
  );
  window.addEventListener('beforeunload', function () {
    flushSave(true);
  });
  window.addEventListener('pagehide', function () {
    flushSave(true);
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') flushSave(true);
  });

  var btnAll = document.getElementById('btn-sel-all');
  var btnNone = document.getElementById('btn-sel-none');
  var btnLow = document.getElementById('btn-sel-low');
  var btnCopy = document.getElementById('btn-copy-json');
  var fb = document.getElementById('copy-feedback');

  if (btnAll) {
    btnAll.addEventListener('click', function () {
      document.querySelectorAll('article.hunk .impl-chk').forEach(function (c) {
        c.checked = true;
      });
      flushSave(true);
    });
  }
  if (btnNone) {
    btnNone.addEventListener('click', function () {
      document.querySelectorAll('article.hunk .impl-chk').forEach(function (c) {
        c.checked = false;
      });
      flushSave(true);
    });
  }
  if (btnLow) {
    btnLow.addEventListener('click', function () {
      document.querySelectorAll('article.hunk').forEach(function (art) {
        var cb = art.querySelector('.impl-chk');
        if (!cb) return;
        cb.checked = art.getAttribute('data-tier') === 'low';
      });
      flushSave(true);
    });
  }
  if (btnCopy) {
    btnCopy.addEventListener('click', function () {
      flushSave(true);
      var payload = exportPayload();
      var text = JSON.stringify(payload, null, 2);
      var msg =
        'Copied ' +
        payload.itemCount +
        ' item(s)';
      if (payload.editedButUncheckedCount > 0) {
        msg +=
          ' (includes ' +
          payload.editedButUncheckedCount +
          ' where you edited text but did not tick Implement — those were previously dropped; sorry)';
      } else {
        msg += '.';
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          function () {
            if (fb) fb.textContent = msg;
          },
          function () {
            if (fb)
              fb.textContent =
                'Clipboard blocked — open DevTools console for full JSON.';
            try {
              console.log(text);
            } catch (e) {}
          }
        );
      } else if (fb) {
        fb.textContent = 'Clipboard API unavailable.';
      }
    });
  }

  var btnDl = document.getElementById('btn-dl-json');
  if (btnDl) {
    btnDl.addEventListener('click', function () {
      flushSave(true);
      var payload = exportPayload();
      var text = JSON.stringify(payload, null, 2);
      var blob = new Blob([text], { type: 'application/json;charset=utf-8' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'transcript-compare-export.json';
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      if (fb)
        fb.textContent =
          'Downloaded ' + payload.itemCount + ' item(s) as JSON file.';
    });
  }

  restoreState();
})();
</script>
"""


def _build_html(pairs: list[tuple[str, Path, Path]]) -> str:
    episodes_html: list[str] = []
    total_hunks = 0
    by_tier = {"high": 0, "medium": 0, "low": 0}

    for label, raw_path, corr_path in pairs:
        raw_lines = raw_path.read_text(encoding="utf-8", errors="replace").splitlines()
        corr_lines = corr_path.read_text(encoding="utf-8", errors="replace").splitlines()
        hunks = _hunks(raw_lines, corr_lines)
        total_hunks += len(hunks)
        for h in hunks:
            by_tier[h["tier"]] += 1

        # Sort hunks: low first (most urgent), then medium, then high
        order = {"low": 0, "medium": 1, "high": 2}
        hunks_sorted = sorted(hunks, key=lambda x: (order.get(x["tier"], 9), -x["score"]))

        yt_id = _youtube_id_from_label(label)
        blocks: list[str] = []
        for hi, h in enumerate(hunks_sorted):
            tier = h["tier"]
            badge_class = {"high": "tier-high", "medium": "tier-medium", "low": "tier-low"}[tier]
            raw_blk = "\n".join(html.escape(x) for x in h["raw_lines"])
            corr_joined = "\n".join(h["corr_lines"])
            corr_blk = html.escape(corr_joined)
            orig_b64 = base64.b64encode(corr_joined.encode("utf-8")).decode("ascii")
            tag_note = html.escape(h["tag"])
            # Stable across sort order / report regen (not enumerate index — that
            # reused keys and let localStorage paste old edits onto wrong hunks).
            _sig = "\n".join(h["raw_lines"] + h["corr_lines"])[:8000]
            _hid = hashlib.sha1(_sig.encode("utf-8")).hexdigest()[:12]
            hunk_key = f"{label}__r{h['raw_start']}-{h['raw_end']}__c{h['corr_start']}-{h['corr_end']}__{h['tag']}__{_hid}"
            el_id = _safe_dom_id(label, hi)
            start_sec = _first_timestamp_seconds(h["raw_lines"])
            if start_sec is None:
                start_sec = _first_timestamp_seconds(h["corr_lines"])
            ts_hint = _format_ts_human(start_sec)
            start_val = 0 if start_sec is None else start_sec
            data_yt_attr = f' data-youtube-id="{html.escape(yt_id, quote=True)}"' if yt_id else ""
            data_start_attr = (
                f' data-block-start="{start_val}"' if start_sec is not None else ""
            )

            if yt_id and start_sec is not None:
                video_block = f"""
                  <details class="hunk-video" data-video-id="{html.escape(yt_id, quote=True)}" data-start="{start_val}">
                    <summary class="hunk-video-sum">Video at ~{html.escape(ts_hint)} — load player</summary>
                    <div class="hunk-video-inner">
                      <div class="iframe-mount" aria-live="polite"></div>
                      <p class="hunk-video-hint">Click inside the player, then use ← → to jump (YouTube). Use <strong>Focus video</strong> if keys do not respond.</p>
                      <button type="button" class="focus-yt">Focus video for keyboard</button>
                    </div>
                  </details>"""
            elif yt_id:
                video_block = f"""
                  <div class="hunk-video-na">No timestamp in this block — <a href="https://www.youtube.com/watch?v={html.escape(yt_id, quote=True)}" target="_blank" rel="noopener">open episode</a>.</div>"""
            else:
                video_block = """<div class="hunk-video-na">No YouTube id in episode filename.</div>"""

            blocks.append(
                f"""
                <article class="hunk {badge_class}" id="{html.escape(el_id, quote=True)}" data-tier="{tier}" data-hunk-key="{html.escape(hunk_key, quote=True)}" data-episode="{html.escape(label, quote=True)}"{data_yt_attr}{data_start_attr}>
                  <header>
                    <label class="impl-pick"><input type="checkbox" class="impl-chk" autocomplete="off"/> Implement</label>
                    <span class="badge {badge_class}">{tier.upper()}</span>
                    <span class="meta">score {h["score"]} · opcode {tag_note} ·
                    raw lines {h["raw_start"]}–{h["raw_end"]} ·
                    corrected lines {h["corr_start"]}–{h["corr_end"]}</span>
                  </header>
                  <p class="why">{html.escape(h["why"])}</p>
                  <div class="grid">
                    <div class="col">
                      <h4>Raw</h4>
                      <pre>{raw_blk or "(empty)"}</pre>
                    </div>
                    <div class="col impl-col">
                      <h4>Implement as (editable)</h4>
                      <textarea class="impl-text" rows="{max(3, min(16, corr_joined.count(chr(10)) + 3))}" wrap="off" spellcheck="true" data-orig-b64="{orig_b64}">{corr_blk or "(empty)"}</textarea>
                      <button type="button" class="reset-impl" title="Restore original corrected text from report">Restore corrected</button>
                    </div>
                  </div>
                  {video_block}
                </article>
                """
            )

        episodes_html.append(
            f"""
            <section class="episode" id="{html.escape(label, quote=True)}">
              <h2>{html.escape(label)}</h2>
              <p class="filepair"><code>{html.escape(str(raw_path.relative_to(PROJECT)))}</code>
              → <code>{html.escape(str(corr_path.relative_to(PROJECT)))}</code></p>
              <p class="stats">{len(hunks)} change block(s) · raw {len(raw_lines)} lines · corrected {len(corr_lines)} lines</p>
              <div class="hunks">{"".join(blocks) if blocks else "<p class='none'>No line-level differences.</p>"}</div>
            </section>
            """
        )

    toc = "".join(
        f'<li><a href="#{html.escape(lbl, quote=True)}">{html.escape(lbl)}</a></li>'
        for lbl, _, _ in pairs
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Raw vs corrected transcript review — Bride of Charlie</title>
  <style>
    :root {{
      --bg: #0f1419;
      --text: #e7e9ea;
      --muted: #8b98a5;
      --border: #38444d;
      --high: #00ba7c;
      --medium: #f5a623;
      --low: #f4212e;
      --pre: #15202b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      margin: 0;
      padding: 1.5rem clamp(1rem, 4vw, 3rem) 3rem;
      max-width: 1100px;
      margin-inline: auto;
    }}
    h1 {{ font-size: 1.5rem; margin-top: 0; }}
    h2 {{ font-size: 1.15rem; margin-top: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 0.35rem; }}
    h4 {{ margin: 0 0 0.35rem; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }}
    .lead {{ color: var(--muted); font-size: 0.95rem; }}
    .summary {{
      background: var(--pre);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.25rem;
      margin: 1rem 0 2rem;
    }}
    nav ul {{ list-style: none; padding: 0; margin: 0.5rem 0 0; display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; }}
    nav a {{ color: #1d9bf0; }}
    .filepair code {{ font-size: 0.8rem; }}
    .stats {{ color: var(--muted); font-size: 0.85rem; margin: 0.25rem 0 1rem; }}
    .hunk {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem;
      margin-bottom: 1rem;
      background: rgba(21, 32, 43, 0.6);
    }}
    .hunk header {{ display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 1rem; margin-bottom: 0.5rem; }}
    .badge {{
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      letter-spacing: 0.04em;
    }}
    .tier-high .badge.tier-high {{ background: rgba(0, 186, 124, 0.2); color: var(--high); }}
    .tier-medium .badge.tier-medium {{ background: rgba(245, 166, 35, 0.15); color: var(--medium); }}
    .tier-low .badge.tier-low {{ background: rgba(244, 33, 46, 0.15); color: var(--low); }}
    .meta {{ font-size: 0.75rem; color: var(--muted); }}
    .why {{ font-size: 0.85rem; color: #c4cdd6; margin: 0.25rem 0 0.75rem; }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }}
    @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    pre {{
      margin: 0;
      padding: 0.75rem;
      background: var(--pre);
      border-radius: 6px;
      font-size: 0.78rem;
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid var(--border);
    }}
    .none {{ color: var(--muted); font-style: italic; }}
    .impl-toolbar {{
      background: var(--pre);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.25rem;
      margin: 1rem 0 1.5rem;
    }}
    .impl-toolbar-title {{ margin: 0 0 0.5rem; font-size: 1rem; }}
    .impl-toolbar-row {{ display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; align-items: center; margin-bottom: 0.5rem; }}
    .impl-toolbar-row button {{
      font: inherit;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: #1c2732;
      color: var(--text);
      cursor: pointer;
    }}
    .impl-toolbar-row button:hover {{ background: #253341; }}
    #copy-feedback {{ font-size: 0.85rem; color: var(--muted); min-height: 1.2em; }}
    #persist-status {{ font-size: 0.85rem; color: var(--high); min-height: 1.2em; flex: 1 1 12rem; }}
    .impl-toolbar-hint {{ margin: 0; font-size: 0.85rem; color: var(--muted); }}
    .impl-pick {{ display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; cursor: pointer; user-select: none; }}
    .impl-pick input {{ width: 1rem; height: 1rem; }}
    .impl-col textarea.impl-text {{
      width: 100%;
      margin: 0;
      padding: 0.75rem;
      background: #0d1117;
      color: var(--text);
      border-radius: 6px;
      font-size: 0.78rem;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      line-height: 1.45;
      border: 1px solid var(--border);
      resize: vertical;
      min-height: 5rem;
    }}
    .reset-impl {{
      margin-top: 0.35rem;
      font: inherit;
      font-size: 0.75rem;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      border: none;
      background: transparent;
      color: #1d9bf0;
      cursor: pointer;
      text-decoration: underline;
    }}
    .reset-impl:hover {{ color: #4cc3ff; }}
    .hunk-video {{
      margin-top: 1rem;
      border-top: 1px solid var(--border);
      padding-top: 0.75rem;
    }}
    .hunk-video-sum {{
      cursor: pointer;
      font-size: 0.9rem;
      color: #1d9bf0;
      list-style: none;
    }}
    .hunk-video-sum::-webkit-details-marker {{ display: none; }}
    .hunk-video-inner {{ margin-top: 0.75rem; }}
    .iframe-mount iframe {{
      width: 100%;
      max-width: 560px;
      aspect-ratio: 16 / 9;
      height: auto;
      min-height: 200px;
      border: 0;
      border-radius: 8px;
      background: #000;
    }}
    .hunk-video-hint {{ font-size: 0.8rem; color: var(--muted); margin: 0.5rem 0; }}
    .focus-yt {{
      font: inherit;
      font-size: 0.85rem;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: #1c2732;
      color: var(--text);
      cursor: pointer;
    }}
    .focus-yt:hover {{ background: #253341; }}
    .hunk-video-na {{ font-size: 0.85rem; color: var(--muted); margin-top: 0.75rem; }}
    .hunk-video-na a {{ color: #1d9bf0; }}
    footer {{ margin-top: 3rem; font-size: 0.8rem; color: var(--muted); }}
  </style>
</head>
<body>
  <h1>Raw vs corrected transcripts — review</h1>
  <p class="lead">
    Timestamp-aligned diff between <code>transcripts/</code> and <code>transcripts_corrected/</code> (same cue time on each side; line indices can differ).
    Confidence is <strong>heuristic only</strong> (string similarity, filler removal, length): it is not LLM judgment.
    <strong>Low</strong> = please read both columns; <strong>High</strong> = likely minor / cleanup edit.
  </p>
  <div class="summary">
    <strong>Overview</strong><br/>
    Episodes: {len(pairs)} · Total change blocks: {total_hunks}
    · High: {by_tier["high"]} · Medium: {by_tier["medium"]} · Low: {by_tier["low"]}
  </div>
  <nav aria-label="Episodes"><ul>{toc}</ul></nav>
  <div class="impl-toolbar" role="region" aria-label="Implementation queue">
    <p class="impl-toolbar-title">Implementation</p>
    <div class="impl-toolbar-row">
      <button type="button" id="btn-sel-all">Select all</button>
      <button type="button" id="btn-sel-none">Clear all</button>
      <button type="button" id="btn-sel-low">Select low tier only</button>
      <button type="button" id="btn-copy-json">Copy JSON</button>
      <button type="button" id="btn-dl-json">Download JSON</button>
      <span id="copy-feedback"></span>
      <span id="persist-status" class="persist-status" aria-live="polite"></span>
    </div>
    <p class="impl-toolbar-hint">
      <strong>Copy JSON</strong> / <strong>Download JSON</strong> include every block where you ticked <strong>Implement</strong> <em>or</em> changed the right-hand text (edits are never omitted).
      <strong>Implement</strong> marks downstream intent (<code>implement: true</code>). Edits autosave to <code>localStorage</code> (v3 key) for this <strong>exact page URL</strong>. If the right column ever showed the wrong lines after a report refresh, that was stale storage — this version uses stable hunk keys so it should not recur. Opening via <code>file://</code> vs hosted <code>/compare</code> uses different storage. Use <strong>Download JSON</strong> often as a backup.
    </p>
  </div>
  {"".join(episodes_html)}
  {COMPARE_PAGE_SCRIPT}
  <footer>
    Generated by <code>scripts/transcript_raw_vs_corrected_report.py</code>.
    Re-run after transcript updates to refresh this page.
  </footer>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        type=Path,
        default=OUT_DEFAULT,
        help=f"Output HTML path (default: {OUT_DEFAULT})",
    )
    args = ap.parse_args()
    pairs = _collect_pairs()
    if not pairs:
        raise SystemExit(f"No matching episode pairs in {RAW_DIR} / {CORR_DIR}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    html_out = _build_html(pairs)
    args.out.write_text(html_out, encoding="utf-8")
    print(f"Wrote {args.out} ({len(pairs)} episodes)")


if __name__ == "__main__":
    main()
