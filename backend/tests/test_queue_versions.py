from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from app.db import SessionLocal, now
from app.models import Idea, Publication, Version
from app.jobs import enqueue, claim, heartbeat, checkpoint
from app.services import (
    current_context,
    save_version,
    evaluate_version,
    publication_detail,
)
from app.schemas import Article


def test_atomic_claim_and_lease_recovery(db):
    current_context(db)
    job = enqueue(db, "ideas", {"quantity": 1})

    def compete(owner):
        with SessionLocal() as s:
            return claim(s, owner)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(compete, ["first", "second"]))
    assert results.count(job.id) == 1 and results.count(None) == 1
    db.refresh(job)
    owner = job.lease_owner
    checkpoint(db, job, "research", {"sources": ["persistent"]})
    job.lease_until = now() - timedelta(seconds=1)
    db.commit()
    assert claim(db, "recovered") == job.id
    assert job.checkpoints["research"]["sources"] == ["persistent"]
    assert heartbeat(db, job.id, owner) == 0
    assert heartbeat(db, job.id, "recovered") == 1


def test_active_key_and_selector_snapshot(db):
    from app.models import Configuration

    current_context(db)
    first = enqueue(db, "wp_send", {"publication_id": "example"}, "publication:example")
    duplicate = enqueue(
        db, "wp_send", {"publication_id": "example"}, "publication:example"
    )
    assert duplicate.id == first.id
    db.add(
        Configuration(
            key="preferences",
            value={"provider": "anthropic", "model": "claude-sonnet-5-5"},
        )
    )
    db.commit()
    second = enqueue(db, "ideas", {"quantity": 1})
    assert first.selection["provider"] == "openai"
    assert second.selection["provider"] == "anthropic"


def test_versions_invalidate_evaluation_and_preserve_linkedin(db):
    pub = Publication(title="Una idea")
    db.add(pub)
    db.flush()
    article = Article(title="Una idea", body="<p>Texto original</p>").model_dump()
    v = save_version(db, pub, "wordpress", article, "initial")
    evaluate_version(db, pub, v)
    save_version(
        db, pub, "linkedin", {"text": "Mi edición propia"}, "manual", based_on=v.id
    )
    db.commit()
    assert publication_detail(db, pub)["evaluation"]
    assert save_version(db, pub, "wordpress", article, "unchanged").id == v.id
    edited = save_version(
        db, pub, "wordpress", {**article, "body": "<p>Contenido cambiado</p>"}, "manual"
    )
    db.commit()
    assert publication_detail(db, pub)["evaluation"] is None and pub.li_stale
    assert db.get(Version, pub.current_li).data["text"] == "Mi edición propia"
    assert edited.id != v.id


def test_idea_one_publication_concurrency(authed, db):
    idea = Idea(title="La idea", summary="Resumen", angle="Enfoque")
    db.add(idea)
    db.commit()
    a = authed.post("/api/ideas/" + idea.id + "/publication", json={"research": False})
    b = authed.post("/api/ideas/" + idea.id + "/publication", json={"research": False})
    assert (
        a.status_code == 202
        and a.json()["publication_id"] == b.json()["publication_id"]
    )
    db.refresh(idea)
    assert idea.status == "pendiente"
    assert db.query(Publication).count() == 1


def test_optimistic_edit_and_busy_protection(authed, db):
    pub = Publication(title="Publicación")
    db.add(pub)
    db.commit()
    a = Article(title="Título nuevo").model_dump()
    assert (
        authed.put(
            "/api/publications/" + pub.id + "/wordpress",
            json={"revision": 1, "data": a},
        ).status_code
        == 200
    )
    assert (
        authed.put(
            "/api/publications/" + pub.id + "/wordpress",
            json={"revision": 1, "data": a},
        ).status_code
        == 409
    )
    db.refresh(pub)
    enqueue(db, "correct", {"publication_id": pub.id}, "publication:" + pub.id)
    assert (
        authed.put(
            "/api/publications/" + pub.id + "/wordpress",
            json={"revision": pub.revision, "data": a},
        ).status_code
        == 409
    )
