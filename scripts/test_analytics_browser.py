"""UI regression using explicitly simulated analytics, never production data."""

import json
from datetime import date, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
out = root / "docs" / "screenshots"
out.mkdir(exist_ok=True)
start = date(2026, 7, 1)
series = [
    {
        "date": (start + timedelta(days=i)).isoformat(),
        "views": 40 + i % 14,
        "sessions": 30 + i % 7,
        "clicks": 10 + i % 5,
        "impressions": 100 + i,
    }
    for i in range(70)
]
article = {
    "id": "test-article",
    "title": "Python para automatizar tareas",
    "url": "https://example.com/python/",
    "topic": "Python",
    "format": "tutorial",
    "age_days": 150,
    "words": 1200,
    "seo_score": 75,
    "ga4": {"views": 400, "sessions": 300, "engagement_rate": 0.65},
    "search_console": {"clicks": 30, "impressions": 1000, "ctr": 0.03, "position": 9},
    "observed_days": 60,
    "views_per_observed_day": 6.7,
    "change": -0.32,
    "ctr_interval": [0.02, 0.04],
    "engagement_interval": [0.59, 0.70],
    "sparse": False,
}
group = {
    "label": "Python",
    "articles": 3,
    "measured_articles": 3,
    "views": 1000,
    "clicks": 60,
    "median_daily_views": 8,
}
dashboard = {
    "start": "2026-07-01",
    "end": "2026-09-08",
    "state": "disponible",
    "totals": {
        "ga4": {"views": 3500, "sessions": 2400},
        "search_console": {"clicks": 850, "impressions": 14000},
    },
    "series": series,
    "articles": [article],
    "themes": [group],
    "formats": [{**group, "label": "tutorial"}],
    "queries": [
        {
            "query": "automatizar con python",
            "publication_id": "test-article",
            "page": "https://example.com/python/",
            "clicks": 30,
            "impressions": 1000,
            "ctr": 0.03,
            "position": 9,
            "sparse": False,
        }
    ],
    "recommendations": [
        {
            "kind": "explorar",
            "title": "Explorar automatización con Python",
            "publication_id": "test-article",
            "evidence": "1000 impresiones y posición media 9. Datos simulados exclusivamente para esta prueba.",
            "brief": "Investiga automatización con Python y contrasta el histórico.",
        }
    ],
    "sources": [
        {
            "source": "linkedin / referral",
            "views": 70,
            "sessions": 50,
            "engagement_rate": 0.6,
        }
    ],
    "temporal": [
        {
            "metric": "views",
            "observed": 70,
            "anomalies": [],
            "forecast": None,
            "weekday": [{"day": i, "mean": 50 + i, "n": 10} for i in range(7)],
        }
    ],
    "correlations": [{"feature": "words", "n": 1, "rho": None}],
    "coverage": {
        "ga4_days": 70,
        "search_console_days": 70,
        "days": 70,
        "unmapped_rows": 2,
        "partial_rows": 100,
        "imports": [],
    },
    "methodology": [
        "Datos simulados para regresión visual; no son resultados del propietario."
    ],
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    writes = []

    def route(r):
        path = r.request.url.split("/api", 1)[1].split("?", 1)[0]
        if r.request.method != "GET":
            writes.append(path)
        value = []
        if path == "/auth/session":
            value = {"username": "test", "csrf": "test"}
        elif path == "/preferences":
            value = {
                "app_name": "Prueba de analítica",
                "provider": "openai",
                "model": "test",
            }
        elif path == "/catalog":
            value = {"version": "test", "models": []}
        elif path == "/analytics":
            value = dashboard
        elif path == "/estimate":
            value = {"currency": "USD", "low": None, "high": None, "assumptions": {}}
        elif path == "/sync/metrics":
            value = {"id": "test-import", "kind": "metrics", "state": "pendiente"}
        r.fulfill(status=200, content_type="application/json", body=json.dumps(value))

    page.route("**/api/**", route)
    page.goto("http://127.0.0.1:18086/?view=analitica")
    expect(page.get_by_role("heading", name="Analítica editorial.")).to_be_visible()
    expect(page.get_by_role("img")).to_be_visible()
    page.screenshot(path=str(out / "analytics-desktop-test.png"), full_page=True)
    page.get_by_role("tab", name="Qué funciona").click()
    expect(page.get_by_role("button", name=article["title"])).to_be_visible()
    page.get_by_role("tab", name="Demanda y canales").click()
    expect(
        page.get_by_role("cell", name="automatizar con python", exact=False)
    ).to_be_visible()
    page.get_by_role("tab", name="Análisis estadístico").click()
    expect(page.get_by_text("Sin muestra", exact=True)).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_role("tab", name="Evolución y decisiones").click()
    page.screenshot(path=str(out / "analytics-mobile-test.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
        "Mobile overflow"
    )
    page.get_by_role("button", name="Preparar idea", exact=True).click()
    expect(page.locator('textarea[name="instructions"]')).to_have_value(
        dashboard["recommendations"][0]["brief"]
    )
    assert not writes, "Preparing an idea must not initiate paid generation"
    assert not errors, errors
    browser.close()
    print(
        "PASS analytics tabs, chart, mobile layout, recommendation prefill; no automatic AI writes"
    )
