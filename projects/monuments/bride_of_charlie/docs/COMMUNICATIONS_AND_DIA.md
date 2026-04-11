# Communications guide: Bride of Charlie (Monument Zero) & DIA

Canonical copy for **public-facing messaging**, **OpenClaw-assisted outreach**, and **fan participation**.  
**Source of truth:** this file in agent-lab. OpenClaw workspace links here via `workspace/docs/COMMUNICATIONS_AND_DIA.md` (symlink).

---

## Plain language (don’t assume fans know our jargon)

| Term we use internally | Say this to fans instead |
|-------------------------|---------------------------|
| **Nodes** | **People, places, organizations, and story threads** the show keeps coming back to—each one a **named thread** in the archive so you can see how episodes link up. (If you must say “node” once, add: *“think people, places, and groups, not tech.”*) |
| **Inscription** | A **careful write-up** of one episode: what was shown, quoted, or cited, tied together so it can be checked. |
| **Artifacts** | **On-screen evidence**: documents, clips, screenshots, things the episode actually puts in front of you. |
| **Claims** | **Specific factual statements** the episode supports with that evidence—not opinions or rants. |

**Rule for YouTube, Telegram, etc.:** Prefer **people, places, names, dates, and documents** over schema words. Builders can still say “nodes” in READMEs and the hub.

---

## What this project is (one paragraph)

**Bride of Charlie** is the first **monument** in a larger effort: turning a long-form investigative series into a **structured, evidence-first archive**—each episode becomes a **careful record** that ties **what the show showed** (documents, clips, quotes) to **who and what** it’s about (**people, places, orgs, recurring threads**) so nothing important gets lost to noise or memory-holing. The goal is **clarity and verifiability**, not a parallel narrative.

---

## DIA — Decentralized Intelligence Agency

**DIA** is the umbrella name for how this work is organized **without a single gatekeeper**.

| Idea | What it means in practice |
|------|---------------------------|
| **Decentralized** | Many people can propose episodes, spot errors, and improve transcripts; no one closet owns the truth. |
| **Intelligence** | We treat the show as **source material** and build **structured intelligence** (who, what, when, what document). |
| **Agency** | Participants **act**: nominate, verify, correct, prioritize—not only consume. |

**Public-safe framing:** “open research collective,” “community verification,” “shared ledger of what the episodes establish.”  
**Avoid:** sounding covert, militaristic, or like “we’re investigating people” in a stalker sense. The show is already public; we’re **cataloging and checking** what it presents.

---

## Audiences

| Segment | What they care about | How to speak to them |
|---------|----------------------|----------------------|
| **Candace fans / viewers** | The story, fairness, “what did we actually see?” | Warm, specific to the show, no jargon dump. |
| **Standaces** (and similar communities) | Loyalty, in-jokes, respect for the host’s break | Acknowledge the pause; don’t spam every video. |
| **Researchers / builders** | Schema, workflow, Neo4j, scripts | Point to `README.md`, `IDEAL_WORKFLOW.md`, repo paths. |

---

## Messaging pillars

1. **Respect the source** — We follow what episodes present; we separate evidence from opinion.  
2. **Monument, not hot take** — This is an **archive** and **participation layer**, not a substitute for the show.  
3. **Help us get it right** — Fans know episodes cold; that skill is **exactly** what verification needs.  
4. **Utah / genealogy** — When relevant, nod to **family lines and how people/places connect**—the same kind of **“who links to whom”** work the monument does for the series, in everyday language (don’t say **nodes** unless you define it—see **Plain language**).

---

## Tone guardrails

- **Fan-to-fan**, not corporate or influencer hype.  
- **No unexplained “nodes”** in public copy—use **people, places, orgs, recurring threads** (see **Plain language**).  
- **One clear ask** per message (e.g. “help verify this episode” OR “nominate a must-include episode,” not five).  
- **No URLs required** in a YouTube comment if it triggers spam filters—invite people to reply or DM *you* / a single stable link you control.  
- **Ask first before the agent posts** anything public (see OpenClaw `AGENTS.md` — external posts need human approval).

---

## Calls to action (pick one per touch)

