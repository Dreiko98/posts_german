import io
import json
import secrets
from datetime import timedelta, date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode
from typing import Literal
from fastapi import (
    FastAPI,
    Depends,
    Request,
    Response,
    UploadFile,
    File as Upload,
    Body,
)
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, text as sql_text
from sqlalchemy.exc import IntegrityError
from PIL import Image, UnidentifiedImageError
from .config import settings
from .db import get_db, now
from .models import (
    User,
    Session,
    LoginAttempt,
    Context,
    Idea,
    Publication,
    Version,
    Connection,
    Configuration,
    File,
    Job,
    AICall,
    Notification,
    OAuthState,
    Source,
    uid,
)
from .schemas import (
    LoginInput,
    PasswordInput,
    ContextInput,
    IdeaGenerate,
    IdeaEdit,
    IdeaState,
    ChannelEdit,
    Prepare,
    Instruction,
    ConnectionInput,
    Preferences,
    ModelOption,
    MetricsInput,
    Article,
    LinkedInText,
)
from .security import (
    require_session,
    digest,
    password_hasher,
    verify_password,
    new_session,
    encrypt,
    decrypt,
    connection_data,
)
from .errors import AppError
from .services import (
    current_context,
    serialize,
    publication_detail,
    save_version,
    evaluate_version,
    statistical_signals,
)
from .catalog import preferences, catalog, model_option, money, estimate
from .jobs import enqueue
from .network import request_json
from .integrations import WordPress, ga4_report, search_console_report

app = FastAPI(
    title="Germán Content Studio",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.exception_handler(AppError)
async def app_error(request, exc):
    return JSONResponse({"error": exc.public()}, status_code=exc.status)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic's default error body echoes supplied credentials.
    return JSONResponse(
        {
            "error": {
                "code": "entrada_invalida",
                "message": "Revisa los campos y límites de entrada.",
                "action": "",
            },
            "fields": [list(e["loc"]) for e in exc.errors()],
        },
        status_code=422,
    )


@app.exception_handler(Exception)
async def internal_error(request, exc):
    return JSONResponse(
        {
            "error": {
                "code": "error_interno",
                "message": "No se pudo completar la operación.",
                "action": "Revisa configuración y estado de servicios.",
            }
        },
        status_code=500,
    )


@app.middleware("http")
async def security_headers(request, call_next):
    length = request.headers.get("content-length", "0")
    if length.isdigit() and int(length) > 12_000_000:
        return JSONResponse(
            {
                "error": {
                    "code": "entrada_grande",
                    "message": "La solicitud es demasiado grande.",
                }
            },
            status_code=413,
        )
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.get("/api/health")
def health(db=Depends(get_db)) -> dict:
    db.execute(sql_text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/openapi.json", dependencies=[Depends(require_session)])
def openapi() -> dict:
    return app.openapi()


@app.post("/api/auth/login")
def login(
    data: LoginInput, request: Request, response: Response, db=Depends(get_db)
) -> dict:
    if request.headers.get("origin") != settings.app_origin:
        raise AppError(
            "origen_no_valido", "Origen de inicio de sesión no permitido.", 403
        )
    ip = request.client.host if request.client else "unknown"
    key = digest(ip)
    # Persistent and serialized per origin IP, independent of arbitrary usernames.
    db.execute(
        sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(key[:15], 16)}
    )
    attempt = db.get(LoginAttempt, key)
    if not attempt:
        attempt = LoginAttempt(key=key, failures=0, window_start=now())
        db.add(attempt)
    if now() - attempt.window_start > timedelta(minutes=15):
        attempt.failures, attempt.window_start = 0, now()
    if attempt.failures >= 5:
        db.commit()
        raise AppError("login_limitado", "Demasiados intentos. Espera 15 minutos.", 429)
    user = db.scalar(select(User).where(User.username == data.username))
    valid = (
        verify_password(user.password_hash, data.password)
        if user
        else verify_password(DUMMY_HASH, data.password)
    )
    if not user or not valid:
        attempt.failures += 1
        db.commit()
        raise AppError("login_invalido", "Usuario o contraseña incorrectos.", 401)
    attempt.failures = 0
    token, session = new_session(db, user)
    response.set_cookie(
        "studio_session",
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    return {"username": user.username, "csrf": session.csrf}


DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))


