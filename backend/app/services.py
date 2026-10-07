from sqlalchemy import select, func, literal_column
from .db import now
from .models import (
    Context,
    Idea,
    Publication,
    Version,
    Evaluation,
    Source,
    Metric,
    File,
)
from .schemas import Article, LinkedInText
from .content import fingerprint, clean_html, relevant, terms
from .seo import evaluate, RULE_VERSION

INITIAL_CONTEXT = {
    "profile": "Germán Mallo Faure, graduado en Ciencia de Datos por la Universitat Politècnica de València. Desarrollo, IA aplicada y automatización: Python, datos, APIs, aplicaciones y RAG.",
    "projects": "La web del propietario presenta un chatbot personal con RAG y soluciones de IA, datos y automatización. Revisar y ampliar cada ficha antes de narrar experiencias con clientes o resultados concretos.",
    "goals": "Divulgar con precisión y mostrar criterio y capacidad para resolver problemas reales.",
    "audience": "Estudiantes, profesionales, empresarios y personas que llegan desde LinkedIn o la web.",
    "tone": "Directo y cercano. Ejemplos y analogías. Crítica y personalidad cuando encaje. Ajustar estructura y nivel a cada idea.",
    "avoid": "Relleno, repetición de keywords, cierres comerciales agresivos y experiencias personales inventadas.",
    "confirmed_facts": "Graduado en Ciencia de Datos por la UPV. Experiencia en desarrollo, IA aplicada y automatización (datos proporcionados por el propietario).",
    "style_examples": "",
    "references": [
        {
            "url": "https://germanmallo.com/",
            "role": "referencia_vigente_consultada_en_desarrollo",
            "consulted_at": "2026-10-05",
        },
        {"url": "https://germanmallo.com/blog/", "role": "ejemplos_historicos"},
        {
            "url": "https://www.linkedin.com/in/german-mallo/",
            "role": "perfil_facilitado_por_propietario",
        },
    ],
}


def current_context(db):
    ctx = db.scalar(select(Context).order_by(Context.created_at.desc()))
    if not ctx:
        ctx = Context(body=INITIAL_CONTEXT.copy())
        db.add(ctx)
        db.commit()
    return ctx


def history(db, query=""):
    ideas = db.scalars(select(Idea).order_by(Idea.updated_at.desc()).limit(30)).all()
    publications = db.scalars(
        select(Publication).order_by(Publication.updated_at.desc()).limit(30)
    ).all()
    if query and terms(query):
        q = func.to_tsquery(
            literal_column("'spanish'"), " | ".join(sorted(terms(query))[:30])
        )
        vector = func.to_tsvector(
            literal_column("'spanish'"),
            Idea.title + " " + Idea.summary + " " + Idea.angle + " " + Idea.topic,
        )
        matches = db.scalars(
            select(Idea)
            .where(vector.op("@@")(q))
            .order_by(func.ts_rank_cd(vector, q).desc())
            .limit(60)
        ).all()
        ideas = list({i.id: i for i in [*matches, *ideas]}.values())
        vector = func.to_tsvector(literal_column("'spanish'"), Publication.title)
        matches = db.scalars(
            select(Publication)
            .where(vector.op("@@")(q))
            .order_by(func.ts_rank_cd(vector, q).desc())
            .limit(60)
        ).all()
        publications = list({p.id: p for p in [*matches, *publications]}.values())
    items = [
        {
            "id": x.id,
            "entity": "idea",
            "title": x.title,
            "summary": x.summary,
            "angle": x.angle,
            "topic": x.topic,
            "status": x.status,
            "discard_reason": x.discard_reason,
            "notes": x.notes,
        }
        for x in ideas
    ]
    for p in publications:
        v = db.get(Version, p.current_wp) if p.current_wp else None
        items.append(
            {
                "id": p.id,
                "entity": "publication",
                "title": p.title,
                "summary": v.data.get("excerpt", "") if v else "",
                "keyphrase": v.data.get("keyphrase", "") if v else "",
                "status": p.wp_status,
                "url": p.canonical_url,
            }
        )
    return relevant(query, items, 30) if query else items[:30]


