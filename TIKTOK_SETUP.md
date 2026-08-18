# TikTok Setup — Phase 4

Verified against the current TikTok for Developers docs (August 2026).

## What ShortBridge asks for

- **Scopes requested**: `user.info.basic`, `video.list`, `video.upload`,
  `video.publish` — requested together at connect time, but what actually
  works is whatever comes back in the token response's `scope` field.
  `video.publish` in particular can stay restricted to private-only
  posting until the app passes TikTok's audit (Phase 9) — Connections
  reflects this per-scope, not an all-or-nothing state.
- **Redirect URI**:
  `https://shortbridge.srv1006990.hstgr.cloud/oauth/tiktok/callback`
- **No PKCE** — that's only required for desktop/mobile apps, not a web
  server flow like this one.

## Sandbox mode (TikTok's equivalent of Google's "Testing" status)

Your app starts in **Sandbox** mode: fully functional for OAuth and
uploads, but only for TikTok accounts you explicitly add as **target
users** (up to 10), and — separately — any content actually posted
through the Content Posting API is forced private until the app passes
review (this second restriction is about posting, not about OAuth or
draft/inbox uploads specifically; Phase 5 will confirm exactly which path
is affected once we're there).

Unlike Google, there's no token-expiry penalty for staying unaudited —
TikTok access tokens last 24h and refresh tokens last 365 days regardless
of Sandbox status.

## Steps

### 1. Create a developer account and an app

1. Go to https://developers.tiktok.com/ and log in (or create an account)
   with the TikTok account you'll manage this from.
2. Click your profile icon (top right) → **Manage apps**.
3. Click **Connect an app**, select/confirm the app owner (your account
   or an organization).
4. Fill in **App details**: app name (e.g. "ShortBridge"), an icon
   (1024x1024px, required even for personal use), category, and a
   description of what it does — TikTok reads this later during review,
   so a plain honest sentence is fine: *"Personal tool that lets me
   review and manually approve my own YouTube Shorts before sending them
   to my own TikTok account as drafts."*
5. Under **Platforms**, choose **Web** and enter your site URL:
   `https://shortbridge.srv1006990.hstgr.cloud`

### 2. Add products

1. In the app's **Products** section, click **Add products**.
2. Add **Login Kit** — this is what enables `user.info.basic` and the
   OAuth flow itself.
3. Add **Content Posting API** — this enables `video.upload` and
   `video.publish`.
4. For each product, add the redirect URI under its platform config:
   ```
   https://shortbridge.srv1006990.hstgr.cloud/oauth/tiktok/callback
   ```

### 3. Get your credentials

In **App details** → **Credentials**, copy the **Client key** and
**Client secret**.

### 4. Turn on Sandbox and add yourself as a target user

1. On the app page, toggle the switch near the app name to **Sandbox**.
2. Click **Create Sandbox**, give it a name, confirm.
3. Under **Sandbox settings** → **Target users**, click **Add account**,
   log in with the TikTok account you're connecting, accept the
   Developer Terms of Service.
4. **Wait up to an hour** — TikTok says the account can take that long to
   actually show up as an approved target user. Don't be alarmed if the
   first connection attempt fails immediately after adding yourself;
   try again later if so.

---

```text
ACTION REQUIRED — TIKTOK

1. Create a TikTok for Developers account and app (step 1)
2. Add Login Kit and Content Posting API products, with the redirect URI
   https://shortbridge.srv1006990.hstgr.cloud/oauth/tiktok/callback (step 2)
3. Copy the Client key and Client secret (step 3)
4. Turn on Sandbox mode and add your own TikTok account as a target user
   (step 4) -- then wait up to an hour before testing the connection

When finished, give me:
- Client key
- Client secret

Tell me: DONE (once you've also added yourself as a target user)
```

## Storing the credentials

Same as Google's: straight into the VPS `.env` (`TIKTOK_CLIENT_KEY`,
`TIKTOK_CLIENT_SECRET`), never into the Git repo, never logged, and I
won't display them back to you again after that.

## Testing the connection

1. Log into ShortBridge → Connections → **Connect** under TikTok
2. You'll go through TikTok's consent screen for the scopes above
3. You should land back on Connections with "Connected — <your TikTok
   display name>" and a per-scope AVAILABLE/NOT APPROVED breakdown
4. If it fails immediately after you just added yourself as a target
   user, that's the up-to-an-hour propagation delay mentioned above —
   wait and retry