@app.get("/api/auth/session")
def session_info(session=Depends(require_session), db=Depends(get_db)) -> dict:
    return {
        "username": db.get(User, session.user_id).username,
        "csrf": session.csrf,
        "expires_at": session.expires_at,
    }


@app.post("/api/auth/logout")
def logout(
    response: Response, session=Depends(require_session), db=Depends(get_db)
) -> dict:
    db.delete(db.get(Session, session.id))
    db.commit()
    response.delete_cookie("studio_session", path="/")
    return {"ok": True}


@app.put("/api/auth/password")
def change_password(
    data: PasswordInput, session=Depends(require_session), db=Depends(get_db)
) -> dict:
    user = db.get(User, session.user_id)
    if not verify_password(user.password_hash, data.current):
        raise AppError("password_incorrecta", "La contraseña actual no coincide.", 403)
    user.password_hash = password_hasher.hash(data.new)
    db.execute(
        delete(Session).where(Session.user_id == user.id, Session.id != session.id)
    )
    db.commit()
    return {"ok": True}


def get_record(db, cls, record_id):
    record = db.get(cls, record_id)
    if not record:
        raise AppError("no_encontrado", "El registro no existe.", 404)
    return record


def revision(record, expected):
    if record.revision != expected:
        raise AppError(
            "conflicto_edicion",
            "Este registro cambió desde que lo abriste.",
            409,
            "Recarga antes de guardar para conservar los cambios.",
        )


def editable(db, pub):
    active = db.scalar(select(Job).where(Job.active_key == "publication:" + pub.id))
    if active:
        raise AppError(
            "trabajo_activo",
            "Hay una operación en curso sobre esta publicación.",
            409,
            "Espera a que termine o cancélala.",
        )


@app.get("/api/context", dependencies=[Depends(require_session)])
def context_get(db=Depends(get_db)) -> dict:
    return serialize(current_context(db))


@app.put("/api/context", dependencies=[Depends(require_session)])
def context_put(data: ContextInput, db=Depends(get_db)) -> dict:
    ctx = current_context(db)
    ctx = db.scalar(select(Context).where(Context.id == ctx.id).with_for_update())
    revision(ctx, data.revision)
    ctx.body, ctx.revision = data.body.model_dump(), ctx.revision + 1
    db.commit()
    return serialize(ctx)


@app.post("/api/context/import", dependencies=[Depends(require_session)])
async def context_import(file: UploadFile = Upload(), db=Depends(get_db)) -> dict:
    raw = await file.read(2_000_001)
    if len(raw) > 2_000_000:
        raise AppError("documento_grande", "El documento supera 2 MB.")
    name = (file.filename or "").lower()
    if not name.endswith((".txt", ".md")):
        raise AppError(
            "documento_tipo",
            "Importa texto UTF-8 (.txt o .md). Copia otros documentos a texto para revisarlos.",
        )
    try:
        value = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AppError("documento_encoding", "Guarda el documento como UTF-8.")
    return {
        "text": value[:20000],
        "source": {
            "name": Path(name).name,
            "consulted_at": now().isoformat(),
            "role": "texto_manual_no_confirmado",
        },
        "truncated": len(value) > 20000,
    }


@app.get("/api/preferences", dependencies=[Depends(require_session)])
def preferences_get(db=Depends(get_db)) -> dict:
    return preferences(db)


@app.put("/api/preferences", dependencies=[Depends(require_session)])
def preferences_put(data: Preferences, db=Depends(get_db)) -> dict:
    money(data.max_cost)
    if money(data.max_cost) > 100:
        raise AppError(
            "limite_maximo", "El límite por operación no puede superar 100 USD."
        )
    model_option(db, data.provider, data.model)
    if data.fallback:
        model_option(db, data.fallback_provider, data.fallback_model)
    row = db.get(Configuration, "preferences") or Configuration(key="preferences")
    row.value = data.model_dump()
    db.add(row)
    db.commit()
    return row.value


@app.get("/api/catalog", dependencies=[Depends(require_session)])
def catalog_get(db=Depends(get_db)) -> dict:
    connections = {c.provider: c for c in db.scalars(select(Connection)).all()}
    prefs = preferences(db)
    return {
        **catalog(db),
        "models": [
            {
                **m,
                "estimate": estimate(m, prefs["max_searches"]),
                "availability": connections[m["provider"]].status
                if m["provider"] in connections
                else "no_conectada",
            }
            for m in catalog(db)["models"]
        ],
    }


