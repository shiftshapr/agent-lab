# External monitors (ROADMAP 4.2) (2026-10-24)

**What runs.** `scripts/daily/monitors.py` runs in every daily pipeline run, after the episode and tweet intakes.
It polls the sources in `config/monitors.json`:
- **Court calendar:** the Utah courts public calendar search, for case 251403576 (State v. Tyler James Robinson,
  Fourth District). It shows hearings in the next 30 days. The full docket (XChange) is paid, so it is not polled.
- **News:** Google News RSS for 8 queries over the last 3 days: Tyler Robinson, the assassination investigation,
  Erika Kirk, TPUSA, Candace Owens, Brian Harpole, Lance Twiggs and UVU security. Items from the POLICY 11 Tier 2
  outlets are marked `tier2`.

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
- New videos from the commentator channels (4.1b), which could be added as a third monitor.
