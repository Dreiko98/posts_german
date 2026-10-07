import signal
import threading
import uuid
from datetime import timedelta
from .db import SessionLocal, now
from .models import Job
from .jobs import claim, heartbeat, finish
from .tasks import run_task
from .errors import AppError

stopping = threading.Event()


def run_one(owner):
    with SessionLocal() as db:
        job_id = claim(db, owner)
        if not job_id:
            return False
    done = threading.Event()

    def keepalive():
        while not done.wait(15):
            with SessionLocal() as s:
                heartbeat(s, job_id, owner)
                from .models import Configuration

                health = s.get(Configuration, "worker_health") or Configuration(
                    key="worker_health"
                )
                health.value = {"heartbeat": now().isoformat()}
                s.add(health)
                s.commit()

    thread = threading.Thread(target=keepalive, daemon=True)
    thread.start()
    try:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            try:
                result = run_task(db, job, owner)
                db.refresh(job)
                if job.lease_owner != owner:
                    return True
                if job.cancel_requested:
                    finish(db, job, "cancelado", result)
                else:
                    finish(
                        db,
                        job,
                        "parcial"
                        if result.get("requires_review")
                        or result.get("partial")
                        or (
                            job.kind == "ideas"
                            and result.get("saved", 0) < result.get("requested", 0)
                        )
                        else "terminado",
                        result,
                    )
            except AppError as exc:
                db.rollback()
                job = db.get(Job, job_id)
                if job.lease_owner != owner:
                    return True
                if (
                    exc.transient
                    and job.attempts < 3
                    and job.kind not in ("li_publish", "wp_send")
                    and not job.cancel_requested
                ):
                    job.state = "pendiente"
                    job.available_at = now() + timedelta(
                        seconds=max(exc.retry_after, min(120, 10 * 2**job.attempts))
                    )
                    job.error = exc.public()
                    job.lease_until = None
                    db.commit()
                else:
                    finish(
                        db,
                        job,
                        "cancelado"
                        if exc.code == "cancelado"
                        else "parcial"
                        if job.checkpoints
                        else "fallido",
                        error=exc.public(),
                    )
            except Exception:
                db.rollback()
                job = db.get(Job, job_id)
                if job.lease_owner == owner:
                    # Do not log provider payloads, credentials or user content.
                    finish(
                        db,
                        job,
                        "parcial" if job.checkpoints else "fallido",
                        error={
                            "code": "error_interno",
                            "message": "Error interno; se conserva el progreso.",
                            "action": "Revisa la configuración o contacta con mantenimiento.",
                        },
                    )
    finally:
        done.set()
        thread.join(timeout=3)
    return True


def main():
    owner = str(uuid.uuid4())
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    signal.signal(signal.SIGINT, lambda *_: stopping.set())
    while not stopping.is_set():
        try:
            with SessionLocal() as db:
                # Healthcheck state independent of the job lease.
                from .models import Configuration

                record = db.get(Configuration, "worker_health") or Configuration(
                    key="worker_health"
                )
                record.value = {"heartbeat": now().isoformat()}
                db.add(record)
                db.commit()
            if not run_one(owner):
                stopping.wait(2)
        except Exception:
            stopping.wait(5)


if __name__ == "__main__":
    main()
