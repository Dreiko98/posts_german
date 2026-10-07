import argparse
import getpass
from sqlalchemy import select
from cryptography.fernet import Fernet
from .db import SessionLocal
from .models import User
from .security import password_hasher
from .services import current_context


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["create-user", "reset-password", "generate-key", "worker-health"],
    )
    parser.add_argument("--username", default="german")
    args = parser.parse_args()
    if args.command == "generate-key":
        print(Fernet.generate_key().decode())
        return
    if args.command == "worker-health":
        from .models import Configuration
        from .db import now
        from datetime import datetime

        with SessionLocal() as db:
            row = db.get(Configuration, "worker_health")
            if (
                not row
                or (
                    now() - datetime.fromisoformat(row.value["heartbeat"])
                ).total_seconds()
                > 180
            ):
                raise SystemExit(1)
        return
    with SessionLocal() as db:
        db.execute(
            __import__("sqlalchemy").text("SELECT pg_advisory_xact_lock(117013)")
        )
        user = db.scalar(select(User).where(User.username == args.username))
        if args.command == "create-user" and db.scalar(select(User).limit(1)):
            raise SystemExit(
                "Ya existe un usuario; no hay registro público. Usa reset-password."
            )
        if args.command == "reset-password" and not user:
            raise SystemExit("Usuario inexistente.")
        password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
        if len(password) < 12 or password != getpass.getpass("Repite la contraseña: "):
            raise SystemExit("Contraseña demasiado corta o confirmación diferente.")
        if not user:
            user = User(
                username=args.username, password_hash=password_hasher.hash(password)
            )
            db.add(user)
        else:
            user.password_hash = password_hasher.hash(password)
            from .models import Session
            from sqlalchemy import delete

            db.execute(delete(Session).where(Session.user_id == user.id))
        db.commit()
        current_context(db)
        print(
            "Usuario listo. No se ha mostrado ni guardado la contraseña en texto plano."
        )


if __name__ == "__main__":
    main()
