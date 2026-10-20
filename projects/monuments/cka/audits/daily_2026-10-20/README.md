# CKA daily 2026-10-20: Ep 404 (seq 167)

This is the first run of the daily pipeline (`docs/daily/RUNBOOK.md`). `intake.py` ran under launchd. The headless
session stopped on an expired `claude` CLI login, so the agent steps were run from an interactive session, following
the runbook as written.

| seq | Ep | date | YouTube | claims |
|---|---|---|---|---|
| 167 | 404 | 2026-10-19 | VUSs6CTp78Q | 77 (C-15494–C-15570) |

- **New nodes:** 2 persons (Jussie Smollett; Kenneth "Kenny" Wynn), 3 topics, 2 memes.
- **Name rules:** 21 rules, mostly scoped to seq 167. Examples: Tyler Bowyer, Jussie Smollett, Hegseth, Fort Hood,
  Jean-Michel Trogneux and Katie Zacharia.
  - The proposed rule "Larry Loomer" → Laura Loomer was dropped: the host calls Loomer "Larry" on purpose.
- **Opus check at intake:**
  - 77 claims checked; 1 material finding (wording overstated a hedge), confirmed and fixed. Rate 1.3%.
  - 7 minor fixes were applied. Two minor fixes that would have dropped content were held back.
- **Gate exception:** C-15568 → N-27, "a Ye song". The alias "Ye" is shorter than the grounding matcher accepts.

## Review items
1. **Kenneth "Kenny" Wynn (new person).** The host reads a viewer tip that he is Blake Wynn's father, then a 2004
   article saying he was the subject of a child-pornography investigation; it reports no charges. He is a private
   individual. All four claims are attributed to the tip or the article, and none states the allegation as fact.
   Should these stay, as the host's allegation and a cited article, or be tagged tangential?
   - C-15533, 00:17:44: "someone emailed us a tip that Blake's father, Blake's father, Kenneth Wynn, who goes also
     goes by Kenny was raided back in 2004." https://youtu.be/VUSs6CTp78Q?t=1064
   - C-15534, 00:18:01: "Kenny Wynn, the brother of hotel casino developer Steve Wynn, is the subject of the same
     international child pornography investigation…" https://youtu.be/VUSs6CTp78Q?t=1081
   - C-15535 (https://youtu.be/VUSs6CTp78Q?t=1095) and C-15536 (https://youtu.be/VUSs6CTp78Q?t=1107) carry the
     article's details.
2. **"Bobby Sauce at take naps"** (00:02:22, https://youtu.be/VUSs6CTp78Q?t=142). Possibly Bobby Sausalito (N-898),
   who covered the statue story before. It is unconfirmed and no person is cited.
