import pytest
from app.content import clean_html, blocks
from app.seo import evaluate, stop_cycle
from app.errors import provider_error, AppError
from app.network import public_destination


def good_article():
    return {
        "title": "Automatización útil",
        "seo_title": "Automatización útil: cómo resolver problemas reales",
        "slug": "automatizacion-util",
        "keyphrase": "automatización útil",
        "meta_description": "La automatización útil ayuda a resolver problemas concretos. Aprende a elegir un proceso, evaluar sus límites y medir el resultado con criterio.",
        "body": "<p>La automatización útil comienza por entender un problema.</p><h2>Cómo diseñar una automatización útil</h2><p>"
        + " ".join(
            [
                "Un proceso claro evita errores y permite dedicar tiempo a decisiones que requieren criterio."
            ]
            * 25
        )
        + '</p><a href="https://germanmallo.com/blog/">Blog</a><a href="https://developer.wordpress.org/">Fuente</a>',
        "excerpt": "",
        "categories": [],
        "tags": [],
        "image_alt": "",
    }


def test_reproducible_score_and_meaningful_bad_input():
    a = good_article()
    result = evaluate(a, "https://germanmallo.com")
    assert result == evaluate(a, "https://germanmallo.com")
    assert result["score"] >= 70
    assert evaluate({"body": "Hola", "title": "Hola"})["score"] < 30
    assert result["coverage"] < 100
    assert "Imagen manual y alt pendientes" in result["pending_site_checks"]
    assert (
        evaluate({**a, "body": a["body"] + "<p>Edición</p>"})["fingerprint"]
        != result["fingerprint"]
    )


def test_cycle_limits_and_no_improvement():
    assert stop_cycle([70]) == "umbral"
    assert stop_cycle([20, 30, 40, 50, 60, 65]) == "maximo_mejoras"
    assert stop_cycle([60, 59, 58]) == "sin_mejora"
    assert stop_cycle([50, 55, 54]) is None
    assert stop_cycle([50, 55, 54, 55]) == "sin_mejora"


def test_sanitization_and_block_serialization():
    body = '<h1>Título</h1><p onclick="alert(1)">Texto <a href="javascript:alert(1)">malo</a></p><script>secreto()</script><h3>Detalle</h3><ul><li>Primero</li></ul>'
    cleaned = clean_html(body)
    assert (
        "<h1>" not in cleaned
        and "<h2>" in cleaned
        and "onclick" not in cleaned
        and "javascript" not in cleaned
        and "secreto" not in cleaned
    )
    result = blocks(cleaned)
    assert (
        "<!-- wp:paragraph -->" in result
        and '<!-- wp:heading {"level": 3} -->' in result
    )
    assert "<!-- wp:html -->" in result
    from app.content import text

    assert text(result) == text(cleaned)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1",
        "file:///etc/passwd",
        "http://user:password@example.com",
        "https://example.com:9999",
    ],
)
def test_ssrf_blocks_internal_and_invalid_destinations(url):
    with pytest.raises(AppError):
        public_destination(url)


def test_dns_mixed_public_private_is_blocked(monkeypatch):
    monkeypatch.setattr(
        "socket.getaddrinfo",
        lambda *a, **k: [
            (2, 1, 6, "", ("8.8.8.8", 80)),
            (2, 1, 6, "", ("127.0.0.1", 80)),
        ],
    )
    with pytest.raises(AppError):
        public_destination("https://example.com")


def test_provider_error_classification():
    assert (
        provider_error(429, {"error": {"code": "insufficient_quota"}}).code
        == "facturacion_cuota"
    )
    assert provider_error(429, {}).code == "saturacion"
    assert provider_error(401, {}).code == "autenticacion_proveedor"
    assert provider_error(403, {}).code == "permisos_proveedor"
    assert (
        provider_error(
            400, {"error": {"message": "Your credit balance is too low"}}
        ).code
        == "credito_agotado"
    )
