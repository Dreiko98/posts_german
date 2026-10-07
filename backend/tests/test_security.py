from app.models import Connection, User
from app.security import digest


def test_all_private_data_requires_session(client):
    for path in [
        "/context",
        "/ideas",
        "/publications",
        "/connections",
        "/catalog",
        "/costs",
        "/jobs",
        "/metrics",
        "/notifications",
        "/openapi.json",
        "/files/absent",
    ]:
        assert client.get("/api" + path).status_code == 401
    assert client.post("/api/ideas/generate", json={"quantity": 5}).status_code == 401


def test_login_cookie_logout_and_csrf(authed):
    assert authed.get("/api/auth/session").status_code == 200
    assert authed.cookies.get("studio_session")
    assert (
        authed.put(
            "/api/preferences", headers={"X-CSRF-Token": "wrong"}, json={}
        ).status_code
        == 403
    )
    assert (
        authed.put(
            "/api/preferences", headers={"Origin": "https://evil.invalid"}, json={}
        ).status_code
        == 403
    )
    assert authed.post("/api/auth/logout").status_code == 200
    assert authed.get("/api/ideas").status_code == 401


def test_persistent_login_limit(client, db):
    for _ in range(5):
        assert (
            client.post(
                "/api/auth/login",
                headers={"Origin": "http://localhost:8080"},
                json={"username": "x", "password": "wrong"},
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login",
            headers={"Origin": "http://localhost:8080"},
            json={"username": "another", "password": "wrong"},
        ).status_code
        == 429
    )


def test_secrets_encrypted_never_echoed(authed, db):
    secret = "private-secret-not-for-frontend"
    response = authed.put(
        "/api/connections/openai", json={"config": {}, "secrets": {"api_key": secret}}
    )
    assert response.status_code == 200
    assert secret not in response.text
    row = db.query(Connection).one()
    assert secret not in row.encrypted and row.encrypted
    assert secret not in authed.get("/api/connections").text
    invalid = authed.put(
        "/api/connections/openai",
        json={"config": {}, "secrets": {"api_key": secret}, "bad": secret},
    )
    assert invalid.status_code == 422 and secret not in invalid.text
    leakage = authed.put(
        "/api/connections/openai", json={"config": {"api_key": secret}, "secrets": {}}
    )
    assert leakage.status_code == 400 and secret not in leakage.text


def test_password_change_revokes_other_sessions(authed, db):
    from app.models import Session
    from app.db import now
    from datetime import timedelta

    user = db.query(User).one()
    db.add(
        Session(
            user_id=user.id,
            token_hash=digest("another"),
            csrf="x",
            expires_at=now() + timedelta(hours=1),
        )
    )
    db.commit()
    assert (
        authed.put(
            "/api/auth/password",
            json={"current": "test-password-strong", "new": "new-test-password-strong"},
        ).status_code
        == 200
    )
    assert db.query(Session).count() == 1
    assert authed.get("/api/auth/session").status_code == 200