@app.put("/api/catalog", dependencies=[Depends(require_session)])
def catalog_put(data: list[ModelOption], db=Depends(get_db)) -> dict:
    if not 1 <= len(data) <= 20:
        raise AppError(
            "catalogo_limite", "El catálogo debe tener entre 1 y 20 modelos."
        )
    ids = set()
    for model in data:
        if (model.provider, model.id) in ids:
            raise AppError("catalogo_duplicado", "Hay un modelo duplicado.")
        ids.add((model.provider, model.id))
        for value in (
            model.input,
            model.output,
            model.cached,
            model.cache_write,
            model.search,
        ):
            if value is not None:
                money(value)
    row = db.get(Configuration, "catalog") or Configuration(key="catalog")
    row.value = {"version": now().isoformat(), "models": [x.model_dump() for x in data]}
    db.add(row)
    db.commit()
    return row.value


@app.get("/api/estimate", dependencies=[Depends(require_session)])
def estimate_get(db=Depends(get_db)) -> dict:
    prefs = preferences(db)
    return estimate(
        model_option(db, prefs["provider"], prefs["model"]), prefs["max_searches"]
    )


CONNECTION_FIELDS = {
    "openai": (set(), {"api_key"}),
    "anthropic": (set(), {"api_key"}),
    "wordpress": ({"url", "username"}, {"application_password"}),
    "linkedin": (
        {"client_id", "redirect_uri"},
        {"client_secret", "access_token", "person_id", "expires_at"},
    ),
    "ga4": ({"property_id"}, {"service_account"}),
    "search_console": ({"site_url"}, {"service_account"}),
}


@app.get("/api/connections", dependencies=[Depends(require_session)])
def connections_get(db=Depends(get_db)) -> list[dict]:
    rows = {c.provider: c for c in db.scalars(select(Connection)).all()}
    return [
        {
            "provider": provider,
            "config": rows[provider].config if provider in rows else {},
            "status": rows[provider].status if provider in rows else "no_conectada",
            "detail": rows[provider].detail
            if provider in rows
            else "Configura esta conexión.",
            "checked_at": rows[provider].checked_at if provider in rows else None,
            "has_secrets": bool(rows[provider].encrypted)
            if provider in rows
            else False,
            "balance": "desconocido" if provider in ("openai", "anthropic") else None,
        }
        for provider in CONNECTION_FIELDS
    ]


@app.put("/api/connections/{provider}", dependencies=[Depends(require_session)])
def connection_put(provider: str, data: ConnectionInput, db=Depends(get_db)) -> dict:
    if provider not in CONNECTION_FIELDS:
        raise AppError("conexion_tipo", "Proveedor no permitido.")
    config_fields, secret_fields = CONNECTION_FIELDS[provider]
    if (
        set(data.config) - config_fields
        or set(data.secrets) - secret_fields
        or len(json.dumps(data.model_dump())) > 40000
    ):
        raise AppError(
            "conexion_campos",
            "La conexión contiene campos no permitidos o es demasiado grande.",
        )
    if provider == "wordpress":
        WordPress(data.config)
    if (
        provider == "linkedin"
        and data.config.get("redirect_uri")
        != settings.app_origin + "/api/oauth/linkedin/callback"
    ):
        raise AppError(
            "oauth_callback",
            "El callback debe coincidir con APP_ORIGIN/api/oauth/linkedin/callback.",
        )
    row = db.scalar(
        select(Connection).where(Connection.provider == provider)
    ) or Connection(provider=provider)
    row.config = data.config
    current = decrypt(row.encrypted or "")
    updates = {k: v for k, v in data.secrets.items() if v not in ("", None)}
    row.encrypted = encrypt({**current, **updates})
    row.status, row.detail = (
        "no_comprobada",
        "Credenciales guardadas; conexión aún no comprobada.",
    )
    db.add(row)
    db.commit()
    return {
        "provider": provider,
        "status": row.status,
        "has_secrets": bool(row.encrypted),
    }


@app.delete("/api/connections/{provider}", dependencies=[Depends(require_session)])
def connection_delete(provider: str, db=Depends(get_db)) -> dict:
    row = db.scalar(select(Connection).where(Connection.provider == provider))
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}


