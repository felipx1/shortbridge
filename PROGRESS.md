# ShortBridge — Progress

- [x] **Phase 0** — VPS audit (read-only, via Hostinger's management API — no shell access). Findings: Ubuntu 24.04, Traefik already reverse-proxying by Docker label, no host port conflicts possible for a new service, `/docker/<project>/` is the deploy convention, chosen host `shortbridge.srv1006990.hstgr.cloud` (zero DNS work).
- [x] **Phase 1** — Project skeleton, Docker/Compose, SQLite (WAL) + Alembic, admin auth (Argon2id, signed sessions, CSRF, rate limiting), APScheduler skeleton, all 6 UI screens (stubbed, real DB-backed), `/health`. Verified locally: migration applies cleanly, full login→dashboard→settings→logout flow passes an end-to-end smoke test (`scripts/smoke_test.py`).
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

- Not yet deployed to the VPS — deployment is repo-based (see `INSTALL.md`);
  needs a Git remote before Phase 2 can ship there.
- Dockerfile/entrypoint verified by code review, not by an actual `docker build`
  (no local Docker on this dev machine) — first real build happens on deploy;
  re-run the smoke test inside the container before trusting it in production.
- `/privacy` and `/terms` pages (section 41) intentionally deferred to Phase 9,
  once TikTok's requirements for them are confirmed.
