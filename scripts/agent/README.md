# ShortBridge Home Download Agent

Runs on this computer (a residential IP), not the VPS — see
`../../UNOFFICIAL_DOWNLOAD.md` for why.

**Local-only mode**: downloads Shorts straight into `downloaded_shorts/`
at the repo root and keeps them there — it does **not** upload anything
to the server. Progress is tracked in `downloaded_shorts/.manifest.txt`
(one YouTube video ID per line, appended as each download finishes),
independent of anything on the server. The Library page on ShortBridge
won't show these as "Downloaded" — that's expected in this mode.

Run manually, whenever you want — no scheduled task. Each run handles up
to 5 pending videos (with a short pause between each) and exits; run it
again for more.

## One-time setup

1. **Generate a token** (treat it like a password — it authenticates to
   your ShortBridge instance):
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

Prints something like "N video(s) this run (X/Y already downloaded)",
downloads them into `downloaded_shorts/`, exits. Run it again for the
next batch.

If it prints an error about missing config, check step 3 above. If
downloads themselves fail, see the troubleshooting section in
`UNOFFICIAL_DOWNLOAD.md`.

## How to tell it's working

- `downloaded_shorts/` fills up with `.mp4` files, one per Short.
- The log line at the end of each run reports how many succeeded, how
  many MB, and how many are left overall.
