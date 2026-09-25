# CKA manifest gaps

Publish dates come from Invidious (`invidious.f5.si`). Re-run the builder after refreshing dates.

## Finish full channel listing + dates

```bash
cd ~/workspace/agent-lab
python3 -m yt_dlp --flat-playlist --print "%(id)s|%(title)s" \
  "https://www.youtube.com/@RealCandaceO/streams" \
  > /tmp/candace_streams.txt
python3 projects/monuments/cka/scripts/build_episode_manifest.py --streams-cache /tmp/candace_streams.txt
```

If YouTube blocks metadata, export cookies and retry:

```bash
python3 -m yt_dlp --cookies-from-browser chrome --flat-playlist \
  --print "%(upload_date)s|%(id)s|%(title)s" "https://www.youtube.com/@RealCandaceO/streams"
```

- **missing_upload_date**: 1 video (`ZkDO-MRLUco`, Candace Ep 381) — manifest uses **inferred** `2026-09-01` between Ep 380/382 until Invidious/yt-dlp backfill succeeds.
- **date_fetch_errors**: intermittent Invidious 403/rate limits; re-run builder with `--sleep 0.5` if needed.
