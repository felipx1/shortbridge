# Unofficial YouTube Download

**Off by default.** You explicitly asked for this after being told the
trade-offs — this file is the detailed version of that conversation, kept
around so future-you (or future-me) remembers why it exists, what was
tried, and what actually works.

## What this is

Automatic downloading of your synced Shorts' actual video files, using
[yt-dlp](https://github.com/yt-dlp/yt-dlp) instead of the official YouTube
Data API — because **the official API has no download capability for any
channel, including your own** (verified against current docs before
building this; there's no compliant automated alternative, only manual
ones: Google Takeout, or YouTube Studio's per-video Download button).

## Why it doesn't run on the VPS

It was built to run directly on the VPS first. That failed in production:
YouTube's bot detection ("Sign in to confirm you're not a bot") treats
datacenter IPs (this VPS included) far more aggressively than residential
ones. Investigated three fixes, in order, each hitting a real wall:

1. **`player_client=android` spoof** — works from a residential IP
   (confirmed), fails from the VPS's IP with the same bot-check error.
2. **Browser cookies** — yt-dlp's own FAQ says cookies only work reliably
   from *the same IP* the browser session was created on. Cookies
   exported from a home connection, used from the VPS, produced a
   different error ("The page needs to be reloaded" -- YouTube requiring
   a PO Token even with valid cookies).
3. **PO Token provider** (`bgutil-ytdlp-pot-provider`, a companion
   service) — its own README states plainly: *"Providing a PO token does
   not guarantee bypassing 403 errors or bot checks, but it may help."*
   Not worth standing up and maintaining a whole additional Docker service
   for a "may help, no guarantee."

The two remaining options were a paid residential proxy service (ongoing
cost, still no guarantee) or running the download step from a residential
IP that already works — which is what got built.

## What actually works: the home agent

`scripts/agent/shortbridge_agent.py` runs on a residential connection
(your own computer, not the VPS), where the `player_client=android` spoof
alone is enough — confirmed against a real video from your channel. Each
run:

1. Asks the server (`GET /api/agent/pending-downloads`, bearer-token
   authenticated, not your admin login) what's still missing.
2. Downloads each with yt-dlp — the exact same code the server itself
   would use (`app.providers.youtube_unofficial`), just from a different IP.
3. Uploads the finished file (`POST /api/agent/videos/{id}/upload`) --
   the server hashes it, runs ffprobe, and creates the `MediaAsset`,
   linked to the source `YouTubeVideo` (exact match, no fuzzy matching
   needed -- it was requested by video ID).
4. Exits. Run manually whenever you want (double-click
   `scripts/agent/run_agent.bat`, or run the script directly) -- not
   scheduled, not a standing background process. Each run handles up to 5
   videos; run it again for the next batch.

The server-side pieces (`ENABLE_YOUTUBE_UNOFFICIAL_DOWNLOAD`, the paced
background job, the manual "Download" button in the Library UI) are
**left in place** in case a proxy or some future fix changes the
VPS-side math — they just won't succeed against this VPS's IP today.
`AGENT_API_TOKEN` is independent of that flag; the agent works whether or
not VPS-side downloading is enabled.

## Setup

See `scripts/agent/README.md` for exact steps (generate the token, fill
in `agent_config.env`, register the scheduled task).

## If downloads start failing again

1. Check `pip show yt-dlp` against the latest release
   (https://github.com/yt-dlp/yt-dlp/releases) — this project usually
   ships a fix within days of YouTube breaking something. Bump the pin in
   `requirements.txt` **and** in whatever environment runs the agent,
   redeploy/reinstall both.
2. If the agent itself starts getting bot-checked (residential IPs can
   get flagged too, just less often): re-read the three failed VPS-side
   fixes above before re-trying any of them — the reasoning they failed
   for still applies.
3. If it becomes more maintenance than it's worth: turn
   `ENABLE_YOUTUBE_UNOFFICIAL_DOWNLOAD` off, stop running the agent, and
   fall back to Google Takeout (bulk, for the existing backlog) + YouTube
   Studio's Download button (per-video, for new uploads) — manually
   uploaded into ShortBridge. Nothing else in the app depends on this
   being enabled.

## Legal / ToS note

This is against YouTube's Terms of Service, which permit downloading only
via a button YouTube itself provides. It's your own content, downloaded
for your own use, at a small personal scale — a materially different risk
profile than, say, redistributing someone else's videos — but it is not
compliant, and that's a deliberate, informed trade-off you made, not
something to forget is happening.
