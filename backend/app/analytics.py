"""Descriptive editorial analytics over real daily observations; no paid AI calls."""

import math
import re
import unicodedata
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, median
from urllib.parse import quote, urlparse
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from .db import now
from .errors import AppError
from .models import (
    AnalyticsRow,
    AnalyticsBatch,
    Publication,
    Idea,
    Version,
    Evaluation,
    Connection,
    Configuration,
    AICall,
)
from .security import connection_data
from .integrations import google_token
from .network import request_json


def validate_period(start, end):
    try:
        a, b = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        raise AppError("periodo", "Introduce fechas válidas.")
    if a > b or (b - a).days >= 180 or b > date.today():
        raise AppError(
            "periodo",
            "Selecciona hasta 180 días, con el inicio anterior al fin y sin fechas futuras.",
        )
    return a, b


def sync_daily(db, provider, start, end):
    validate_period(start, end)
    config = connection_data(db, provider)
    prop = str(config.get("property_id" if provider == "ga4" else "site_url", ""))
    token = google_token(
        config,
        [
            "https://www.googleapis.com/auth/"
            + ("analytics.readonly" if provider == "ga4" else "webmasters.readonly")
        ],
    )
    summary = {}
    for dataset in ("site", "content"):
        dimensions = (
            (
                ["date"]
                if dataset == "site"
                else ["date", "pagePath", "sessionSourceMedium"]
            )
            if provider == "ga4"
            else (["date"] if dataset == "site" else ["date", "page", "query"])
        )
        rows, offset, metadata, truncated = [], 0, {}, False
        while True:
            if provider == "ga4":
                data, _ = request_json(
                    "POST",
                    f"https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport",
                    headers={"Authorization": "Bearer " + token},
                    json={
                        "dateRanges": [{"startDate": start, "endDate": end}],
                        "dimensions": [{"name": x} for x in dimensions],
                        "metrics": [
                            {"name": x}
                            for x in (
                                "sessions",
                                "screenPageViews",
                                "engagedSessions",
                                "eventCount",
                            )
                        ],
                        "offset": offset,
                        "limit": 10000,
                        "orderBys": [{"dimension": {"dimensionName": "date"}}],
                    },
                )
                batch = data.get("rows", [])
                metadata = data.get("metadata", {})
                done = offset + len(batch) >= data.get("rowCount", 0)
            else:
                data, _ = request_json(
                    "POST",
                    "https://www.googleapis.com/webmasters/v3/sites/"
                    + quote(prop, safe="")
                    + "/searchAnalytics/query",
                    headers={"Authorization": "Bearer " + token},
                    json={
                        "startDate": start,
                        "endDate": end,
                        "dimensions": dimensions,
                        "rowLimit": 25000,
                        "startRow": offset,
                        "dataState": "final",
                        "type": "web",
                    },
                )
                batch = data.get("rows", [])
                done = len(batch) < 25000
            rows.extend(batch)
            offset += len(batch)
            if done or not batch or offset >= 100000:
                truncated = not done and bool(batch)
                break
        metadata = {
            **metadata,
            "truncated": truncated,
            "query_rows_partial": provider == "search_console" and dataset == "content",
            "time_basis": "Fecha de la propiedad GA4"
            if provider == "ga4"
            else "Fecha Search Console (Pacific Time)",
            "type": "web",
        }
        quality = (
            "parcial"
            if truncated
            or metadata.get("subjectToThresholding")
            or metadata.get("samplingMetadatas")
            or metadata.get("dataLossFromOtherRow")
            or metadata["query_rows_partial"]
            else "disponible"
        )
        # Replace overlapping observations atomically; repeated refreshes never add duplicate visits.
        db.execute(
            delete(AnalyticsRow).where(
                AnalyticsRow.provider == provider,
                AnalyticsRow.property == prop,
                AnalyticsRow.dataset == dataset,
                AnalyticsRow.day >= start,
                AnalyticsRow.day <= end,
            )
        )
        for row in rows:
            if provider == "ga4":
                keys = [x["value"] for x in row["dimensionValues"]]
                raw_day = keys[0]
                day = f"{raw_day[:4]}-{raw_day[4:6]}-{raw_day[6:8]}"
                values = dict(
                    zip(
                        ("sessions", "views", "engaged_sessions", "events"),
                        (float(x["value"]) for x in row["metricValues"]),
                    )
                )
                dims = (
                    {}
                    if dataset == "site"
                    else {"page": keys[1], "source_medium": keys[2]}
                )
            else:
                keys = row["keys"]
                day = keys[0]
                values = {
                    k: float(row[k])
                    for k in ("clicks", "impressions", "ctr", "position")
                }
                dims = {} if dataset == "site" else {"page": keys[1], "query": keys[2]}
            if start <= day <= end:
                db.add(
                    AnalyticsRow(
                        provider=provider,
                        property=prop,
                        dataset=dataset,
                        day=day,
                        dimensions=dims,
                        values=values,
                        quality=quality,
                    )
                )
        db.add(
            AnalyticsBatch(
                provider=provider,
                property=prop,
                dataset=dataset,
                start=start,
                end=end,
                metadata_=metadata,
                rows=len(rows),
            )
        )
        db.commit()
        summary[dataset] = {"rows": len(rows), "quality": quality}
    return summary


