import httpx
import pytest
from app.models import Connection, Publication, Idea, Metric, File
from app.security import encrypt
from app.services import save_version, statistical_signals
from app.schemas import Article
from app.integrations import send_wordpress, send_linkedin, check_public, sync_metrics
from app.errors import AppError
from tests.fakes import FakeWordPress
from tests.test_content_seo import good_article


@pytest.fixture
def wp_pub(db, monkeypatch):
    FakeWordPress.reset()
    monkeypatch.setattr("app.integrations.WordPress", FakeWordPress)
    db.add(
        Connection(
            provider="wordpress",
            config={"url": "https://germanmallo.com", "username": "test"},
            encrypted=encrypt({"application_password": "test-only"}),
        )
    )
    db.add(
        Connection(
            provider="linkedin",
            config={},
            encrypted=encrypt({"access_token": "test-only", "person_id": "123"}),
        )
    )
    idea = Idea(title="Automatización útil", summary="Resumen", angle="Enfoque")
    db.add(idea)
    db.flush()
    pub = Publication(title=idea.title, idea_id=idea.id)
    db.add(pub)
    db.flush()
    version = save_version(
        db,
        pub,
        "wordpress",
        Article.model_validate(good_article()).model_dump(),
        "initial",
    )
    save_version(
        db,
        pub,
        "linkedin",
        {"text": "Una reflexión propia."},
        "manual",
        based_on=version.id,
    )
    db.commit()
    return pub


def test_wp_partial_seo_repair_same_post_and_lost_creation(db, wp_pub):
    FakeWordPress.fail_seo = True
    with pytest.raises(AppError):
        send_wordpress(db, wp_pub, None)
    assert (
        wp_pub.wp_id
        and wp_pub.wp_status == "parcial"
        and wp_pub.confirmations["content"]
        and not wp_pub.confirmations["seo"]
    )
    FakeWordPress.fail_seo = False
    send_wordpress(db, wp_pub, None)
    assert (
        wp_pub.wp_status == "draft"
        and all(wp_pub.confirmations.values())
        and FakeWordPress.creates == 1
    )
    assert FakeWordPress.meta[wp_pub.wp_id]["seo_title"] == good_article()["seo_title"]
    second = Publication(title="Otra publicación")
    db.add(second)
    db.flush()
    save_version(db, second, "wordpress", good_article(), "initial")
    db.commit()
    FakeWordPress.lose_response = True
    with pytest.raises(AppError) as exc:
        send_wordpress(db, second, None)
    assert exc.value.code == "wordpress_incierto" and second.wp_id is None
    send_wordpress(db, second, None)
    assert second.wp_id and FakeWordPress.creates == 2


def test_wordpress_image_alt_and_readback(db, wp_pub, tmp_path):
    path = tmp_path / "image.png"
    path.write_bytes(b"test-upload")
    file = File(
        path=str(path), mime="image/png", size=11, alt="Una captura explicativa"
    )
    db.add(file)
    db.flush()
    wp_pub.file_id = file.id
    db.commit()
    send_wordpress(db, wp_pub, None)
    assert file.wp_id == 50 and FakeWordPress.medias[50]["alt_text"] == file.alt
    assert FakeWordPress.posts[wp_pub.wp_id]["featured_media"] == 50
    assert wp_pub.confirmations["image"]
    send_wordpress(db, wp_pub, None)
    assert len(FakeWordPress.medias) == 1


def test_external_edits_not_overwritten_or_published_regressed(db, wp_pub):
    send_wordpress(db, wp_pub, None)
    remote = FakeWordPress.posts[wp_pub.wp_id]
    remote["content"]["raw"] = "<p>Cambio externo</p>"
    remote["modified_gmt"] = "2026-10-05T11:00:00"
    with pytest.raises(AppError) as exc:
        send_wordpress(db, wp_pub, None)
    assert (
        exc.value.code == "cambios_externos"
        and remote["content"]["raw"] == "<p>Cambio externo</p>"
    )
    remote["status"] = "publish"
    with pytest.raises(AppError) as exc:
        send_wordpress(db, wp_pub, None)
    assert exc.value.code == "wordpress_no_borrador" and remote["status"] == "publish"