@app.post("/api/connections/{provider}/test", dependencies=[Depends(require_session)])
def connection_test(provider: str, db=Depends(get_db)) -> dict:
    row = db.scalar(select(Connection).where(Connection.provider == provider))
    if not row:
        raise AppError("no_conectada", "Configura primero la conexión.", 409)
    config = connection_data(db, provider)
    try:
        if provider in ("openai", "anthropic"):
            headers = (
                {"Authorization": "Bearer " + config.get("api_key", "")}
                if provider == "openai"
                else {
                    "x-api-key": config.get("api_key", ""),
                    "anthropic-version": "2023-06-01",
                }
            )
            data, _ = request_json(
                "GET",
                "https://api.openai.com/v1/models"
                if provider == "openai"
                else "https://api.anthropic.com/v1/models",
                headers=headers,
            )
            row.detail = "Autenticación comprobada. Modelos y herramientas dependen de permisos; saldo desconocido."
        elif provider == "wordpress":
            wp = WordPress(config)
            wp.request("GET", "wp/v2/users/me", params={"context": "edit"})
            try:
                info = wp.request("GET", "german-studio/v1/health")
                row.detail = "WordPress y conector disponibles. Yoast: " + str(
                    info.get("yoast_version") or "no instalado"
                )
            except AppError:
                row.status, row.detail = (
                    "parcial",
                    "WordPress accesible; instala o revisa el plugin German Studio Connector.",
                )
                row.checked_at = now()
                db.commit()
                return {"status": row.status, "detail": row.detail}
        elif provider == "linkedin":
            request_json(
                "GET",
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": "Bearer " + config.get("access_token", "")},
            )
            row.detail = "Perfil OAuth accesible; publicar requiere w_member_social y aprobación del producto."
        elif provider == "ga4":
            ga4_report(
                config,
                (date.today() - timedelta(days=7)).isoformat(),
                date.today().isoformat(),
            )
            row.detail = "Lectura GA4 comprobada. La disponibilidad de datos depende del periodo y umbrales."
        elif provider == "search_console":
            search_console_report(
                config,
                (date.today() - timedelta(days=7)).isoformat(),
                date.today().isoformat(),
            )
            row.detail = (
                "Lectura Search Console comprobada; la API devuelve filas principales."
            )
        row.status = "conectada"
    except AppError as exc:
        row.status, row.detail = "error", exc.message
    except Exception:
        row.status, row.detail = (
            "error",
            "No se pudo comprobar la conexión. Revisa credenciales, red y permisos.",
        )
    row.checked_at = now()
    db.commit()
    return {"status": row.status, "detail": row.detail}


@app.post("/api/oauth/linkedin/start")
def oauth_start(session=Depends(require_session), db=Depends(get_db)) -> dict:
    config = connection_data(db, "linkedin")
    state = secrets.token_urlsafe(32)
    db.add(
        OAuthState(
            provider="linkedin",
            state_hash=digest(state),
            session_id=session.id,
            expires_at=now() + timedelta(minutes=10),
        )
    )
    db.commit()
    return {
        "url": "https://www.linkedin.com/oauth/v2/authorization?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": config.get("client_id", ""),
                "redirect_uri": config.get("redirect_uri", ""),
                "state": state,
                "scope": "openid profile w_member_social",
            }
        )
    }


@app.get("/api/oauth/linkedin/callback")
def oauth_callback(
    state: str = "",
    code: str = "",
    error: str = "",
    session=Depends(require_session),
    db=Depends(get_db),
):
    row = db.scalar(
        select(OAuthState)
        .where(
            OAuthState.state_hash == digest(state),
            OAuthState.session_id == session.id,
            OAuthState.expires_at > now(),
        )
        .with_for_update()
    )
    if not row:
        raise AppError(
            "oauth_estado",
            "La autorización ha caducado o no pertenece a esta sesión.",
            403,
        )
    db.delete(row)
    db.commit()
    if error or not code:
        raise AppError(
            "oauth_denegado",
            "LinkedIn no concedió autorización.",
            409,
            "Comprueba los productos y permisos de la aplicación.",
        )
    config = connection_data(db, "linkedin")
    tokens, _ = request_json(
        "POST",
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
        },
    )
    identity, _ = request_json(
        "GET",
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": "Bearer " + tokens["access_token"]},
    )
    row = db.scalar(select(Connection).where(Connection.provider == "linkedin"))
    secret = decrypt(row.encrypted)
    row.encrypted = encrypt(
        {
            **secret,
            "access_token": tokens["access_token"],
            "person_id": identity["sub"],
            "expires_at": (now() + timedelta(seconds=tokens["expires_in"])).isoformat(),
        }
    )
    row.status, row.detail = "conectada", "OAuth autorizado para el perfil personal."
    db.commit()
    return RedirectResponse(
        settings.app_origin + "/?view=ajustes&oauth=ok", status_code=303
    )


