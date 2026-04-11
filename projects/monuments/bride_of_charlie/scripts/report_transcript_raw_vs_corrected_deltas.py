#!/usr/bin/env python3
"""
For each episode transcript pair, compare raw vs corrected text grouped by
timestamp (all lines sharing the same [mm:ss] / [h:mm:ss] are concatenated).

Reports:
  - Timestamps present in both where |len(raw_join) - len(corr_join)| >= threshold
  - Timestamps only in raw or only in corrected (count + sample)

Does not assume equal line counts.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "transcripts"
CORR = PROJECT / "transcripts_corrected"

LINE_RE = re.compile(r"^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)$")


def ts_to_seconds(ts: str) -> int:
    parts = [int(p) for p in ts.split(":")]
    if len(parts) == 2:
        m, s = parts
        return m * 60 + s
    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    raise ValueError(ts)


def fmt_ts(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def parse(path: Path) -> list[tuple[int, str, int]]:
    out: list[tuple[int, str, int]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = LINE_RE.match(line)
        if not m:
            continue
        ts, body = m.group(1), m.group(2)
        out.append((ts_to_seconds(ts), body, lineno))
    return out


def by_timestamp(lines: list[tuple[int, str, int]]) -> dict[int, tuple[str, int, int]]:
    """ts_sec -> (joined bodies with space, first_lineno, last_lineno)."""
    groups: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for ts_sec, body, lineno in lines:
        groups[ts_sec].append((lineno, body))
    out: dict[int, tuple[str, int, int]] = {}
    for ts_sec, pairs in groups.items():
        pairs.sort(key=lambda x: x[0])
        first_ln = pairs[0][0]
        last_ln = pairs[-1][0]
        joined = " ".join(b for _, b in pairs)
        out[ts_sec] = (joined, first_ln, last_ln)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--threshold",
        type=int,
        default=60,
        help="Minimum absolute character delta (raw vs corrected) to print (default 60).",
    )
    ap.add_argument(
        "--top",
        type=int,
        default=40,
        help="Max delta rows to print per episode (sorted by |delta|).",
    )
    args = ap.parse_args()

    for raw_path in sorted(RAW.glob("episode_*.txt")):
        corr_path = CORR / raw_path.name
        if not corr_path.is_file():
            print(f"\n=== {raw_path.name} ===\n  [skip] no matching file in transcripts_corrected/")
            continue

        raw_map = by_timestamp(parse(raw_path))
        corr_map = by_timestamp(parse(corr_path))
        raw_ts = set(raw_map)
        corr_ts = set(corr_map)
        both = raw_ts & corr_ts
        only_raw = sorted(raw_ts - corr_ts)
        only_corr = sorted(corr_ts - raw_ts)

        deltas: list[tuple[int, int, int, int, int, str, str]] = []
        for ts in both:
            rj, rlo, rhi = raw_map[ts]
            cj, clo, chi = corr_map[ts]
            lr, lc = len(rj), len(cj)
            d = lr - lc
            if abs(d) >= args.threshold:
                deltas.append((ts, rlo, clo, lr, lc, rj, cj))

        deltas.sort(key=lambda x: abs(x[3] - x[4]), reverse=True)

        print(f"\n=== {raw_path.name} ===")
        print(
            f"  timestamps: raw={len(raw_ts)} corrected={len(corr_ts)} "
            f"intersection={len(both)} only_raw={len(only_raw)} only_corr={len(only_corr)}"
        )
        if deltas:
            print(f"  large deltas (|raw-corr| >= {args.threshold}), top {args.top} by |delta|:")
            for ts, rlo, clo, lr, lc, rj, cj in deltas[: args.top]:
                diff = lr - lc
                _, rlo2, rhi = raw_map[ts]
                _, clo2, chi = corr_map[ts]
                print(
                    f"    [{fmt_ts(ts)}] L{rlo2}-{rhi} raw vs L{clo2}-{chi} corr | "
                    f"len {lr} vs {lc} (raw-corr={diff:+d})"
                )
                print(f"      R: {rj[:200]!r}{'…' if len(rj) > 200 else ''}")
                print(f"      C: {cj[:200]!r}{'…' if len(cj) > 200 else ''}")
        else:
            print(f"  (no shared timestamps with |len delta| >= {args.threshold})")

        if only_raw:
            print(f"  sample timestamps only in raw ({len(only_raw)} total):")
            for ts in only_raw[:6]:
                t, lo, hi = raw_map[ts][0], raw_map[ts][1], raw_map[ts][2]
                print(f"    [{fmt_ts(ts)}] L{lo}: {t[:100]!r}{'…' if len(t) > 100 else ''}")
        if only_corr:
            print(f"  sample timestamps only in corrected ({len(only_corr)} total):")
            for ts in only_corr[:6]:
                t, lo, hi = corr_map[ts][0], corr_map[ts][1], corr_map[ts][2]
                print(f"    [{fmt_ts(ts)}] L{lo}: {t[:100]!r}{'…' if len(t) > 100 else ''}")


if __name__ == "__main__":
    main()
