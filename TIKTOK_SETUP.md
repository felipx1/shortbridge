# TikTok Setup — Phase 4

Not written yet. Phase 4 will:

1. Check the current TikTok for Developers docs (app creation, Login Kit,
   Content Posting API, sandbox vs. production, current scope names) as
   they exist when Phase 4 starts, since these have changed before and
   this doc needs to match reality, not an assumption.
2. Land here with exact steps to create the app, request `user.info.basic`,
   `video.upload`, `video.list`, and (separately, expect longer approval
   time) `video.publish`, and register the redirect URI
   `https://shortbridge.srv1006990.hstgr.cloud/oauth/tiktok/callback`
   (path may change if current docs recommend otherwise).
3. Explain the sandbox/unaudited-app limitations you'll hit before
   `video.publish` is approved (see `TIKTOK_APP_REVIEW.md`, added in
   Phase 9) — Draft Upload (`video.upload`) works before that; direct
   public posting doesn't.
4. Tell you exactly what to paste into `.env` (`TIKTOK_CLIENT_KEY`,
   `TIKTOK_CLIENT_SECRET`).
