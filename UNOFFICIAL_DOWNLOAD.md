# Unofficial YouTube Download

**Off by default.** You explicitly asked for this after being told the
trade-offs — this file is the detailed version of that conversation, kept
around so future-you (or future-me) remembers why it exists and what to
expect from it.

## What this is

`ENABLE_YOUTUBE_UNOFFICIAL_DOWNLOAD=true` turns on automatic downloading of
your synced Shorts' actual video files, using [yt-dlp](https://github.com/yt-dlp/yt-dlp)
instead of the official YouTube Data API — because **the official API has
no download capability for any channel, including your own** (verified
against current docs before building this; there's no compliant automated
alternative, only manual ones: Google Takeout, or YouTube Studio's
per-video Download button).

## What it actually does

- yt-dlp extracts the real video stream from YouTube's internal player
  responses — the same mechanism every YouTube-downloader tool uses,
  Repurpose.io included, in all likelihood.
- Runs as a paced background job (`YOUTUBE_DOWNLOAD_INTERVAL_SECONDS`,
  default 15s): one video at a time, not a burst, so a large backlog
  trickles in instead of hammering YouTube.
- Also available on-demand: a "Download" button per video on the Library
  page.
- On success: computes sha256, runs ffprobe, creates a `MediaAsset` row
  already linked to the source `YouTubeVideo` (no fuzzy matching needed —
  we downloaded it *by* video ID, so the link is exact).
- On failure (private/deleted/age-restricted/region-locked/yt-dlp itself
  broken against a YouTube change): logs the error on the video row and
  backs off for `YOUTUBE_DOWNLOAD_RETRY_AFTER_HOURS` (default 6h) before
  trying that specific video again — shown as "Failed" with the reason on
  hover in the Library page, with a manual Retry button.

## Why this needed a workaround to work at all

During development, plain requests hit YouTube's bot-detection wall
immediately: `"Sign in to confirm you're not a bot"` — on a plain public
video, no less. The fix in `app/providers/youtube_unofficial.py` is
`extractor_args: {"youtube": {"player_client": ["android"]}}`, which makes
yt-dlp present itself as the YouTube Android app instead of a browser —
a known, commonly-used yt-dlp workaround, not something invented here.

**This is exactly the fragility that was flagged before building this.**
It works today (verified against a real video from the connected channel,
not just a synthetic test). It can stop working whenever YouTube tightens
bot-detection on the Android client path too, with no warning.

## If downloads start failing

1. Check `pip show yt-dlp` against the latest release
   (https://github.com/yt-dlp/yt-dlp/releases) — this project usually
   ships a fix within days of YouTube breaking something, since it has a
   large active community. Bump the pin in `requirements.txt`, redeploy.
2. If that alone doesn't fix it, the next thing yt-dlp usually needs is
   real browser cookies from a logged-in YouTube session
   (`--cookies-from-browser` / `--cookies cookies.txt` in yt-dlp's own
   docs). Not implemented here yet — would mean exporting cookies from
   your browser periodically (they expire) and mounting the file into the
   container. More moving parts, more fragility. Ask before adding this.
3. If it becomes more maintenance than it's worth: turn the flag off and
   fall back to Google Takeout (bulk, for the existing backlog) + YouTube
   Studio's Download button (per-video, for new uploads) into
   `media/inbox/` — this was the original, fully-compliant plan, and nothing
   about the rest of the app depends on the unofficial path being enabled.

## Legal / ToS note

This is against YouTube's Terms of Service, which permit downloading only
via a button YouTube itself provides. It's your own content, downloaded
for your own use, at a small personal scale — a materially different risk
profile than, say, redistributing someone else's videos — but it is not
compliant, and that's a deliberate, informed trade-off you made, not
something to forget is happening.