def wilson(success, total):
    if total <= 0:
        return None
    p = max(0, min(1, success / total))
    z = 1.96
    center = (p + z * z / (2 * total)) / (1 + z * z / total)
    delta = (
        z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / (1 + z * z / total)
    )
    return [max(0, center - delta), min(1, center + delta)]


def aggregate(rows):
    values = defaultdict(float)
    weighted = 0
    for row in rows:
        for key, value in row.values.items():
            if key not in ("ctr", "position"):
                values[key] += value
        weighted += row.values.get("position", 0) * row.values.get("impressions", 0)
    if "impressions" in values:
        values["ctr"] = (
            values.get("clicks", 0) / values["impressions"]
            if values["impressions"]
            else 0
        )
        values["position"] = (
            weighted / values["impressions"] if values["impressions"] else 0
        )
    if "sessions" in values:
        values["engagement_rate"] = (
            values.get("engaged_sessions", 0) / values["sessions"]
            if values["sessions"]
            else 0
        )
    return dict(values)


def temporal(series, metric):
    known = [(x["date"], x.get(metric)) for x in series if x.get(metric) is not None]
    anomalies, forecast = [], None
    for i in range(14, len(series)):
        current = series[i].get(metric)
        history = [
            x.get(metric)
            for x in series[max(0, i - 28) : i]
            if x.get(metric) is not None
        ]
        if current is None or len(history) < 14:
            continue
        center = median(history)
        mad = median([abs(x - center) for x in history])
        scale = max(1, 1.4826 * mad)
        if abs(current - center) > 3.5 * scale and abs(current - center) >= 5:
            anomalies.append(
                {
                    "date": series[i]["date"],
                    "metric": metric,
                    "value": current,
                    "baseline": center,
                    "direction": "subida" if current > center else "bajada",
                }
            )
    # Forecast only with 42 consecutive observed daily totals and a held-out week.
    last = series[-56:]
    if len(last) >= 42 and all(x.get(metric) is not None for x in last):
        values = [x[metric] for x in last]
        train, actual = values[:-7], values[-7:]
        level = mean(train[-7:])
        baseline_error = mean(abs(x - level) for x in actual)
        seasonal = train[-7:]
        seasonal_error = mean(abs(a - b) for a, b in zip(actual, seasonal))
        method = (
            "Semana anterior" if seasonal_error < baseline_error else "Media de 7 días"
        )
        prediction = (
            values[-7:] if method == "Semana anterior" else [mean(values[-7:])] * 7
        )
        error = min(seasonal_error, baseline_error)
        forecast = {
            "method": method,
            "backtest_mae": error,
            "points": [
                {
                    "date": (
                        date.fromisoformat(last[-1]["date"]) + timedelta(days=i + 1)
                    ).isoformat(),
                    "value": v,
                    "low": max(0, v - 2 * error),
                    "high": v + 2 * error,
                }
                for i, v in enumerate(prediction)
            ],
            "message": "Proyección descriptiva a 7 días. Banda ±2 MAE del último backtest; no es un intervalo probabilístico calibrado.",
        }
    weekday = []
    for day in range(7):
        vals = [v for d, v in known if date.fromisoformat(d).weekday() == day]
        weekday.append(
            {"day": day, "mean": mean(vals) if vals else None, "n": len(vals)}
        )
    return {
        "metric": metric,
        "anomalies": anomalies[-12:],
        "forecast": forecast,
        "weekday": weekday,
        "observed": len(known),
    }