@app.get("/api/ideas", dependencies=[Depends(require_session)])
def ideas_get(q: str = "", status: str = "", db=Depends(get_db)) -> list[dict]:
    query = select(Idea).order_by(Idea.updated_at.desc())
    if q:
        query = query.where(
            (Idea.title.ilike("%" + q[:200] + "%"))
            | (Idea.summary.ilike("%" + q[:200] + "%"))
        )
    if status:
        query = query.where(Idea.status == status)
    publications = {
        p.idea_id: p.id
        for p in db.scalars(
            select(Publication).where(Publication.idea_id.is_not(None))
        ).all()
    }
    return [
        {
            **serialize(i),
            "publication_id": publications.get(i.id),
            "sources": [
                serialize(s)
                for s in db.scalars(select(Source).where(Source.idea_id == i.id)).all()
            ],
        }
        for i in db.scalars(query.limit(500)).all()
    ]


@app.post(
    "/api/ideas/generate", status_code=202, dependencies=[Depends(require_session)]
)
def ideas_generate(data: IdeaGenerate, db=Depends(get_db)) -> dict:
    if data.manual and not data.instructions.strip():
        raise AppError("intencion_vacia", "Escribe la intención de tu idea.")
    prefs = preferences(db)
    if data.quantity > prefs["max_ideas"]:
        raise AppError("cantidad_limite", "La cantidad supera el límite configurado.")
    current_context(db)
    return serialize(
        enqueue(
            db,
            "ideas",
            {**data.model_dump(), "quantity": 1 if data.manual else data.quantity},
        )
    )


@app.put("/api/ideas/{idea_id}", dependencies=[Depends(require_session)])
def idea_put(idea_id: str, data: IdeaEdit, db=Depends(get_db)) -> dict:
    idea = db.scalar(select(Idea).where(Idea.id == idea_id).with_for_update())
    if not idea:
        raise AppError("no_encontrado", "La idea no existe.", 404)
    revision(idea, data.revision)
    for key, value in data.model_dump(exclude={"revision"}).items():
        setattr(idea, key, value)
    idea.revision += 1
    db.commit()
    return serialize(idea)


@app.put("/api/ideas/{idea_id}/state", dependencies=[Depends(require_session)])
def idea_state(idea_id: str, data: IdeaState, db=Depends(get_db)) -> dict:
    idea = db.scalar(select(Idea).where(Idea.id == idea_id).with_for_update())
    if not idea:
        raise AppError("no_encontrado", "La idea no existe.", 404)
    revision(idea, data.revision)
    if idea.status == "utilizada":
        raise AppError("idea_utilizada", "La idea ya tiene un artículo publicado.", 409)
    idea.status, idea.discard_reason = (
        data.status,
        data.discard_reason if data.status == "descartada" else idea.discard_reason,
    )
    idea.revision += 1
    db.commit()
    return serialize(idea)


@app.post(
    "/api/ideas/{idea_id}/publication",
    status_code=202,
    dependencies=[Depends(require_session)],
)
def create_publication(idea_id: str, data: Prepare, db=Depends(get_db)) -> dict:
    idea = db.scalar(select(Idea).where(Idea.id == idea_id).with_for_update())
    if not idea:
        raise AppError("no_encontrado", "La idea no existe.", 404)
    pub = db.scalar(select(Publication).where(Publication.idea_id == idea_id))
    if pub:
        return {"publication_id": pub.id, "existing": True}
    pub = Publication(title=idea.title, idea_id=idea.id)
    db.add(pub)
    db.flush()
    job = enqueue(
        db,
        "generate_publication",
        {"publication_id": pub.id, **data.model_dump()},
        "publication:" + pub.id,
    )
    return {"publication_id": pub.id, "job_id": job.id, "existing": False}


@app.get("/api/publications", dependencies=[Depends(require_session)])
def publications_get(q: str = "", db=Depends(get_db)) -> list[dict]:
    query = select(Publication).order_by(Publication.updated_at.desc())
    if q:
        query = query.where(Publication.title.ilike("%" + q[:200] + "%"))
    return [publication_detail(db, p) for p in db.scalars(query.limit(500)).all()]


