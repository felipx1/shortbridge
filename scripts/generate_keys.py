"""Run once (locally or on the VPS) to generate APP_SECRET_KEY and
APP_ENCRYPTION_KEY for .env. Never regenerate on a live install without
reading .env.example's warning about what each rotation invalidates."""
import secrets

from cryptography.fernet import Fernet

print(f"APP_SECRET_KEY={secrets.token_urlsafe(48)}")
print(f"APP_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
