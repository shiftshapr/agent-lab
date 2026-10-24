# Phase 6 adversarial re-audit: claims (CKA ROADMAP 6.1, strata C and D)

Follow `QA_PROMPT.md` exactly (`<PACK>` is your stratum folder), with two changes:

1. **Be adversarial.** Earlier extraction and QA passes already checked these claims. Assume errors remain and look
   for them, especially: words of a guest, clip, caller or document given to the host; an allegation stated as fact
   rather than "The host alleges / says"; added certainty, motive, numbers or names; a mis-transcribed name turned
   into a person id; a timestamp off the snippet.
2. **Stratum C only (allegations about named people): two extra checks**, recorded in the same result object:
   - `framing`: `ok` if the claim presents the allegation as the host's allegation, keeping her hedges; `error` if it
     reads as an established fact or is stronger than she said. A `framing` error is **material**.
   - `privacy`: `ok`, or `flag` if the claim alleges a crime or sexual misconduct by a named private individual,
     names a minor, gives a private person's address, phone or plate, or concerns a private individual's personal
     life. Flags are not errors; they go to Daveed. Say which in the note.

Write `<stratum>/results_NN.json` as QA_PROMPT says (plus `framing` and `privacy` for stratum C).
