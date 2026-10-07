from datetime import timedelta
from sqlalchemy import select, or_, and_, update
from sqlalchemy.exc import IntegrityError
from .db import now
from .models import Job, Context, Notification
from .catalog import preferences, model_option
from .errors import AppError


def enqueue(db, kind, parameters, active_key=None):
    if parameters.get("publication_id"):
        from .models import Publication

        pub = db.get(Publication, parameters["publication_id"])
        if pub:
            parameters = {**parameters, "base_revision": pub.revision}
    prefs = preferences(db)
    model = model_option(db, prefs["provider"], prefs["model"])
    context = db.scalar(select(Context).order_by(Context.created_at.desc()))
    selection = {**prefs, "rates": model}
    if prefs["fallback"]:
        selection["fallback_rates"] = model_option(
            db, prefs["fallback_provider"], prefs["fallback_model"]
        )
    job = Job(
        kind=kind,
        parameters=parameters,
        active_key=active_key,
        selection=selection,
        context_snapshot={
            "body": context.body if context else {},
            "revision": context.revision if context else 0,
        },
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Job).where(Job.active_key == active_key))
        if existing:
            return existing
        raise
    return job


def claim(db, owner):
    job = db.scalar(
        select(Job)
        .where(
            or_(
                and_(Job.state == "pendiente", Job.available_at <= now()),
                and_(Job.state == "ejecutando", Job.lease_until < now()),
            )
        )
        .order_by(Job.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not job:
        return None
    if job.cancel_requested:
        job.state, job.active_key = "cancelado", None
        db.commit()
        return None
    if job.attempts >= 3:
        job.state, job.active_key = "interrumpido", None
        job.error = {
            "code": "intentos_agotados",
            "message": "El trabajo agotó sus tres intentos técnicos.",
            "action": "Revisa el error y reanuda manualmente.",
        }
        db.commit()
        return None
    job.state, job.lease_owner, job.lease_until, job.heartbeat = (
        "ejecutando",
        owner,
        now() + timedelta(seconds=150),
        now(),
    )
    job.attempts += 1
    db.commit()
    return job.id


def assert_active(db, job, owner):
    db.refresh(job)
    if job.cancel_requested:
        raise AppError(
            "cancelado",
            "Trabajo cancelado; se conservan los resultados guardados.",
            409,
        )
    if job.lease_owner != owner or job.lease_until < now():
        raise AppError("lease_perdido", "Otro worker ha recuperado el trabajo.", 409)


def heartbeat(db, job_id, owner):
    return db.execute(
        update(Job)
        .where(Job.id == job_id, Job.lease_owner == owner, Job.state == "ejecutando")
        .values(heartbeat=now(), lease_until=now() + timedelta(seconds=150))
    ).rowcount


def checkpoint(db, job, key, data):
    job.checkpoints = {**job.checkpoints, key: data}
    db.commit()


def finish(db, job, state, result=None, error=None):
    job.state, job.active_key, job.lease_until = state, None, None
    job.progress = 100 if state == "terminado" else job.progress
    job.result = result or job.result
    job.error = error or {}
    job.phase = {
        "terminado": "Terminado",
        "parcial": "Revisión pendiente",
        "fallido": "Interrumpido por error",
        "cancelado": "Cancelado",
    }.get(state, state)
    db.add(
        Notification(
            message=f"{job.kind}: {job.phase}"
            + (f" — {job.error.get('message', '')}" if job.error else ""),
            kind="error" if error else "info",
            job_id=job.id,
        )
    )
    db.commit()
