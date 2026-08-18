# Google OAuth Setup — Phase 2

Verified against the current Google Cloud Console and OAuth 2.0 / YouTube
Data API v3 docs (August 2026). The console has been restructured since
older tutorials were written — OAuth consent configuration now lives under
a section called **"Google Auth Platform"**, split into Branding / Audience
/ Clients / Data Access tabs, not a single "OAuth consent screen" page.

## What ShortBridge asks for

- **Scope**: `https://www.googleapis.com/auth/youtube.readonly` only —
  "View your YouTube account". Read-only, least privilege (section 6). No
  write/upload scope is requested; ShortBridge never modifies your YouTube
  channel.
- **Offline access**: yes (`access_type=offline`), so sync can run on its
  own schedule without you sitting at the browser.
- **Redirect URI**: `https://shortbridge.srv1006990.hstgr.cloud/oauth/google/callback`

## Important: the 7-day refresh token limit

`youtube.readonly` is a "sensitive" scope. While your app's publishing
status is **Testing** (the default, and what you'll use here — it's
unverified, meaning Google hasn't reviewed it, which is normal for a
personal single-user app), **Google expires refresh tokens after 7 days**.
ShortBridge detects this (an `invalid_grant` error on refresh) and marks
the connection "Reconnection needed" on the Connections page instead of
failing silently — but it does mean clicking "Reconnect" roughly weekly
unless you complete Google's app verification process later (optional,
more paperwork than it's worth for personal use right now — revisit if
this gets annoying).

## Steps

### 1. Create a Google Cloud project

1. Go to https://console.cloud.google.com/
2. Top bar → project dropdown → **New Project**. Name it something like
   `shortbridge` (this name is only visible to you).

### 2. Enable the YouTube Data API v3

1. Left sidebar → **APIs & Services** → **Library**
2. Search "YouTube Data API v3" → open it → **Enable**

### 3. Configure Google Auth Platform

1. Left sidebar → **APIs & Services** → **Google Auth Platform** (or
   search "Google Auth Platform" in the top search bar)
2. **Branding** tab: fill in an app name (e.g. "ShortBridge") and your
   email as support contact. You do not need a logo or a public homepage
   for Testing status.
3. **Audience** tab:
   - User type: **External** (unless this is a Google Workspace account —
     then Internal is simpler and skips the 7-day limit entirely)
   - Publishing status: leave as **Testing**
   - Under "Test users", click **Add users** and add the Gmail address of
     the YouTube channel you're connecting. Only accounts listed here can
     complete the OAuth flow while in Testing status.
4. **Data Access** tab: click **Add or remove scopes**, find and check
   `.../auth/youtube.readonly` (filter by "YouTube Data API v3"), save.

### 4. Create the OAuth Client ID

1. Still under **Google Auth Platform** → **Clients** tab → **Create Client**
2. Application type: **Web application**
3. Name: `shortbridge-web` (or anything)
4. Under **Authorized redirect URIs**, click **Add URI** and enter exactly:
   ```
   https://shortbridge.srv1006990.hstgr.cloud/oauth/google/callback
   ```
5. Click **Create**. Google shows a **Client ID** and **Client Secret** —
   copy both now (the secret is only shown once, though you can always
   regenerate it later if you lose it).

---

```text
ACTION REQUIRED — GOOGLE

1. Create the Google Cloud project and enable YouTube Data API v3 (step 1-2 above)
2. Configure Google Auth Platform: Branding, Audience (External, Testing,
   add yourself as a test user), Data Access (add youtube.readonly) (step 3)
3. Create a Web application OAuth Client with redirect URI
   https://shortbridge.srv1006990.hstgr.cloud/oauth/google/callback (step 4)
4. Copy the Client ID and Client Secret

When finished, give me:
- Client ID
- Client Secret
```

## Storing the credentials

Once you give me the Client ID and Secret, I put them straight into the
`.env` on the VPS (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) and redeploy
— they're never written into the Git repo, never logged, and I won't
display them back to you again after that. If you ever need to rotate
them, generate a new secret in the same **Clients** tab and just tell me
the new value; the old one keeps working until you delete it there.

## Testing the connection

After the client ID/secret are deployed:
1. Log into ShortBridge → Connections → **Connect** under YouTube
2. You'll see Google's consent screen (it will say "Google hasn't verified
   this app" — that's expected for Testing status; click Advanced → Go to
   shortbridge (unsafe) → Continue, since you're the developer and the
   only test user)
3. You should land back on Connections with "Connected — <your channel
   name>"
4. Click **Sync now** and check the Library page — your Shorts should
   appear within a few seconds for a normal-sized channel