@app.get("/api/publications/{pub_id}", dependencies=[Depends(require_session)])
def publication_get(pub_id: str, db=Depends(get_db)) -> dict:
    return publication_detail(db, get_record(db, Publication, pub_id))


@app.put(
    "/api/publications/{pub_id}/{channel}", dependencies=[Depends(require_session)]
)
def channel_put(
    pub_id: str,
    channel: Literal["wordpress", "linkedin"],
    data: ChannelEdit,
    db=Depends(get_db),
) -> dict:
    pub = db.scalar(
        select(Publication).where(Publication.id == pub_id).with_for_update()
    )
    if not pub:
        raise AppError("no_encontrado", "La publicación no existe.", 404)
    revision(pub, data.revision)
    editable(db, pub)
    expected = Article if channel == "wordpress" else LinkedInText
    if not isinstance(data.data, expected):
        raise AppError("canal_datos", "Los campos no corresponden al canal.")
    save_version(
        db,
        pub,
        channel,
        data.data.model_dump(),
        "edicion_manual",
        based_on=pub.current_wp if channel == "linkedin" else None,
    )
    db.commit()
    return publication_detail(db, pub)


@app.get("/api/publications/{pub_id}/versions", dependencies=[Depends(require_session)])
def versions_get(pub_id: str, db=Depends(get_db)) -> list[dict]:
    get_record(db, Publication, pub_id)
    return [
        serialize(v)
        for v in db.scalars(
            select(Version)
            .where(Version.publication_id == pub_id)
            .order_by(Version.created_at.desc())
        ).all()
    ]


@app.post(
    "/api/publications/{pub_id}/restore/{version_id}",
    dependencies=[Depends(require_session)],
)
def restore_version(
    pub_id: str,
    version_id: str,
    expected_revision: int = Body(embed=True),
    db=Depends(get_db),
) -> dict:
    pub = db.scalar(
        select(Publication).where(Publication.id == pub_id).with_for_update()
    )
    if not pub:
        raise AppError("no_encontrado", "La publicación no existe.", 404)
    revision(pub, expected_revision)
    editable(db, pub)
    version = get_record(db, Version, version_id)
    if version.publication_id != pub.id:
        raise AppError(
            "version_no_pertenece", "La versión no pertenece a esta publicación.", 403
        )
    save_version(
        db,
        pub,
        version.channel,
        version.data,
        "restauracion",
        version.context_snapshot,
        version.based_on,
    )
    if version.channel == "linkedin":
        pub.li_stale = version.based_on != pub.current_wp
    db.commit()
    return publication_detail(db, pub)


@app.post(
    "/api/publications/{pub_id}/evaluate", dependencies=[Depends(require_session)]
)
def evaluate_post(pub_id: str, db=Depends(get_db)) -> dict:
    pub = get_record(db, Publication, pub_id)
    editable(db, pub)
    version = db.get(Version, pub.current_wp) if pub.current_wp else None
    if not version:
        raise AppError("sin_borrador", "No hay contenido para evaluar.", 409)
    evaluation = evaluate_version(db, pub, version)
    db.commit()
    return serialize(evaluation)


ACTION_KINDS = {
    "correct": "correct",
    "adapt-linkedin": "adapt_linkedin",
    "send-wordpress": "wp_send",
    "check-wordpress": "wp_check",
    "publish-linkedin": "li_publish",
    "import-remote": "wp_import_version",
}


@app.post(
    "/api/publications/{pub_id}/actions/{action}",
    status_code=202,
    dependencies=[Depends(require_session)],
)
def action_post(
    pub_id: str, action: str, data: Instruction, db=Depends(get_db)
) -> dict:
    pub = db.scalar(
        select(Publication).where(Publication.id == pub_id).with_for_update()
    )
    if not pub or action not in ACTION_KINDS:
        raise AppError(
            "accion_no_encontrada", "La acción o publicación no existe.", 404
        )
    if action == "publish-linkedin":
        if (
            not pub.wp_id
            or not pub.public_verified
            or pub.wp_status != "publish"
            or pub.li_stale
            or pub.li_status in ("publicado", "incierto", "enviando")
        ):
            raise AppError(
                "linkedin_bloqueado",
                "LinkedIn requiere artículo público comprobado y adaptación vigente.",
                409,
                "Comprueba WordPress y revisa la adaptación. El worker verificará otra vez antes de enviar.",
            )
    job = enqueue(
        db,
        ACTION_KINDS[action],
        {"publication_id": pub.id, **data.model_dump()},
        "publication:" + pub.id,
    )
    return serialize(job)


