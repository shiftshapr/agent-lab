# Claim timestamp corrections, 2026-10-14

`check_claim_timestamps.py` (ROADMAP 0.5) compares each claim's Claim Timestamp with the transcript block that holds its Transcript Snippet. These 26 claims were set to the start of that block, in the draft and the inscription. They are extraction errors, corrected in place (POLICY §12), not host revisions.

- **Real drift (7):** the old timestamp was 1 to 5 minutes before the quoted words, so the `?t=` link missed them.
- **Tightened (19):** the old timestamp was 40 to 60 seconds before the block. That is within the check's tolerance, but the block start is where the words are, so the correction stands.

The checker's first version matched the first occurrence of a repeated phrase and let marker positions drift; both were fixed before these were re-validated. After the fixes, 11,462 claims are checked (124 snippets not found verbatim, which the preflight snippet gate covers) and 0 are off-block.

| Claim | Episode | Old | New | Kind |
|---|---|---|---|---|
| C-6506 | ep15 | 00:57:20 | 00:58:55 | real drift |
| C-9609 | ep27 | 00:29:15 | 00:30:15 | tightened |
| C-9615 | ep27 | 00:35:13 | 00:36:03 | tightened |
| C-9627 | ep27 | 00:47:00 | 00:48:02 | real drift |
| C-9723 | ep30 | 00:20:57 | 00:21:38 | tightened |
| C-8038 | ep35 | 00:37:12 | 00:37:53 | tightened |
| C-14027 | ep47 | 00:16:04 | 00:17:03 | tightened |
| C-6966 | ep53 | 00:42:56 | 00:43:37 | tightened |
| C-6978 | ep53 | 00:56:19 | 00:57:00 | tightened |
| C-8156 | ep54 | 00:14:53 | 00:17:45 | real drift |
| C-5456 | ep57 | 00:36:29 | 00:38:17 | real drift |
| C-7049 | ep63 | 00:49:45 | 00:50:40 | tightened |
| C-8418 | ep70 | 00:30:08 | 00:31:39 | real drift |
| C-7136 | ep75 | 00:59:43 | 01:00:36 | tightened |
| C-12809 | ep83 | 00:40:56 | 00:41:40 | tightened |
| C-8659 | ep89 | 00:26:31 | 00:27:13 | tightened |
| C-5697 | ep107 | 00:12:51 | 00:13:38 | tightened |
| C-4602 | ep116 | 00:14:50 | 00:15:38 | tightened |
| C-8859 | ep122 | 00:21:31 | 00:22:19 | tightened |
| C-7253 | ep124 | 00:59:57 | 01:00:47 | tightened |
| C-5976 | ep130 | 00:29:13 | 00:29:59 | tightened |
| C-7519 | ep137 | 00:34:45 | 00:35:32 | tightened |
| C-3743 | ep142 | 00:14:25 | 00:15:13 | tightened |
| C-9170 | ep142 | 00:14:25 | 00:15:13 | tightened |
| C-10569 | ep152 | 00:41:34 | 00:46:20 | real drift |
| C-7824 | ep156 | 00:44:10 | 00:45:44 | real drift |