def statistical_signals(db):
    rows = db.scalars(
        select(Metric).order_by(Metric.updated_at.desc()).limit(1000)
    ).all()
    if not rows:
        return {
            "state": "sin_datos",
            "message": "No hay métricas consultadas. Genera con contexto e historial.",
            "signals": [],
        }
    groups = {}
    for r in rows:
        if not r.publication_id:
            continue
        key = (r.publication_id, r.provider, r.period_start, r.period_end)
        g = groups.setdefault(
            key,
            {
                "publication_id": r.publication_id,
                "provider": r.provider,
                "start": r.period_start,
                "end": r.period_end,
                "quality": r.quality,
                "values": {},
                "position_weighted_sum": 0.0,
                "linkedin_sessions": 0.0,
            },
        )
        for name, value in r.values.items():
            if name not in ("ctr", "position"):
                g["values"][name] = g["values"].get(name, 0) + value
        if r.provider == "search_console":
            g["position_weighted_sum"] += r.values.get("position", 0) * r.values.get(
                "impressions", 0
            )
        if "linkedin" in r.dimensions.get("source_medium", "").casefold():
            g["linkedin_sessions"] += r.values.get("sessions", 0)
    for g in groups.values():
        v = g["values"]
        if g["provider"] == "search_console":
            v["ctr"] = v.get("clicks", 0) / max(1, v.get("impressions", 0))
            v["position"] = g["position_weighted_sum"] / max(1, v.get("impressions", 0))
            g["message"] = (
                "Hay pocos datos para concluir."
                if v.get("impressions", 0) < 100
                else f"Este artículo recibió {v.get('clicks', 0):g} clics en este periodo; no demuestra causalidad."
            )
        else:
            v["engagement_rate"] = v.get("engaged_sessions", 0) / max(
                1, v.get("sessions", 0)
            )
            g["message"] = (
                "Las sesiones sumadas por página pueden contar una sesión en varias páginas; no son sesiones únicas del sitio."
            )
        pub = db.get(Publication, g["publication_id"])
        idea = db.get(Idea, pub.idea_id) if pub.idea_id else None
        g.update(
            title=pub.title,
            topic=idea.topic if idea else "histórico",
            angle=idea.angle if idea else "",
            content_type=idea.content_type if idea else "",
            article_age_days=(now() - pub.published_at).days
            if pub.published_at
            else None,
        )
        g.pop("position_weighted_sum")
    from datetime import date

    comparisons = []
    all_signals = list(groups.values())
    for current in all_signals:
        length = (
            date.fromisoformat(current["end"]) - date.fromisoformat(current["start"])
        ).days
        previous = [
            s
            for s in all_signals
            if s["publication_id"] == current["publication_id"]
            and s["provider"] == current["provider"]
            and s["end"] < current["start"]
            and (date.fromisoformat(s["end"]) - date.fromisoformat(s["start"])).days
            == length
        ]
        if not previous:
            continue
        prior = max(previous, key=lambda s: s["end"])
        key = "clicks" if current["provider"] == "search_console" else "views"
        current_count, prior_count = (
            current["values"].get(key, 0),
            prior["values"].get(key, 0),
        )
        enough = (
            min(
                current["values"].get("impressions", current_count),
                prior["values"].get("impressions", prior_count),
            )
            >= 100
        )
        comparisons.append(
            {
                "publication_id": current["publication_id"],
                "title": current["title"],
                "provider": current["provider"],
                "current": [current["start"], current["end"]],
                "previous": [prior["start"], prior["end"]],
                "indicator": key,
                "difference": current_count - prior_count,
                "relative_change": (current_count - prior_count) / prior_count
                if prior_count
                else None,
                "quality": "muestra_escasa"
                if not enough
                else "parcial"
                if "parcial" in (current["quality"], prior["quality"])
                else "disponible",
                "message": "Comparación descriptiva de ventanas equivalentes; no demuestra causalidad. Considera la antigüedad del artículo.",
            }
        )
    return {
        "state": "disponible" if groups else "sin_datos",
        "signals": all_signals[:60],
        "comparisons": comparisons[:30],
        "message": "Compara periodos equivalentes y antigüedad. GA4 y Search Console miden fenómenos distintos.",
    }


