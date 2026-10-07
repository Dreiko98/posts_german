import hashlib
import json
import secrets
from datetime import timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, Request
from sqlalchemy import select
from .config import settings
from .db import get_db, now
from .errors import AppError
from .models import Session, User, Connection

password_hasher = PasswordHasher()


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def encrypt(data: dict):
    if not settings.master_key:
        raise AppError(
            "clave_maestra",
            "Falta la clave maestra externa.",
            503,
            "Configura MASTER_KEY y reinicia.",
        )
    return (
        Fernet(settings.master_key.encode()).encrypt(json.dumps(data).encode()).decode()
    )


def decrypt(value: str):
    if not value:
        return {}
    try:
        return json.loads(Fernet(settings.master_key.encode()).decrypt(value.encode()))
    except (ValueError, InvalidToken):
        raise AppError(
            "descifrado",
            "No se pueden descifrar las credenciales.",
            503,
            "Restaura la clave maestra correcta.",
        )


def connection_data(db, provider: str):
    c = db.scalar(select(Connection).where(Connection.provider == provider))
    if not c:
        raise AppError(
            "no_conectada",
            f"La conexión {provider} no está configurada.",
            409,
            "Completa la conexión en Ajustes.",
        )
    return {**c.config, **decrypt(c.encrypted)}


def require_session(request: Request, db=Depends(get_db)):
    token = request.cookies.get("studio_session", "")
    session = (
        db.scalar(
            select(Session).where(
                Session.token_hash == digest(token), Session.expires_at > now()
            )
        )
        if token
        else None
    )
    if not session:
        raise AppError("sesion_requerida", "Inicia sesión para continuar.", 401)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("origin") != settings.app_origin:
            raise AppError(
                "origen_no_valido", "El origen de la solicitud no está permitido.", 403
            )
        if not secrets.compare_digest(
            request.headers.get("x-csrf-token", ""), session.csrf
        ):
            raise AppError(
                "csrf",
                "La sesión necesita actualizarse antes de guardar.",
                403,
                "Recarga la página.",
            )
    return session


def verify_password(encoded, password):
    try:
        return password_hasher.verify(encoded, password)
    except VerificationError:
        return False


def new_session(db, user: User):
    token = secrets.token_urlsafe(32)
    session = Session(
        token_hash=digest(token),
        csrf=secrets.token_hex(32),
        user_id=user.id,
        expires_at=now() + timedelta(hours=settings.session_hours),
    )
    db.add(session)
    db.commit()
    return token, session