@app.post("/api/publications/{pub_id}/image", dependencies=[Depends(require_session)])
async def image_upload(
    pub_id: str, file: UploadFile = Upload(), db=Depends(get_db)
) -> dict:
    pub = get_record(db, Publication, pub_id)
    editable(db, pub)
    raw = await file.read(10_000_001)
    if len(raw) > 10_000_000:
        raise AppError("imagen_grande", "La imagen supera 10 MB.")
    try:
        with Image.open(io.BytesIO(raw)) as img:
            fmt = img.format
            if (
                fmt not in ("JPEG", "PNG", "WEBP")
                or img.width * img.height > 40_000_000
            ):
                raise ValueError()
            img.verify()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
        raise AppError(
            "imagen_tipo", "Usa JPEG, PNG o WebP válida, de hasta 40 megapíxeles."
        )
    key = uid()
    ext, mime = {
        "JPEG": ("jpg", "image/jpeg"),
        "PNG": ("png", "image/png"),
        "WEBP": ("webp", "image/webp"),
    }[fmt]
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    path = settings.data_dir / f"{key}.{ext}"
    path.write_bytes(raw)
    record = File(id=key, path=str(path), mime=mime, size=len(raw))
    db.add(record)
    db.flush()
    pub.file_id, pub.revision = record.id, pub.revision + 1
    db.commit()
    return publication_detail(db, pub)


class FileEdit(BaseModel):
    alt: str = Field(default="", max_length=1000)
    wp_id: int | None = Field(default=None, ge=1)


@app.put("/api/files/{file_id}", dependencies=[Depends(require_session)])
def file_put(file_id: str, data: FileEdit, db=Depends(get_db)) -> dict:
    record = get_record(db, File, file_id)
    pub = db.scalar(
        select(Publication).where(Publication.file_id == file_id).with_for_update()
    )
    if pub:
        editable(db, pub)
    record.alt = data.alt
    if data.wp_id:
        record.wp_id, record.upload_uncertain = data.wp_id, False
    if pub:
        pub.revision += 1
    db.commit()
    return {"id": record.id, "alt": record.alt, "wp_id": record.wp_id}


@app.get("/api/files/{file_id}", dependencies=[Depends(require_session)])
def file_get(file_id: str, db=Depends(get_db)):
    record = get_record(db, File, file_id)
    return FileResponse(
        record.path,
        media_type=record.mime,
        headers={"Content-Disposition": "inline", "X-Content-Type-Options": "nosniff"},
    )


@app.post("/api/sync/blog", status_code=202, dependencies=[Depends(require_session)])
def sync_blog(db=Depends(get_db)) -> dict:
    return serialize(enqueue(db, "sync_blog", {}, "sync:blog"))


@app.get("/api/taxonomy", dependencies=[Depends(require_session)])
def taxonomy_get(db=Depends(get_db)) -> dict:
    row = db.get(Configuration, "taxonomy")
    return row.value if row else {"categories": [], "tags": []}


@app.post("/api/sync/metrics", status_code=202, dependencies=[Depends(require_session)])
def metrics_sync(data: MetricsInput, db=Depends(get_db)) -> dict:
    if date.fromisoformat(data.start) > date.fromisoformat(data.end):
        raise AppError("periodo", "La fecha inicial debe ser anterior a la final.")
    return serialize(enqueue(db, "metrics", data.model_dump(), "sync:metrics"))


@app.get("/api/metrics", dependencies=[Depends(require_session)])
def metrics_get(db=Depends(get_db)) -> dict:
    return statistical_signals(db)


@app.get("/api/jobs", dependencies=[Depends(require_session)])
def jobs_get(db=Depends(get_db)) -> list[dict]:
    return [
        serialize(j)
        for j in db.scalars(select(Job).order_by(Job.created_at.desc()).limit(50)).all()
    ]


@app.get("/api/jobs/{job_id}", dependencies=[Depends(require_session)])
def job_get(job_id: str, db=Depends(get_db)) -> dict:
    return serialize(get_record(db, Job, job_id))


