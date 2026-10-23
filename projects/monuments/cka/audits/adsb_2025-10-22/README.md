# ADS-B flight data, 2025-09-10 (S-13) (2026-10-22)

**Source.** adsb.lol globe history for 2025-09-10 (S-13: 3.5 GB, two tar parts, private in
`~/agent-lab-data/cka_sources`). The data is ODbL; a derived summary is in `sources/adsb/2025-09-10_summary.json`,
with individual owners omitted. The file covers one UTC day, 18:00 MDT on 9 September to 18:00 MDT on 10 September,
so evening flights on 10 September (Mountain time) need the 2025-09-11 file.

**Method.** `scripts/sources/adsb/scan.py` streamed all 74,405 aircraft traces. It kept every aircraft the archive's
claims name (SU-BTT, SU-BND, SU-BTU, N582MM, N1098L, N888KG, N102DZ, N8724A, N560TW, N40JD), any SU- registration,
and every aircraft within 8 km of Provo Airport or UVU: 416 traces. `legs.py` and `detail.py` derived takeoffs,
landings (ground speed over 80 kt), coverage gaps, the position at the moment of the shot (18:23:28Z) and the
closest approach to UVU. SU-BTU and N8724A are not in the day's data.

**Verdicts (`verdicts.json`, applied with `apply_record.py`).** 9 corroborated, 1 contradicted-by-record:
- **C-2015:** SU-BTT took off from Provo at 07:14 MDT for Wilmington. Corroborated.
- **C-3620:** SU-BND transmitted only from the ground at Provo (10:05–11:34 and 13:40–14:29 MDT) and never flew.
  Corroborated.
- **C-2144, C-2145:** N102DZ flew Scottsdale 07:12 MST to Salt Lake City 09:23 MDT, then Salt Lake City 13:00 MDT
  back to Scottsdale, with 20 minutes on the ground. Corroborated.
- **C-5414:** contradicted. N102DZ landed at Provo at 15:30 MDT and left at 16:10 MDT for Camarillo; it did not
  arrive at 4:36 p.m.
- **C-2937:** N560TW flew Scottsdale to Provo (landed 10:07 MDT, left 10:27 MDT), on to Santa Barbara, and back to
  Scottsdale (12:43 MST). Corroborated.
- **C-7389:** N40JD took off from Scottsdale 64 minutes after the shot and landed at Provo at 14:29 MDT.
  Corroborated.
- **C-9171:** N582MM took off near Denver at 11:58 MDT and reached Pierre at about 12:55 MDT. Corroborated.
- **C-2060:** N1098L was over southeast Idaho at the shot and over Provo about 22–27 minutes later. Corroborated.
- **C-2059:** N1098L flew up to Montana and turned around. Corroborated.

**Left unverified.**
- **C-2005, C-2007 (N888KG "departed 1:20 p.m.").** Wheels-up was 13:11:53 MDT, 8 minutes earlier. The gap
  toward Page fits the account but does not prove it.
- **C-1671, C-1673 (N1098L "from Texas", "around the time").** Not settled.
- **C-9172 (N582MM's Provo landing at 6:57 p.m.).** Needs the 9/11 file.

**Notable for the register.**
- **N1098L, a Global 6000:** made two low passes over Provo Airport, at 09:16 and about 12:48 MDT, descending to
  roughly 250 ft above the field without landing.
- **Aircraft near UVU at the shot:** within 10 km of UVU in the 20 minutes either side of the shot were Provo training
  and general-aviation traffic (including UVU's own DA40 and PA-44 trainers, the nearest 0.8 km away at 12:18 MDT and
  about 900 ft above the campus), business jets on approach to Provo, and airliners passing at about 18,000 ft.
- **Register updates:** six questions were updated with S-13 findings: Q-206 is answered, and Q-234, Q-235, Q-240,
  Q-329 and Q-473 are partly answered.

**Next.**
- **The 2025-09-11 file:** needed for evening Mountain-time flights, including N582MM to Provo.
- **C-37A 99-044 (Sept 7–8):** needs the 9/7–9/9 files.

## 2025-09-11 file (S-14, same day)
The local disk filled during the download, so the incomplete parts were deleted and `scan.py url …` streamed the
release (3,684,116,480 bytes; per-part sha256 in the manifest) straight from GitHub without saving it. It scanned
78,194 traces and kept 410 (`sources/adsb/2025-09-11_summary.json`).

**Corroborated (2):**
- **C-9172:** N582MM landed at Provo at 18:57 MDT on 10 September and stayed overnight.
- **C-9173:** it flew back to Pierre at 08:08 MDT on 11 September.

**Other findings (register):**
- **N102DZ:** returned to Provo at 19:31 MDT on 10 September and left for the Phoenix area at 09:54 MDT on
  11 September.
- **SU-BTT:** left Wilmington for Cairo at 05:55 MDT on 11 September.
- **SU-BND:** made no flight.
- **Register updates:** Q-235, Q-240 and Q-332 updated.

Totals now: 362 corroborated, 38 contradicted-by-record.
