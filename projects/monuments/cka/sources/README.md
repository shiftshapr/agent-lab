# Source streams (ROADMAP 4.1)

`streams.json` lists the streams and their tier: Tier 1 is primary records, Tier 2 is reputable reporting (POLICY 11).
`scripts/sources/fetch.py` downloads each item into `~/agent-lab-data/cka_sources/<stream>/`, which is private, and
extracts its text. It assigns a stable S-id and records the URL, date, publisher, sha256, size and retrieval time in
`manifest.json`. Only the manifest is in this public repo; claims cite sources by S-id (`Verification Evidence: S-…`).

Status, 2026-10-21:
- **Fetched:**
  - Seven hearing transcripts of State v. Robinson (S-2 to S-8; the preliminary hearing days 1–5, the bindover and a
    contempt hearing; Rev.com transcription of public testimony).
  - The 2025-09-12 press conference (S-11).
  - The UVU After-Action Report (S-12, 158 pages).
  - The adsb.lol ADS-B archive for 2025-09-10 (S-13, 3.5 GB).
- **Blocked:** the charging Information (S-1) and the County Attorney press releases (S-9, S-10). The County Attorney's
  site returns HTTP 503 and DocumentCloud blocks automated download. These need retrying, or a copy saved by hand.