def ranks(values):
    ordered = sorted(set(values))
    return (
        [
            sum(i + 1 for i, x in enumerate(sorted(values)) if x == v) / values.count(v)
            for v in values
        ]
        if ordered
        else []
    )


def spearman(x, y):
    if len(x) < 10:
        return None
    a, b = ranks(x), ranks(y)
    ma, mb = mean(a), mean(b)
    denom = math.sqrt(sum((v - ma) ** 2 for v in a) * sum((v - mb) ** 2 for v in b))
    return sum((u - ma) * (v - mb) for u, v in zip(a, b)) / denom if denom else None


def analytics_dashboard(db, start, end):
    a, b = validate_period(start, end)
    connections = {c.provider: c for c in db.scalars(select(Connection)).all()}
    all_rows = db.scalars(
        select(AnalyticsRow).where(AnalyticsRow.day >= start, AnalyticsRow.day <= end)
    ).all()
    rows = [
        r
        for r in all_rows
        if r.provider in connections
        and r.property
        == str(
            connections[r.provider].config.get(
                "property_id" if r.provider == "ga4" else "site_url", ""
            )
        )
    ]
    batches = [
        x
        for x in db.scalars(
            select(AnalyticsBatch).order_by(AnalyticsBatch.created_at.desc())
        ).all()
        if x.provider in connections
        and x.property
        == str(
            connections[x.provider].config.get(
                "property_id" if x.provider == "ga4" else "site_url", ""
            )
        )
        and x.start <= end
        and x.end >= start
    ]
    site = [r for r in rows if r.dataset == "site"]
    by_day = defaultdict(list)
    for r in site:
        by_day[r.day].append(r)
    series = []
    for i in range((b - a).days + 1):
        day = (a + timedelta(days=i)).isoformat()
        item = {
            "date": day,
            **{k: None for k in ("views", "sessions", "clicks", "impressions")},
        }
        for provider in ("ga4", "search_console"):
            item.update(aggregate([r for r in by_day[day] if r.provider == provider]))
        series.append(item)
    pubs = db.scalars(select(Publication)).all()
    pathmap = {}
    for p in pubs:
        for url in p.url_history + [p.canonical_url]:
            if url:
                pathmap[urlparse(url).path.rstrip("/")] = p.id
    grouped, queries, sources = defaultdict(list), defaultdict(list), defaultdict(list)
    unmapped = 0
    for row in rows:
        if row.dataset != "content":
            continue
        pub_id = pathmap.get(urlparse(row.dimensions.get("page", "")).path.rstrip("/"))
        if pub_id:
            grouped[pub_id].append(row)
        else:
            unmapped += 1
        if row.dimensions.get("query"):
            queries[
                (row.dimensions["query"], pub_id, row.dimensions.get("page", ""))
            ].append(row)
        if row.dimensions.get("source_medium"):
            sources[row.dimensions["source_medium"]].append(row)
    taxonomy = db.get(Configuration, "taxonomy")
    categories = {
        x["id"]: x["name"]
        for x in (taxonomy.value.get("categories", []) if taxonomy else [])
    }
    articles = []
    for p in pubs:
        metrics = grouped[p.id]
        idea = db.get(Idea, p.idea_id) if p.idea_id else None
        version = db.get(Version, p.current_wp) if p.current_wp else None
        data = version.data if version else {}
        category = ", ".join(
            categories.get(x, str(x)) for x in data.get("categories", [])
        )
        words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", data.get("body", ""))))
        evaluations = (
            db.scalars(
                select(Evaluation)
                .where(Evaluation.version_id == p.current_wp)
                .order_by(Evaluation.created_at.desc())
                .limit(1)
            ).first()
            if p.current_wp
            else None
        )
        ga = aggregate([r for r in metrics if r.provider == "ga4"])
        sc = aggregate([r for r in metrics if r.provider == "search_console"])
        midpoint = a + timedelta(days=((b - a).days + 1) // 2)
        current = [
            r for r in metrics if r.provider == "ga4" and r.day >= midpoint.isoformat()
        ]
        previous = [
            r for r in metrics if r.provider == "ga4" and r.day < midpoint.isoformat()
        ]
        days_current = len({r.day for r in current})
        days_previous = len({r.day for r in previous})
        change = None
        if days_current >= 7 and days_previous >= 7:
            previous_rate = aggregate(previous).get("views", 0) / days_previous
            current_rate = aggregate(current).get("views", 0) / days_current
            change = (current_rate / previous_rate - 1) if previous_rate else None
        observed = len({r.day for r in metrics if r.provider == "ga4"})
        age = (now() - p.published_at).days if p.published_at else None
        articles.append(
            {
                "id": p.id,
                "title": p.title,
                "url": p.canonical_url,
                "topic": idea.topic if idea else category or "Sin clasificar",
                "format": idea.content_type if idea else "Histórico sin clasificar",
                "age_days": age,
                "words": words,
                "seo_score": evaluations.score
                if evaluations
                and version
                and evaluations.fingerprint == version.fingerprint
                else None,
                "ga4": ga,
                "search_console": sc,
                "observed_days": observed,
                "views_per_observed_day": ga.get("views", 0) / observed
                if observed
                else None,
                "change": change,
                "ctr_interval": wilson(sc.get("clicks", 0), sc.get("impressions", 0)),
                "engagement_interval": wilson(
                    ga.get("engaged_sessions", 0), ga.get("sessions", 0)
                ),
                "sparse": ga.get("sessions", 0) < 30 and sc.get("impressions", 0) < 100,
            }
        )
    articles.sort(key=lambda x: x["ga4"].get("views", 0), reverse=True)
    themes = defaultdict(list)
    formats = defaultdict(list)
    for article in articles:
        themes[article["topic"]].append(article)
        formats[article["format"]].append(article)

    def group_summary(groups):
        return sorted(
            [
                {
                    "label": label,
                    "articles": len(items),
                    "measured_articles": sum(
                        bool(x["ga4"] or x["search_console"]) for x in items
                    ),
                    "views": sum(x["ga4"].get("views", 0) for x in items),
                    "clicks": sum(x["search_console"].get("clicks", 0) for x in items),
                    "median_daily_views": median(
                        [
                            x["views_per_observed_day"]
                            for x in items
                            if x["views_per_observed_day"] is not None
                        ]
                    )
                    if any(x["views_per_observed_day"] is not None for x in items)
                    else None,
                }
                for label, items in groups.items()
            ],
            key=lambda x: x["views"],
            reverse=True,
        )

    opportunities = []
    for (query, pub_id, page), qrows in queries.items():
        v = aggregate(qrows)
        opportunities.append(
            {
                "query": query,
                "publication_id": pub_id,
                "page": page,
                **v,
                "sparse": v.get("impressions", 0) < 100,
            }
        )
    opportunities.sort(key=lambda x: x.get("impressions", 0), reverse=True)
    recommendations = []
    theme_summary = group_summary(themes)
    for group in theme_summary:
        if group["measured_articles"] >= 3 and group["views"] >= 100:
            recommendations.append(
                {
                    "kind": "continuar",
                    "title": "Probar una continuación sobre " + group["label"],
                    "publication_id": None,
                    "evidence": f"{group['measured_articles']} artículos con métricas y {group['views']:g} vistas en el periodo. Mediana: {group['median_daily_views'] or 0:.1f} vistas por día observado. Es una hipótesis editorial basada en el histórico, no una garantía de rendimiento.",
                    "priority": group["views"] * 0.01,
                    "brief": "Propón una continuación útil sobre "
                    + group["label"]
                    + ". Revisa todos los artículos, ideas y descartes relacionados; conserva el enfoque propio y explica qué aporta de nuevo.",
                }
            )
    for article in articles:
        v = article["search_console"]
        peers = [
            x["search_console"]["ctr"]
            for x in articles
            if x["id"] != article["id"]
            and x["search_console"].get("impressions", 0) >= 100
            and abs(x["search_console"].get("position", 100) - v.get("position", 100))
            <= 3
        ]
        if v.get("impressions", 0) >= 100 and 4 <= v.get("position", 0) <= 20:
            target = median(peers) if len(peers) >= 2 else None
            recommendations.append(
                {
                    "kind": "optimizar",
                    "title": "Mejorar «" + article["title"] + "»",
                    "publication_id": article["id"],
                    "evidence": f"{v['impressions']:g} impresiones, posición media {v['position']:.1f} y CTR {v['ctr']:.1%}."
                    + (
                        f" CTR mediano de {len(peers)} artículos con posición cercana: {target:.1%}."
                        if target is not None
                        else " No hay suficientes artículos comparables para estimar un CTR objetivo."
                    ),
                    "priority": v["impressions"]
                    * (max(0, target - v["ctr"]) if target is not None else 0.01),
                    "brief": "Revisar intención de búsqueda, título SEO y contenido de «"
                    + article["title"]
                    + "» con estas métricas; verificar las fuentes antes de actualizar.",
                }
            )
        if (
            article["change"] is not None
            and article["change"] < -0.3
            and article["ga4"].get("views", 0) >= 100
        ):
            recommendations.append(
                {
                    "kind": "actualizar",
                    "title": "Revisar caída de «" + article["title"] + "»",
                    "publication_id": article["id"],
                    "evidence": f"Las vistas por día observado han cambiado {article['change']:.0%} entre mitades del periodo. Puede reflejar antigüedad, cobertura o cambios de tráfico.",
                    "priority": article["ga4"].get("views", 0) * abs(article["change"]),
                    "brief": "Comprobar si ha quedado desactualizado y revisar fuentes y enfoque de «"
                    + article["title"]
                    + "».",
                }
            )
    existing = list(db.scalars(select(Idea)).all())

    def tokens(s):
        s = "".join(
            c
            for c in unicodedata.normalize("NFD", s.lower())
            if not unicodedata.combining(c)
        )
        return {x for x in re.findall(r"\w+", s) if len(x) > 3}

    seen_queries = set()
    for q in opportunities:
        if q["query"] in seen_queries or q["impressions"] < 100 or q["position"] < 8:
            continue
        seen_queries.add(q["query"])
        qt = tokens(q["query"])
        related = [
            i
            for i in existing
            if qt and len(qt & tokens(i.title + " " + i.summary)) / len(qt) >= 0.6
        ]
        if related:
            continue
        recommendations.append(
            {
                "kind": "explorar",
                "title": "Explorar «" + q["query"] + "»",
                "publication_id": q["publication_id"],
                "evidence": f"Consulta real: {q['impressions']:g} impresiones, {q['clicks']:g} clics y posición {q['position']:.1f}. No se encontró una idea con coincidencia léxica suficiente; hay que comprobar el solapamiento editorial.",
                "priority": q["impressions"] * 0.02,
                "brief": "Investiga una propuesta propia sobre «"
                + q["query"]
                + "». El histórico registra "
                + str(int(q["impressions"]))
                + " impresiones para esta consulta. Compara el artículo relacionado y todo el historial, incluidos descartes; plantea una continuación solo si aporta un enfoque diferente.",
            }
        )
    recommendations.sort(key=lambda x: x["priority"], reverse=True)
    measurable = [x for x in articles if x["observed_days"] >= 7]
    correlations = []
    for feature in ("words", "age_days", "seo_score"):
        items = [x for x in measurable if x[feature] is not None]
        correlations.append(
            {
                "feature": feature,
                "n": len(items),
                "rho": spearman(
                    [x[feature] for x in items],
                    [x["views_per_observed_day"] for x in items],
                ),
            }
        )
    ga_site = aggregate([r for r in site if r.provider == "ga4"])
    sc_site = aggregate([r for r in site if r.provider == "search_console"])
    source_summary = [
        {"source": name, **aggregate(items)} for name, items in sources.items()
    ]
    source_summary.sort(key=lambda x: x.get("views", 0), reverse=True)
    calls = db.scalars(select(AICall)).all()
    period_calls = [
        c
        for c in calls
        if start
        <= c.created_at.astimezone(ZoneInfo("Europe/Madrid")).date().isoformat()
        <= end
    ]
    production = {
        "ideas": {
            state: sum(i.status == state for i in existing)
            for state in ("pendiente", "seleccionada", "utilizada", "descartada")
        },
        "wordpress_published": sum(p.wp_status == "publish" for p in pubs),
        "linkedin_published": sum(p.li_status == "publicado" for p in pubs),
        "publications": len(pubs),
        "ai_calls": len(period_calls),
        "calculated_cost": float(sum(c.calculated_cost or 0 for c in period_calls)),
        "uncertain_reserved": float(
            sum(c.estimated_cost or 0 for c in period_calls if c.uncertain)
        ),
        "currency": "USD",
        "message": "Estados actuales de la biblioteca. Costes registrados en el periodo por fecha Europe/Madrid; reservas inciertas separadas. No representan ROI ni ingresos.",
    }
    return {
        "start": start,
        "end": end,
        "state": "disponible" if rows else "sin_datos",
        "totals": {"ga4": ga_site, "search_console": sc_site},
        "series": series,
        "articles": articles,
        "themes": theme_summary,
        "production": production,
        "formats": group_summary(formats),
        "queries": opportunities[:100],
        "recommendations": recommendations[:20],
        "sources": source_summary[:30],
        "temporal": [temporal(series, k) for k in ("views", "clicks")],
        "correlations": correlations,
        "coverage": {
            "ga4_days": sum(x["views"] is not None for x in series),
            "search_console_days": sum(x["clicks"] is not None for x in series),
            "days": len(series),
            "unmapped_rows": unmapped,
            "partial_rows": sum(r.quality == "parcial" for r in rows),
            "imports": [
                {
                    "provider": x.provider,
                    "dataset": x.dataset,
                    "start": x.start,
                    "end": x.end,
                    "rows": x.rows,
                    "imported_at": x.created_at.isoformat(),
                    "metadata": x.metadata_,
                }
                for x in batches[:8]
            ],
        },
        "methodology": [
            "Totales del sitio consultados separadamente: las sesiones de las páginas no se suman como sesiones únicas.",
            "Los días sin observaciones se muestran como huecos; no se inventan ceros.",
            "Las consultas de Search Console son filas principales y pueden omitir consultas anónimas. Las métricas detalladas no tienen por qué sumar los totales.",
            "GA4 usa la fecha de la propiedad; Search Console usa Pacific Time. No se equiparan sesiones y clics.",
            "CTR y engagement: intervalos Wilson al 95%, aproximados; las observaciones no necesariamente son independientes.",
            "Correlaciones Spearman requieren 10 artículos; muestran asociación, con posibles efectos de antigüedad y cobertura.",
            "Las prioridades son heurísticas versionadas (editorial-analytics-v1), no predicciones de visitas ni causalidad.",
            "La clasificación histórica procede de categorías WordPress; los formatos desconocidos permanecen sin clasificar.",
            "No se dispone de impresiones, likes o comentarios del perfil LinkedIn; solo tráfico atribuido por GA4.",
        ],
    }
