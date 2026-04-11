#!/usr/bin/env python3
"""
Apply quality-review export when line numbers are stale: anchor-based patches.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
CORR = PROJECT / "transcripts_corrected"

CRUFT = re.compile(
    r"\nRECOMMENDED FIX \(EDITABLE\)\s*\n\s*Restore default\s*$", re.IGNORECASE | re.MULTILINE
)


def _read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find(lines: list[str], needle: str) -> int:
    for i, ln in enumerate(lines):
        if needle in ln:
            return i
    return -1


def _impl_text(it: dict) -> str:
    rel = it.get("implementFile")
    if rel:
        path = PROJECT / rel
        if path.is_file():
            return path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"implementFile not found: {path}")
    return (it.get("implementText") or "").replace("\r\n", "\n")


def main() -> None:
    default_json = PROJECT / "reports" / "quality_fix_16.json"
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_json
    data = (
        json.loads(json_path.read_text(encoding="utf-8"))
        if json_path.is_file()
        else {"items": []}
    )
    by_id = {it["findingId"]: it for it in data.get("items", [])}

    # --- ep001: remove IRS/tnusa ad block immediately before morfar segment ---
    p = CORR / "episode_001_ZAsV0fHGBiM.txt"
    lines = _read(p)
    if "ep001-closing-financing" in by_id:
        i0 = _find(lines, "[56:21] Also want to remind you guys about tax")
        i1 = _find(lines, "[57:38] The morfar–farfar scandal")
        if i0 >= 0 and i1 >= 0 and i0 < i1:
            del lines[i0:i1]
            print(f"episode_001: removed tax-network block lines {i0 + 1}-{i1} before morfar")
    if "ep001-sear-typo" in by_id:
        impl = _impl_text(by_id["ep001-sear-typo"]).strip().splitlines()
        i = _find(lines, "Loretta Abbis. I want to sear into your")
        if i >= 0 and len(impl) >= 3:
            lines[i : i + 3] = impl[:3]
            print("episode_001: sear-typo block")
    _write(p, lines)

    # --- ep002 ---
    p = CORR / "episode_002_1IY2oD-_xVA.txt"
    lines = _read(p)
    if "ep002-nimi-sponsor" in by_id:
        impl = _impl_text(by_id["ep002-nimi-sponsor"]).strip().splitlines()
        a = _find(lines, "[42:08] Use promo code candace at checkout")
        b = _find(lines, "[44:16] You know, easily the most important")
        if a >= 0 and b >= 0 and b >= a:
            lines[a : b + 1] = impl
            print(f"episode_002: nimi-sponsor replaced {b - a + 1} -> {len(impl)} lines")
    if "ep002-policy-frantzve" in by_id:
        impl = _impl_text(by_id["ep002-policy-frantzve"]).strip().splitlines()
        a = _find(lines, "[12:25] Look at Dr. Jerry Frantzve")
        if a >= 0:
            for j, ln in enumerate(impl):
                if a + j < len(lines):
                    lines[a + j] = ln
            print("episode_002: policy-frantzve")
    _write(p, lines)

    # --- ep003 ---
    p = CORR / "episode_003_cZxHqYsWRYg.txt"
    lines = _read(p)
    if "ep003-open-loretta" in by_id:
        impl = _impl_text(by_id["ep003-open-loretta"]).strip().splitlines()
        if impl and impl[-1].rstrip().endswith("was"):
            impl[-1] = impl[-1].rstrip() + " involved with horse racing. Is everybody"
        a = _find(lines, "[02:07] Man, oh man. Loretta Abbis")
        b = _find(lines, "[02:32] somehow maybe connected to gambling")
        if a >= 0 and b >= 0 and b > a:
            lines[a:b] = impl
            print(f"episode_003: open-loretta replaced {b - a} lines")
    if "ep003-preborn-mid" in by_id:
        impl = _impl_text(by_id["ep003-preborn-mid"]).strip().splitlines()
        a = _find(lines, "[23:53] right, you guys. Thanks to you. Last")
        b = _find(lines, "[26:53] So, who is Erika Kirk?")
        if a >= 0 and b >= 0 and b > a:
            sub = lines[a:b]
            rel = next((i for i, ln in enumerate(sub) if "[27:39] will show you" in ln), -1)
            tail = sub[rel:] if rel >= 0 else []
            merged = impl + tail
            lines[a:b] = merged
            print(f"episode_003: preborn-mid replaced {b - a} -> {len(merged)} lines")
    _write(p, lines)

    # --- ep004 ---
    p = CORR / "episode_004_jTj9Ip46r4w.txt"
    lines = _read(p)
    if "ep004-khazarian-long" in by_id or "ep004-preborn-snippet" in by_id:
        sn_txt = "[27:25] A little bit of history."
        if "ep004-preborn-snippet" in by_id:
            sn_txt = _impl_text(by_id["ep004-preborn-snippet"]).strip() or sn_txt
        sn = sn_txt.splitlines()
        a = _find(lines, "[24:08] Thanks to you. Last year, Preborn")
        b = _find(lines, "[34:33] Depression")
        chunk = lines[a : b + 1] if a >= 0 and b >= 0 else []
        bx_rel = next(
            (i for i, ln in enumerate(chunk) if "[27:25]" in ln and "history" in ln.lower()),
            -1,
        )
        if a >= 0 and b >= 0 and bx_rel >= 0:
            bx = a + bx_rel
            merged = [sn[0]] + lines[bx + 1 : b + 1]
            old_w = b - a + 1
            lines[a : b + 1] = merged
            print(f"episode_004: merged preborn+snippet+khar {old_w} -> {len(merged)} lines")
        elif a >= 0 and b >= 0:
            print("episode_004: merge SKIP (no [27:25] history line in range)")
    if "ep004-butterbee" in by_id:
        impl = _impl_text(by_id["ep004-butterbee"]).strip().splitlines()
        a = _find(lines, "[15:06] Butterbee")
        if a >= 0:
            for j, ln in enumerate(impl):
                if a + j < len(lines):
                    lines[a + j] = ln
            print("episode_004: butterbee")
    _write(p, lines)

    # --- ep005: strip orphaned Nimi read (timestamp jump 33→35) ---
    p = CORR / "episode_005_2tFYJf1klgY.txt"
    lines = _read(p)
    if "ep005-nimi-thrive-purge" in by_id:
        a = _find(lines, "gold.com. Also, you know, I'm going to")
        b = _find(lines, "[35:11] I just have to know what Tyler was doing")
        if a >= 0 and b >= 0 and b > a:
            del lines[a:b]
            print(f"episode_005: removed orphaned Nimi block ({b - a} lines)")
    _write(p, lines)

    # --- ep006 ---
    p = CORR / "episode_006_y8lak3CRwDw.txt"
    lines = _read(p)
    if "ep006-supercalifrag" in by_id:
        impl = _impl_text(by_id["ep006-supercalifrag"]).strip().splitlines()
        a = _find(lines, "[12:24] and working with the department of")
        if a >= 0:
            for j, ln in enumerate(impl):
                if a + j < len(lines):
                    lines[a + j] = ln
            print("episode_006: supercalifrag")
    if "ep006-preborn-financing" in by_id:
        impl = _impl_text(by_id["ep006-preborn-financing"]).strip().splitlines()
        a = _find(lines, "[35:32] Thanks to you. Last year, Preborn")
        b = _find(lines, "[38:33] So, I have been very clear with you guys")
        if a >= 0 and b >= 0 and b > a:
            lines[a:b] = impl
            print(f"episode_006: preborn-financing {b - a} -> {len(impl)} lines")
    _write(p, lines)

    # --- ep007 ---
    p = CORR / "episode_007_DdPjoy5W-wY.txt"
    lines = _read(p)
    if "ep007-nimi-dose" in by_id:
        a = _find(lines, "[22:34] right, you guys. Nimi Skincare")
        b = _find(lines, "[25:23] shares your values. Pure Talk, America's")
        if a >= 0 and b >= 0:
            end = b + 1
            if end < len(lines) and "wireless company" in lines[end]:
                end += 1
            del lines[a:end]
            print(f"episode_007: removed Nimi/Dose/PureTalk block ({end - a} lines)")
    if "ep007-sex-cells" in by_id:
        impl = _impl_text(by_id["ep007-sex-cells"]).strip().splitlines()
        a = _find(lines, "[45:41] Sex sells, babe.")
        if a >= 0:
            for j, ln in enumerate(impl):
                if a + j < len(lines):
                    lines[a + j] = ln
            print("episode_007: sex-cells")
    if "ep007-gika-popa" in by_id:
        impl = _impl_text(by_id["ep007-gika-popa"]).strip().splitlines()
        a = _find(lines, "[56:57] years. General")
        if a >= 0:
            for j, ln in enumerate(impl):
                if a + j < len(lines):
                    lines[a + j] = ln
            print("episode_007: gika-popa")
    if "ep007-forward-ellipsis" in by_id:
        impl = _impl_text(by_id["ep007-forward-ellipsis"]).strip().splitlines()
        a = _find(lines, "[31:52] forward to...")
        if a >= 0:
            for j, ln in enumerate(impl):
                if a + j < len(lines):
                    lines[a + j] = ln
            print("episode_007: forward-ellipsis")
    _write(p, lines)

    print("Done.")


if __name__ == "__main__":
    main()
