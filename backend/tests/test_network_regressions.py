import gzip
import httpx
import pytest
from app.network import public_get
from app.errors import AppError


def test_pinned_dns_retains_tls_sni_and_decompresses_once(monkeypatch):
    monkeypatch.setattr(
        "socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("8.8.8.8", 443))]
    )
    seen = []

    def response(request):
        seen.append(request)
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html", "Content-Encoding": "gzip"},
            content=gzip.compress(b"<p>Verified public content</p>"),
        )

    original = httpx.Client
    monkeypatch.setattr(
        "app.network.httpx.Client",
        lambda **kwargs: original(transport=httpx.MockTransport(response), **kwargs),
    )
    result = public_get("https://public.example/article")
    assert result.text == "<p>Verified public content</p>"
    assert seen[0].url.host == "8.8.8.8" and seen[0].headers["host"] == "public.example"
    assert seen[0].extensions["sni_hostname"] == "public.example"


def test_redirects_are_checked_before_internal_fetch(monkeypatch):
    def dns(host, *a, **k):
        return [(2, 1, 6, "", ("127.0.0.1" if host == "127.0.0.1" else "8.8.8.8", 80))]

    monkeypatch.setattr("socket.getaddrinfo", dns)
    seen = []

    def response(request):
        seen.append(request)
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/private"})

    original = httpx.Client
    monkeypatch.setattr(
        "app.network.httpx.Client",
        lambda **kwargs: original(transport=httpx.MockTransport(response), **kwargs),
    )
    with pytest.raises(AppError) as exc:
        public_get("https://public.example/")
    assert exc.value.code == "url_no_permitida" and len(seen) == 1
