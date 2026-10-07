from datetime import date, timedelta
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app.analytics import (
    aggregate,
    wilson,
    temporal,
    spearman,
    sync_daily,
    analytics_dashboard,
    validate_period,
)
from app.models import AnalyticsRow, Connection, Publication, Idea
from app.errors import AppError


def test_weighted_ratios_and_uncertainty():
    rows = [
        SimpleNamespace(values={"clicks": 10, "impressions": 100, "position": 2}),
        SimpleNamespace(values={"clicks": 10, "impressions": 1000, "position": 12}),
    ]
    result = aggregate(rows)
    assert result["ctr"] == pytest.approx(20 / 1100)
    assert result["position"] == pytest.approx(12200 / 1100)
    assert wilson(0, 0) is None
    narrow = wilson(500, 1000)
    wide = wilson(5, 10)
    assert narrow[1] - narrow[0] < wide[1] - wide[0]


def test_temporal_gaps_backtest_and_tied_ranks():
    a = date(2026, 1, 1)
    points = [
        {"date": (a + timedelta(days=i)).isoformat(), "views": 10 + i % 7}
        for i in range(56)
    ]
    result = temporal(points, "views")
    assert result["forecast"]["method"] == "Semana anterior"
    assert result["forecast"]["backtest_mae"] == 0
    assert len(result["forecast"]["points"]) == 7
    points[30]["views"] = None
    assert temporal(points, "views")["forecast"] is None
    assert temporal(points[:10], "views")["forecast"] is None
    assert spearman(list(range(10)), list(reversed(range(10)))) == pytest.approx(-1)
    assert spearman([1] * 10, list(range(10))) is None
    assert spearman([1, 2], [2, 3]) is None


def test_daily_import_overlap_replaces_rows_and_preserves_summaries(db, monkeypatch):
    monkeypatch.setattr(
        "app.analytics.connection_data", lambda *a: {"property_id": "123"}
    )
    monkeypatch.setattr("app.analytics.google_token", lambda *a: "test")
    count = [2]

    def report(*args, **kwargs):
        body = kwargs["json"]
        assert body["dimensions"][0]["name"] == "date"
        keys = [{"value": "20260101"}]
        if len(body["dimensions"]) > 1:
            keys += [{"value": "/blog/example/"}, {"value": "google / organic"}]
        return {
            "rowCount": 1,
            "rows": [
                {
                    "dimensionValues": keys,
                    "metricValues": [{"value": str(count[0])}] * 4,
                }
            ],
        }, None

    monkeypatch.setattr("app.analytics.request_json", report)
    sync_daily(db, "ga4", "2026-01-01", "2026-01-02")
    count[0] = 7
    sync_daily(db, "ga4", "2026-01-01", "2026-01-03")
    rows = db.scalars(select(AnalyticsRow)).all()
    assert len(rows) == 2
    assert all(r.values["views"] == 7 for r in rows)


def test_dashboard_does_not_mix_properties_or_site_and_page_sessions(db):
    db.add(
        Connection(
            provider="ga4",
            config={"property_id": "123"},
            encrypted="",
            status="conectada",
            detail="",
        )
    )
    idea = Idea(
        title="Python",
        summary="",
        angle="",
        topic="Python",
        content_type="tutorial",
        rationale="",
        project_connection="",
        original_input="",
        origin="manual_guiado",
    )
    db.add(idea)
    db.flush()
    pub = Publication(
        title="Python útil",
        canonical_url="https://example.com/blog/python/",
        url_history=["https://example.com/old-python/"],
        idea_id=idea.id,
    )
    db.add(pub)
    db.flush()
    for dataset, page, sessions, prop in [
        ("site", "", 10, "123"),
        ("content", "/old-python/", 7, "123"),
        ("content", "/else/", 8, "123"),
        ("site", "", 1000, "999"),
    ]:
        db.add(
            AnalyticsRow(
                provider="ga4",
                property=prop,
                dataset=dataset,
                day="2026-01-01",
                dimensions={}
                if dataset == "site"
                else {"page": page, "source_medium": "google / organic"},
                values={
                    "sessions": sessions,
                    "views": sessions,
                    "engaged_sessions": sessions / 2,
                },
                quality="disponible",
            )
        )
    db.commit()
    d = analytics_dashboard(db, "2026-01-01", "2026-01-02")
    assert d["totals"]["ga4"]["sessions"] == 10
    assert d["articles"][0]["ga4"]["sessions"] == 7
    assert d["series"][1]["views"] is None
    assert d["coverage"]["unmapped_rows"] == 1
    assert d["temporal"][0]["forecast"] is None


def test_authenticated_endpoint_and_invalid_range(client, authed):
    assert (
        authed.get("/api/analytics?start=2026-01-01&end=2026-01-02").status_code == 200
    )
    assert (
        authed.get("/api/analytics?start=2026-01-02&end=2026-01-01").status_code == 400
    )
    with pytest.raises(AppError):
        validate_period("2026-01-01", "2026-12-31")
