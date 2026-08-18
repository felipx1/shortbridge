# ShortBridge — Progress

- [x] **Phase 0** — VPS audit (read-only, via Hostinger's management API — no shell access). Findings: Ubuntu 24.04, Traefik already reverse-proxying by Docker label, no host port conflicts possible for a new service, `/docker/<project>/` is the deploy convention, chosen host `shortbridge.srv1006990.hstgr.cloud` (zero DNS work).
- [x] **Phase 1** — Project skeleton, Docker/Compose, SQLite (WAL) + Alembic, admin auth (Argon2id, signed sessions, CSRF, rate limiting), APScheduler skeleton, all 6 UI screens (stubbed, real DB-backed), `/health`. Verified locally (smoke test) **and deployed live**: https://shortbridge.srv1006990.hstgr.cloud — `/health` green, real login→dashboard flow confirmed against production over HTTPS. Repo: https://github.com/felipx1/shortbridge.
  - First deploy attempt failed twice; both fixed and redeployed successfully:
    1. Bind-mounted `./data`/`./media` got auto-created root-owned by Docker, unwritable by the non-root (uid 1000) container user → switched to named volumes (`shortbridge_data`, `shortbridge_media`), which inherit the image's ownership.
    2. `ADMIN_PASSWORD_HASH` (Argon2id, full of `$`) got silently corrupted by Compose's `.env` interpolation (`$argon2id` → blank) → must be `$$`-escaped; documented in `INSTALL.md`.
- [ ] **Phase 2** — Google OAuth + YouTube sync
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