def save_version(db, pub, channel, data, reason, snapshot=None, based_on=None):
    if channel == "wordpress":
        data = Article.model_validate(data).model_dump()
        data["body"] = clean_html(data["body"])
        old_id = pub.current_wp
    else:
        data = LinkedInText.model_validate(data).model_dump()
        old_id = pub.current_li
    old = db.get(Version, old_id) if old_id else None
    fp = fingerprint(data)
    if (
        old
        and old.fingerprint == fp
        and (channel == "wordpress" or old.based_on == based_on)
    ):
        return old
    version = Version(
        publication_id=pub.id,
        channel=channel,
        reason=reason,
        data=data,
        fingerprint=fp,
        context_snapshot=snapshot or {},
        based_on=based_on,
    )
    db.add(version)
    db.flush()
    if channel == "wordpress":
        pub.current_wp, pub.title = version.id, data["title"]
        if pub.current_li:
            pub.li_stale = True
    else:
        pub.current_li, pub.li_stale = version.id, False
    pub.revision += 1
    db.flush()
    return version


def evaluate_version(db, pub, version):
    from .models import Connection

    connection = db.scalar(select(Connection).where(Connection.provider == "wordpress"))
    site = (
        connection.config.get("url", "") if connection else "https://germanmallo.com/"
    )
    phrases = [
        v.data.get("keyphrase", "")
        for v in db.scalars(
            select(Version).where(
                Version.channel == "wordpress", Version.publication_id != pub.id
            )
        ).all()
    ]
    data = dict(version.data)
    file = db.get(File, pub.file_id) if pub.file_id else None
    if file:
        data["image_alt"] = file.alt
    result = evaluate(data, site_url=site, image=bool(file), used_keyphrases=phrases)
    evaluated_fingerprint = fingerprint(
        {"article": data, "image": {"id": file.id, "alt": file.alt} if file else None}
    )
    result["fingerprint"] = evaluated_fingerprint
    ev = Evaluation(
        version_id=version.id,
        fingerprint=evaluated_fingerprint,
        evaluator=RULE_VERSION,
        score=result["score"],
        result=result,
    )
    db.add(ev)
    db.flush()
    return ev


def serialize(record):
    return {c.name: getattr(record, c.name) for c in record.__table__.columns}


def publication_detail(db, pub):
    data = serialize(pub)
    wp = db.get(Version, pub.current_wp) if pub.current_wp else None
    li = db.get(Version, pub.current_li) if pub.current_li else None
    evaluation = (
        db.scalar(
            select(Evaluation)
            .where(Evaluation.version_id == pub.current_wp)
            .order_by(Evaluation.created_at.desc())
            .limit(1)
        )
        if wp
        else None
    )
    file = db.get(File, pub.file_id) if pub.file_id else None
    current_data = (
        {**wp.data, **({"image_alt": file.alt} if file else {})} if wp else {}
    )
    evaluated_fingerprint = fingerprint(
        {
            "article": current_data,
            "image": {"id": file.id, "alt": file.alt} if file else None,
        }
    )
    data.update(
        wordpress=serialize(wp) if wp else None,
        linkedin=serialize(li) if li else None,
        evaluation=serialize(evaluation)
        if evaluation and evaluation.fingerprint == evaluated_fingerprint
        else None,
        evaluation_stale=bool(
            wp and (not evaluation or evaluation.fingerprint != evaluated_fingerprint)
        ),
        image={**serialize(file), "path": f"/api/files/{file.id}"} if file else None,
        sources=[
            serialize(s)
            for s in db.scalars(
                select(Source).where(Source.publication_id == pub.id)
            ).all()
        ],
    )
    return data
