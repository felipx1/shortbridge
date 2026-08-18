"""Run to generate ADMIN_PASSWORD_HASH for .env. Prompts interactively so
the plaintext password never ends up in shell history."""
import getpass

from argon2 import PasswordHasher

password = getpass.getpass("New admin password: ")
confirm = getpass.getpass("Confirm: ")
if password != confirm:
    raise SystemExit("Passwords did not match.")
if len(password) < 12:
    raise SystemExit("Use at least 12 characters.")

print("\nADMIN_PASSWORD_HASH=" + PasswordHasher().hash(password))
