# Install (VPS)

Target: `srv1006990.hstgr.cloud` (92.113.34.187), Ubuntu 24.04, Traefik
already running for other projects. Deployed as the Docker Compose project
`shortbridge` at `/docker/shortbridge/`.

## 1. Generate secrets locally first

```
python scripts/generate_keys.py     # -> APP_SECRET_KEY, APP_ENCRYPTION_KEY
python scripts/hash_password.py     # -> ADMIN_PASSWORD_HASH
```

Copy `.env.example` to `.env`, fill in the generated values plus
`ADMIN_USERNAME`. Leave `GOOGLE_*` and `TIKTOK_*` blank for now (Phase 2/4).
`BASE_URL=https://shortbridge.srv1006990.hstgr.cloud`, `COOKIE_SECURE=true`.

**`.env` is never committed.** On the VPS it should end up `chmod 600`.

## 2. Push to a Git repository

The VPS deployment tooling in use here (Hostinger VPS Projects) deploys
either from a `docker-compose.yml`'s raw contents or from a Git repository
URL. Since ShortBridge is custom code (not a published image), push this
project to a repository you control (private is fine — it contains no
secrets, those all live in `.env` which stays off Git).

## 3. Create host directories with the right ownership

`data/` and `media/` are bind-mounted (not named volumes) so you can SFTP
files straight into `media/inbox/` and `media/import/` — but that means
they must be owned by the container's non-root user (uid 1000) *before*
the first `docker compose up`, or ShortBridge won't be able to write to
them:

```
mkdir -p /docker/shortbridge/data /docker/shortbridge/media/{inbox,import,processed}
chown -R 1000:1000 /docker/shortbridge/data /docker/shortbridge/media
```

## 4. Deploy

The project is created/updated as a Docker Compose project named
`shortbridge` on virtual machine `1006990`, pointed at the repository from
step 2. `.env` is uploaded separately (not via Git) directly onto the VPS
at `/docker/shortbridge/.env`.

First boot will:
1. Run Alembic migrations automatically (see `docker-compose.yml` / entrypoint).
2. Create the admin user row from `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH`.
3. Start the scheduler (heartbeat only until Phase 2).

## 5. Verify

```
curl -f https://shortbridge.srv1006990.hstgr.cloud/health
```

Expect `{"status":"ok","database":"ok","scheduler":"ok"}`. Then log in at
`https://shortbridge.srv1006990.hstgr.cloud/login` with the admin
credentials from `.env`.

## 6. DNS / HTTPS

None needed. `shortbridge.srv1006990.hstgr.cloud` resolves automatically
(it's the VPS's own hostname), and Traefik issues the Let's Encrypt
certificate automatically via its existing HTTP-01 challenge setup the
first time it sees a request for that host.