@pytest.mark.parametrize(
    "status,password",
    [
        ("draft", ""),
        ("future", ""),
        ("private", ""),
        ("pending", ""),
        ("publish", "secret"),
    ],
)
def test_linkedin_blocks_non_public_backend_and_ui_contract(
    db, wp_pub, authed, status, password, monkeypatch
):
    send_wordpress(db, wp_pub, None)
    FakeWordPress.posts[wp_pub.wp_id].update(status=status, password=password)
    sent = []
    monkeypatch.setattr("app.integrations.request_json", lambda *a, **k: sent.append(a))
    with pytest.raises(AppError):
        send_linkedin(db, wp_pub, None)
    assert not sent
    response = authed.post(
        "/api/publications/" + wp_pub.id + "/actions/publish-linkedin", json={}
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "mode", ["inaccessible", "login", "redirect", "different_canonical"]
)
def test_public_check_does_not_accept_200_login_or_other_page(mode, monkeypatch):
    post = {
        "status": "publish",
        "password": "",
        "link": "https://germanmallo.com/article/",
        "content": {
            "raw": "<p>Este es el contenido original de un artículo con suficiente texto para verificar identidad</p>"
        },
    }
    status = 404 if mode == "inaccessible" else 200
    body = (
        '<form id="loginform">Login</form>'
        if mode == "login"
        else post["content"]["raw"]
    )
    if mode == "different_canonical":
        body += '<link rel="canonical" href="https://germanmallo.com/other/">'
    url = "https://germanmallo.com/login/" if mode == "redirect" else post["link"]
    monkeypatch.setattr(
        "app.integrations.public_get",
        lambda u: httpx.Response(
            status,
            text=body,
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        ),
    )
    with pytest.raises(AppError):
        check_public(post)


def test_public_post_allows_explicit_linkedin_and_prevents_duplicate(
    db, wp_pub, monkeypatch
):
    send_wordpress(db, wp_pub, None)
    # Mark reviewed against a remote version: WordPress status-only update shouldn't silently approve changed content.
    remote = FakeWordPress.posts[wp_pub.wp_id]
    remote["status"] = "publish"
    from app.integrations import set_remote

    set_remote(wp_pub, remote)
    db.commit()
    monkeypatch.setattr(
        "app.integrations.public_get",
        lambda url: httpx.Response(
            200,
            text=remote["content"]["raw"],
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        ),
    )
    sent = []

    def send(method, url, **kwargs):
        sent.append(kwargs["json"])
        return {}, httpx.Response(201, headers={"x-restli-id": "urn:li:share:100"})

    monkeypatch.setattr("app.integrations.request_json", send)
    result = send_linkedin(db, wp_pub, None)
    assert result["status"] == "publicado" and sent[0]["commentary"].endswith(
        wp_pub.canonical_url
    )
    assert (
        sent[0]["lifecycleState"] == "PUBLISHED"
        and sent[0]["distribution"]["feedDistribution"] == "MAIN_FEED"
    )
    with pytest.raises(AppError):
        send_linkedin(db, wp_pub, None)
    assert len(sent) == 1 and db.get(Idea, wp_pub.idea_id).status == "utilizada"


@pytest.mark.parametrize("failure", ["timeout", "server_error"])
def test_timeout_linkedin_stays_uncertain(db, wp_pub, monkeypatch, failure):
    send_wordpress(db, wp_pub, None)
    remote = FakeWordPress.posts[wp_pub.wp_id]
    remote["status"] = "publish"
    from app.integrations import set_remote

    set_remote(wp_pub, remote)
    db.commit()
    monkeypatch.setattr(
        "app.integrations.public_get",
        lambda url: httpx.Response(
            200,
            text=remote["content"]["raw"],
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        ),
    )

    def fail(*a, **k):
        if failure == "server_error":
            raise AppError(
                "proveedor_saturado", "Respuesta ambigua", 503, transient=True
            )
        raise httpx.ReadTimeout("Lost response")

    monkeypatch.setattr("app.integrations.request_json", fail)
    with pytest.raises(AppError) as exc:
        send_linkedin(db, wp_pub, None)
    assert exc.value.code == "linkedin_incierto" and wp_pub.li_status == "incierto"
    with pytest.raises(AppError):
        send_linkedin(db, wp_pub, None)


