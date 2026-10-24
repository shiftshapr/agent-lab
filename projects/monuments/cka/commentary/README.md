# Commentary series (ROADMAP 4.1b)

Commentators on the case are recorded as **speakers**, the same way the host is, in a series of their own. POLICY 11
applies: a commentator's claim can support, contradict or qualify the host's claim, but it is **never evidence** for a
verification status. `scripts/commentary/check.py` (a finalize gate) enforces the schema and fails if any
verification record cites a `CC-` claim.

**Files.**
- **`episodes.json`:** one entry per video (`K-NNN`), with the speaker group, YouTube id, channel, date, duration,
  caption track and the caption file's sha256. Captions and transcripts are kept privately; they are not in the repo.
- **`claims.json`:** claims `CC-n`. Each has the speaker, a timestamped YouTube link, the claim written as
  "<Speaker> says …", a verbatim snippet (8–40 words), mentions (node ids, plus `mentions_new` for people not yet in
  the register), a relevance tag, and `responds_to_host` when the speaker is answering Candace Owens.
- **`links.json`:** confirmed links `{cc, c, relation, note}` from a `CC` claim to a host `C` claim, where the
  relation is `supports`, `contradicts` or `qualifies`.
- **`claims.md`:** a readable rendering, by video, with each claim's links underneath.

**Pilot (2026-10-23).** It covers 37 videos (about 49 hours): 11 from the Charlie Kirk Show (Andrew Kolvet,
Blake Neff), 12 with Erika Kirk, 9 with Brian Harpole and Frank Turek, and 5 from Baron Coleman.

**Additions.**
- 2026-10-24: Baron Coleman Ep 187–189 (K-038..K-040), approved from the commentator-channel monitor
  (`audits/commentators_2026-10-24/`). That brings the series to 40 videos, 2,249 claims and 571 links.
- `scripts/commentary/render.py` re-renders `claims.md`.

**Method.** The method and prompts are in `audits/commentators_2026-10-23/`.

**Scope limits.** Baron Coleman episodes are covered in full for the first half only. From the superchat half, only
his own new case claims are recorded, never the superchat text. Two re-uploaded segments were de-duplicated.
