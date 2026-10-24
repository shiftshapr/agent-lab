# External monitors (ROADMAP 4.2) (2026-10-24)

**What runs.** `scripts/daily/monitors.py` runs in every daily pipeline run, after the episode and tweet intakes.
It polls the sources in `config/monitors.json`:
- **Court calendar:** the Utah courts public calendar search, for case 251403576 (State v. Tyler James Robinson,
  Fourth District). It shows hearings in the next 30 days. The full docket (XChange) is paid, so it is not polled.
- **News:** Google News RSS for 8 queries over the last 3 days: Tyler Robinson, the assassination investigation,
  Erika Kirk, TPUSA, Candace Owens, Brian Harpole, Lance Twiggs and UVU security. Items from the POLICY 11 Tier 2
  outlets are marked `tier2`.

- **Commentator channels** (added the same day): YouTube RSS feeds of 8 channels. Seven are filtered on case
  keywords: the Charlie Kirk Show, Real America's Voice, TPUSA, Cross Examined (Turek), Shawn Ryan, Paramount
  Tactical and Megyn Kelly. Baron Coleman's channel is unfiltered. Videos from the last 14 days are kept.
  Long-form discussions by commentary-series speakers become candidates for the 4.1b series, with Daveed's approval.

**Where alerts go.**
- Alerts already seen are skipped. The seen state is kept outside the repo, in `~/agent-lab-data/cka_monitor/`.
- New alerts go to `WORK/monitor_alerts.json` and are appended to `ledger/monitor_alerts.json`, which is rendered to
  `.md`. Any new alert starts the daily session even when there is no new episode.
- **RUNBOOK step M** triages them: each becomes `triaged` (with open-question ids where they clearly match) or
  `ignored`. Tier 2 items that report something new are flagged `candidate`. New court entries and candidates go into
  the summary as review items.
- Alerts are leads, never evidence. A candidate is fetched as a source only after Daveed approves it.

**First run (2026-10-24).**
- 163 alerts: 106 triaged and 57 ignored (mostly syndicated AP and Reuters copies). There were no hearings on the
  court calendar in the next 30 days.
- 19 Tier 2 candidates, almost all about the 2026-10-22/23 scheduling hearing:
  - the defense asked for a 2029 trial;
  - Erika Kirk moved for a 2027 trial;
  - no date was set, and the order may come in November;
  - President Trump criticised the judge.
- These are listed in `ledger/monitor_alerts.md` and await Daveed's approval.

**Not covered yet.**
- The paid docket.
- The County Attorney site, a Next.js app with no listing feed.

## Follow-up: the 19 candidates approved (same day)

**Sources.** Daveed approved the 19 Tier 2 candidates.
- **URL fix.** The monitor had stored Google News redirect links. It now resolves Tier 2 items to the publisher's own
  URL, using Google's article-URL lookup.
- **Fetched.** The articles were fetched as S-115..S-133. Three could not be downloaded because the publisher blocks
  automated requests (403): S-116 (Reuters) and S-123 and S-133 (ABC4). They stay in the manifest with that error.
- **Extracted.** 315 verbatim facts were extracted from the other 16 (`PROMPT_extract.md` as in Tier 2).

**Claims.** The facts matched 164 unverified claims. 2 judges proposed 2 corroborations, and on review I kept one:
- **C-4029, kept.** Fox News (S-119) states that 2025-12-11 was Robinson's first in-person court appearance. This
  answers the reason both Tier 2 rounds had rejected the claim.
- **C-12620, rejected.** The quote does not show the defense's dismissal argument.

**Open-questions register.**
- Two reporting conflicts were added.
- Q-1012 records the 2026-10-22/23 scheduling hearing.

**Totals.** 579 corroborated, 38 contradicted-by-record.

**Ledger.** `ledger/monitor_alerts.json` marks the 19 as `approved`, with their S-ids.