def test_metric_url_history_and_weighted_ratios(db, wp_pub, monkeypatch):
    wp_pub.wp_id = 10
    wp_pub.canonical_url = "https://germanmallo.com/new/"
    wp_pub.url_history = ["https://germanmallo.com/old/"]
    db.commit()
    db.add(
        Connection(
            provider="search_console",
            config={"site_url": "sc-domain:germanmallo.com"},
            encrypted=encrypt({"service_account": {}}),
        )
    )
    db.commit()
    monkeypatch.setattr(
        "app.integrations.search_console_report",
        lambda *a: [
            {
                "keys": ["https://germanmallo.com/old/", "a"],
                "clicks": 10,
                "impressions": 100,
                "ctr": 0.1,
                "position": 10,
            },
            {
                "keys": ["https://germanmallo.com/new/", "b"],
                "clicks": 30,
                "impressions": 900,
                "ctr": 30 / 900,
                "position": 2,
            },
        ],
    )
    sync_metrics(db, "search_console", "2026-09-01", "2026-09-30")
    metrics = statistical_signals(db)["signals"]
    assert len(metrics) == 1
    assert (
        metrics[0]["publication_id"] == wp_pub.id
        and metrics[0]["values"]["ctr"] == 0.04
    )
    assert (
        metrics[0]["values"]["position"] == 2.8 and metrics[0]["quality"] == "parcial"
    )
    sync_metrics(db, "search_console", "2026-09-01", "2026-09-30")
    assert db.query(Metric).count() == 2


def test_metrics_empty_is_not_low_performance(db, monkeypatch):
    assert statistical_signals(db)["state"] == "sin_datos"
    db.add(
        Connection(
            provider="ga4",
            config={"property_id": "123"},
            encrypted=encrypt({"service_account": {}}),
        )
    )
    db.commit()
    monkeypatch.setattr("app.integrations.ga4_report", lambda *a: ([], {}, False))
    result = sync_metrics(db, "ga4", "2026-09-01", "2026-09-30")
    assert (
        result["quality"] == "sin_datos"
        and db.query(Metric).one().quality == "sin_datos"
    )


def test_equivalent_metric_periods_and_article_age(db, wp_pub):
    from datetime import timedelta
    from app.db import now

    wp_pub.published_at = now() - timedelta(days=75)
    for start, end, clicks in [
        ("2026-08-01", "2026-08-30", 20),
        ("2026-09-01", "2026-09-30", 30),
        ("2026-07-01", "2026-07-10", 200),
    ]:
        db.add(
            Metric(
                publication_id=wp_pub.id,
                provider="search_console",
                period_start=start,
                period_end=end,
                dimensions={"page": "/test/"},
                values={"clicks": clicks, "impressions": 1000, "position": 3},
                quality="parcial",
            )
        )
    db.commit()
    result = statistical_signals(db)
    comparison = result["comparisons"][0]
    assert comparison["previous"] == ["2026-08-01", "2026-08-30"]
    assert comparison["difference"] == 10 and comparison["relative_change"] == 0.5
    assert comparison["quality"] == "parcial"
    assert all(signal["article_age_days"] == 75 for signal in result["signals"])


def test_image_changes_invalidate_evaluation_without_rewriting_article(db, wp_pub):
    from app.models import Version
    from app.services import evaluate_version, publication_detail

    version = db.get(Version, wp_pub.current_wp)
    file = File(
        path="/data/test.png", mime="image/png", size=100, alt="Descripción inicial"
    )
    db.add(file)
    db.flush()
    wp_pub.file_id = file.id
    evaluate_version(db, wp_pub, version)
    db.commit()
    assert not publication_detail(db, wp_pub)["evaluation_stale"]
    file.alt = "Descripción revisada"
    db.commit()
    assert publication_detail(db, wp_pub)["evaluation_stale"]
    assert wp_pub.current_wp == version.id
