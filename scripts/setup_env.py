"""Create local configuration without default credentials or overwriting an existing .env."""

import secrets
from pathlib import Path
from cryptography.fernet import Fernet

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit(".env ya existe; no se ha modificado.")
target.write_text(
    "POSTGRES_PASSWORD="
    + secrets.token_hex(24)
    + "\nMASTER_KEY="
    + Fernet.generate_key().decode()
    + "\nAPP_ORIGIN=http://localhost:8080\nCOOKIE_SECURE=false\nAPP_NAME=Germán Content Studio\nWEB_PORT=8080\nLINKEDIN_VERSION=202609\n",
    encoding="utf-8",
)
print(
    ".env creado con valores aleatorios. Conserva una copia segura para recuperación."
)