- **Nominate** episodes that should be inscribed next (and why—one sentence).  
- **Verify** a transcript snippet or name spelling against a primary source.  
- **Flag** a statement in a draft that might be overstated or missing **on-screen evidence** the episode actually showed.  
- **Join** a lightweight review round (e.g. “episode X is in draft—who wants to sanity-check?”).  
- **Human in the loop** — Help prioritize episodes, sanity-check drafts, or catch errors the pipeline might miss (plain language for fans).

---

## YouTube comment — copy variants

Use **one** comment on the **last pre-break episode** (high visibility while Candace is away). Edit bracketed bits.

**Formatting:** YouTube comments are **plain text**. Do not use Markdown (`**bold**`, headers, etc.)—it will show up as ugly punctuation. When the agent drafts for YouTube, output **only** what should appear on the platform (no styling syntax).

### Variant A — canonical (author’s cut, paste as-is)

```text
Fellow fans / Standaces – while Candace’s taking time after Easter to dig into Utah genealogy (family lines, who connects to whom), a few of us are building a monument-style archive of the series: each episode written up as a traceable record–who and what it’s about, tied to what was actually said–so nothing important gets lost to memory-holing or noise.

If that sounds like your kind of rabbit hole: we’d love help choosing which episodes to prioritize and being a human in the loop. Reply here or reach out if you want in – no spam, just serious fans who like getting the details right.
```

### Variant B — warmer, Utah nod (plain text)

Love this community. Candace heading to Utah to chase genealogy is such a perfect mirror for the kind of connection mapping some of us are doing around the show — a monument project that treats episodes like primary sources (documents, names, dates, what the episode actually puts in front of you) instead of vibes.

If you’re a Standace who actually remembers episode specifics: we could use your brain for episode picks and verification. Comment or DM [you] if you want to help shape it.

### Variant C — minimal (plain text)

Standaces — small group is building a verified episode-by-episode archive of the series (people, places, and what the show actually showed—stays traceable). While Candace’s on break in Utah: if you want to help pick episodes or sanity-check transcripts, reply here. Fans who sweat the details welcome.

---

## OpenClaw agent: promotion playbook

Use this when the human asks the agent to **support** (not replace) outreach.

### Principles

1. **Draft, don’t blast** — Produce copy variants; human posts or approves.  
2. **Cadence** — At most **one** proactive nudge per channel per few days unless the human says otherwise; never carpet-bomb comments.  
3. **Context file** — For any draft, the agent should **read this doc** first so DIA + monument language stays consistent.  
4. **Segment** — Telegram vs Discord vs email get different lengths; YouTube stays shortest and least link-heavy. **YouTube = plain text only** (no Markdown).

### Concrete workflows

| Trigger | Agent action |
|---------|----------------|
| Human: “draft a YouTube comment for the break” | Output 2–3 **plain-text** variants (no `**` or other Markdown); note character count. Prefer **Variant A** block or match its tone. |
| Human: “weekly Standace update” | Short paragraph + single CTA from **Calls to action**. |
| Heartbeat / cron (only if human enables) | **Do not** auto-post publicly. Optional: remind human “no comms sent this week” or summarize draft queue. |
| Someone volunteers | Acknowledge; point them to **verification** steps in `README.md` / hub (human defines the onboarding path). |

### What the agent should **not** do

- Imply official affiliation with the channel or host unless explicitly authorized.  
- Promise timelines, legal outcomes, or “proof” beyond what inscriptions claim.  
- Share private contributor data or DMs in group contexts.

---

## Technical pointers (for builders & agents)

- **Project root:** `agent-lab/projects/monuments/bride_of_charlie/`  
- **Protocol / briefing:** `brief/monument_zero_briefing.md`  
- **Workflow:** `README.md`, `IDEAL_WORKFLOW.md`, `docs/AUTOMATED_WORKFLOW.md`  
- **Deer Flow / hub UI:** `agent-lab/framework/deer-flow/frontend/src/app/bride-of-charlie/`

---

## Revision log

| Date | Change |
|------|--------|
| 2026-03-30 | Initial comms + DIA + OpenClaw playbook; YouTube variants. Later same day: plain-language glossary (nodes → people/places/orgs/threads); variants avoid unexplained “nodes.” |
| 2026-03-30 | YouTube: plain-text note; Variant A = author copy (“said,” human-in-the-loop); B/C unstylized for paste. |
