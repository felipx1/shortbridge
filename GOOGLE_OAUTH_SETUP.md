# Google OAuth Setup — Phase 2

Not written yet. Phase 2 will:

1. Check the current (Google Cloud Console, as it exists when Phase 2
   starts) menu names for creating a project, enabling the YouTube Data API
   v3, and configuring the OAuth consent screen and a Web application
   OAuth client — these change over time and this doc will describe
   whatever the console actually shows, not a remembered version of it.
2. Land here with exact click-by-click steps and the precise redirect URI
   ShortBridge needs registered (based at
   `https://shortbridge.srv1006990.hstgr.cloud`).
3. Tell you exactly what to paste into `.env` (`GOOGLE_CLIENT_ID`,
   `GOOGLE_CLIENT_SECRET`) and how — never asking for more than that.

Scopes planned: `youtube.readonly` only, to start (see section 6 of the
original spec) — read access to sync your channel's uploads. A write scope
would only be added later, separately, if ShortBridge ever needs to publish
*to* YouTube too.
