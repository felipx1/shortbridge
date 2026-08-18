# ShortBridge Home Download Agent

Runs on this computer (a residential IP), not the VPS — see
`../../UNOFFICIAL_DOWNLOAD.md` for why. Downloads Shorts that ShortBridge
has synced but doesn't have a video file for yet, and uploads them back.

Run manually, whenever you want — no scheduled task. Each run handles up
to 5 pending videos and exits; run it again for more.

## One-time setup

1. **Generate a token** (treat it like a password — it can upload files
   to your ShortBridge instance):
   ```
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. **Add it to the server**: set `AGENT_API_TOKEN=<the token>` in the
   VPS's `.env`, redeploy.
3. **Add it locally**: copy `agent_config.env.example` to
   `agent_config.env` in this folder and fill in the same token plus your
   ShortBridge URL. `agent_config.env` is gitignored — never commit it.

## Running it

Double-click **`run_agent.bat`** in this folder, or from the repo root:
```
.venv\Scripts\python.exe scripts\agent\shortbridge_agent.py
```

Prints something like "N video(s) pending", downloads and uploads them,
exits. Run it again later for the next batch — there's no need to wait
for one run to "finish the backlog"; each run just picks up wherever the
last one left off.

If it prints an error about missing config, check step 3 above. If
downloads themselves fail, see the troubleshooting section in
`UNOFFICIAL_DOWNLOAD.md`.

## How to tell it's working

- ShortBridge's Library page: videos that had "Download" pending should
  show "Downloaded ✓" after a run.
- ShortBridge's Logs page: `youtube_download_completed` events.
