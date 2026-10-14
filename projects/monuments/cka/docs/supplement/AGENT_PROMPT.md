# CKA supplement pass — agent instructions (template)

You run the CKA supplement pass for ONE episode, given to you as SEQ (integer), and TRANSCRIPT (file name).

Read, in this folder (<PACK>/): SUPPLEMENT_SPEC.md (including its Relevance tag and Names sections), then SPEC.md, example_episode_102.md and EPISTEMIC_GRAPH.md. EXAMPLE_SUPPLEMENT_ep060.md is an approved supplement showing the expected quality and density.

Inputs:
- Transcript: <CKA>/transcripts_corrected/<TRANSCRIPT> (read all of it)
- Existing draft (immutable record): <CKA>/drafts/episode_<SEQ as 3 digits>.md

Write only additions to <PACK>/<STAGING>/episode_<SEQ 3 digits>.md. Do not modify any repo file.

Rules:
- Use grep on nodes.tsv / memes.tsv / claims_index.tsv. Reuse existing node and meme ids whenever the person/topic/meme exists: check aliases, names with or without "The", and grep the surname and close spellings.
- N-10899 is Paramount Tactical; N-11001 is Valhalla VFT. Andrew Kolvet is N-14; Justin Streiff is N-15; Robert Shillman (the donor "Bob Shulman") is N-98. "DOVE"/"DOAJ" are Kirk's "internet DOGE". "APAC" is AIPAC. Fort Wuka is always Fort Huachuca.
- Never put a transcription error in an Aliases line; list it under Doubts as `MISTRANSCRIPTION: "<as transcribed>" -> "<real name>" (<timestamp>)`, and say if the wrong rendering is a real name or common word elsewhere.
- Do not record home addresses, phone numbers, license plates or minors' details. Personal material about private individuals is relevance:tangential.
- Only link Contradicts/Revises when the propositions are really the same subject; Revises only for the host walking back her own earlier claim.
- No Claim Timestamp beyond the transcript's last [MM:SS] marker.

When done, run: SKELETON_PACK=<PACK> python3 -I <CKA>/scripts/check_supplement.py <SEQ> --dir <STAGING> and fix every problem until it prints OK.

Report (concise): new claims, artifacts, nodes, memes, the 5 most important missed beats (with timestamps), the MISTRANSCRIPTION list, and doubts.
