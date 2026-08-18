# ShortBridge — Progress

- [x] **Phase 0** — VPS audit (read-only, via Hostinger's management API — no shell access). Findings: Ubuntu 24.04, Traefik already reverse-proxying by Docker label, no host port conflicts possible for a new service, `/docker/<project>/` is the deploy convention, chosen host `shortbridge.srv1006990.hstgr.cloud` (zero DNS work).
- [x] **Phase 1** — Project skeleton, Docker/Compose, SQLite (WAL) + Alembic, admin auth (Argon2id, signed sessions, CSRF, rate limiting), APScheduler skeleton, all 6 UI screens (stubbed, real DB-backed), `/health`. Verified locally (smoke test) **and deployed live**: https://shortbridge.srv1006990.hstgr.cloud — `/health` green, real login→dashboard flow confirmed against production over HTTPS. Repo: https://github.com/felipx1/shortbridge.
  - First deploy attempt failed twice; both fixed and redeployed successfully:
    1. Bind-mounted `./data`/`./media` got auto-created root-owned by Docker, unwritable by the non-root (uid 1000) container user → switched to named volumes (`shortbridge_data`, `shortbridge_media`), which inherit the image's ownership.
    2. `ADMIN_PASSWORD_HASH` (Argon2id, full of `$`) got silently corrupted by Compose's `.env` interpolation (`$argon2id` → blank) → must be `$$`-escaped; documented in `INSTALL.md`.
- [x] **Phase 2** — Google OAuth + YouTube sync. **Connected and verified live** against the real channel "Hazaña prime xd" (253 videos synced, 247 correctly detected as Shorts, 6 correctly excluded as regular-length videos, 1 landscape short-duration clip correctly excluded). Two real bugs found and fixed via production logs, not guessed at:
  1. `TypeError: can't compare offset-naive and offset-aware datetimes` on the first real sync — SQLite drops tzinfo on every stored datetime, so `app.models._util.utcnow()` had to switch to returning naive UTC (project-wide convention now: every datetime is naive and implicitly UTC). Regression test: `scripts/smoke_test_datetime_fix.py` (reproduces via a real SQLite round-trip).
  2. Short detection initially used `snippet.thumbnails.*.width/height` for aspect ratio, exactly as YouTube's docs (and a web search) suggested it should work — but empirically, against a real channel, it reports **1280x720 for every single video** regardless of true orientation, misclassifying 100% of that channel's real Shorts as "not a Short". Switched to `fileDetails.videoStreams[].widthPixels/heightPixels` (owner-only data, real pixel dimensions, with rotation handling for phone-recorded vertical video stored as a landscape file). fileDetails isn't always present (likely time-limited retention for older uploads, observed directly: recent videos had it, most didn't) — falls back to trusting duration alone in that case, which is the accurate call for a Shorts-focused channel.
  - `youtube.readonly` is a sensitive scope → refresh tokens expire after 7 days while the app is in unverified "Testing" status. Handled explicitly (`InvalidGrantError` → `needs_reconnect` flag → "Reconnect" banner on Dashboard/Connections), not left to fail silently.
  - Manual override (Mark as Short / Not a Short) live on the Library page for any edge case the heuristic still gets wrong.
- [ ] **Phase 3** — Media library, import matching, FFprobe/FFmpeg
- [ ] **Phase 4** — TikTok OAuth
- [ ] **Phase 5** — TikTok Draft Upload
- [ ] **Phase 6** — Scheduler + duplicate protection + retries
- [ ] **Phase 7** — UI final pass (bulk select, HTMX where it earns its keep)
- [ ] **Phase 8** — TikTok Direct Post
- [ ] **Phase 9** — TikTok App Review prep
- [ ] **Phase 10** — Backup automation (cron), full docs pass, final tests

## Known gaps carried forward from Phase 1

- `DRY_RUN=true` and no Google/TikTok credentials set yet — the live deploy
  is a real, reachable, but otherwise inert instance (login only) until
  Phase 2.
- `media` is a named volume, not a bind mount, so the SFTP-drop workflow for
  `media/inbox`/`media/import` (section 9) isn't available yet — decide in
  Phase 3 whether to switch it to a bind mount (needs a one-time host
  `chown`, which needs VPS shell access this session didn't have) or build
  an in-app upload UI instead.
- `/privacy` and `/terms` pages (section 41) intentionally deferred to Phase 9,
  once TikTok's requirements for them are confirmed.
- No cron yet for `scripts/backup.sh` — manual until Phase 10.