@app.post("/api/jobs/{job_id}/cancel", dependencies=[Depends(require_session)])
def job_cancel(job_id: str, db=Depends(get_db)) -> dict:
    job = get_record(db, Job, job_id)
    job.cancel_requested = True
    if job.state == "pendiente":
        job.state, job.active_key = "cancelado", None
    db.commit()
    return serialize(job)


@app.post("/api/jobs/{job_id}/resume", dependencies=[Depends(require_session)])
def job_resume(job_id: str, db=Depends(get_db)) -> dict:
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if not job or job.state not in ("fallido", "interrumpido", "parcial", "cancelado"):
        raise AppError(
            "trabajo_no_reanudable", "Este trabajo no se puede reanudar.", 409
        )
    if job.kind == "li_publish":
        raise AppError(
            "linkedin_no_reintentar",
            "No repitas una creación de LinkedIn; reconcilia primero el resultado.",
            409,
        )
    if job.result and not job.error:
        raise AppError(
            "trabajo_ya_completo",
            "El trabajo acabó con pendientes editoriales. Edita la publicación o inicia otra operación.",
            409,
        )
    if job.parameters.get("publication_id"):
        pub = db.get(Publication, job.parameters["publication_id"])
        expected = job.checkpoints.get(
            "managed_revision", job.parameters.get("base_revision")
        )
        if expected is not None and pub.revision != expected:
            raise AppError(
                "reanudacion_conflicto",
                "La publicación cambió después de este trabajo.",
                409,
                "Inicia una nueva operación sobre la versión actual; los checkpoints antiguos se conservan.",
            )
    job.active_key = (
        "publication:" + job.parameters["publication_id"]
        if job.parameters.get("publication_id")
        else (
            "sync:blog"
            if job.kind == "sync_blog"
            else "sync:metrics"
            if job.kind == "metrics"
            else None
        )
    )
    job.state, job.attempts, job.cancel_requested, job.error = "pendiente", 0, False, {}
    job.available_at = now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            "trabajo_activo", "Ya hay otro trabajo activo para este recurso.", 409
        )
    return serialize(job)


class Reconcile(BaseModel):
    remote_id: str = Field(min_length=1, max_length=200)
    revision: int


@app.post(
    "/api/publications/{pub_id}/reconcile-linkedin",
    dependencies=[Depends(require_session)],
)
def reconcile_linkedin(pub_id: str, data: Reconcile, db=Depends(get_db)) -> dict:
    pub = db.scalar(
        select(Publication).where(Publication.id == pub_id).with_for_update()
    )
    if not pub:
        raise AppError("no_encontrado", "La publicación no existe.", 404)
    editable(db, pub)
    revision(pub, data.revision)
    if pub.li_status not in ("incierto", "enviando"):
        raise AppError(
            "linkedin_reconciliacion", "Solo se reconcilian envíos inciertos.", 409
        )
    pub.li_id, pub.li_status = data.remote_id, "publicado"
    pub.revision += 1
    db.commit()
    return publication_detail(db, pub)


@app.get("/api/costs", dependencies=[Depends(require_session)])
def costs_get(db=Depends(get_db)) -> dict:
    rows = db.scalars(
        select(AICall).order_by(AICall.created_at.desc()).limit(500)
    ).all()
    return {
        "currency": "USD",
        "calculated": str(
            sum((r.calculated_cost or Decimal(0) for r in rows), Decimal(0))
        ),
        "uncertain_reserved": str(
            sum(
                (r.estimated_cost or Decimal(0) for r in rows if r.uncertain),
                Decimal(0),
            )
        ),
        "scope": "Últimas 500 llamadas registradas. No es una conciliación con la factura.",
        "calls": [serialize(r) for r in rows],
    }


@app.get("/api/notifications", dependencies=[Depends(require_session)])
def notifications_get(db=Depends(get_db)) -> list[dict]:
    return [
        serialize(n)
        for n in db.scalars(
            select(Notification).order_by(Notification.created_at.desc()).limit(50)
        ).all()
    ]


@app.post("/api/notifications/read", dependencies=[Depends(require_session)])
def notifications_read(db=Depends(get_db)) -> dict:
    for n in db.scalars(select(Notification).where(Notification.read.is_(False))).all():
        n.read = True
    db.commit()
    return {"ok": True}
