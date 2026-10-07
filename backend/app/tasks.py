from sqlalchemy import select
from . import ai
from .models import Idea, Publication, Version, Source, Configuration
from .schemas import IdeaBatch, Relations, Article, EditorialReview, LinkedInText
from .content import text
from .services import history, statistical_signals, save_version, evaluate_version
from .jobs import assert_active, checkpoint
from .seo import stop_cycle
from .security import connection_data
from .integrations import (
    WordPress,
    set_remote,
    remote_hash,
    send_wordpress,
    send_linkedin,
    check_wordpress,
    sync_metrics,
)
from .errors import AppError
from .evidence import restrict_generated_links


def grounded_article(db, job, data, research):
    allowed = [s["url"] for s in research.get("sources", [])]
    allowed += [x["url"] for x in history(db, data["title"]) if x.get("url")]
    clean, warnings = restrict_generated_links(data, allowed)
    job.checkpoints = {
        **job.checkpoints,
        "source_warnings": [*job.checkpoints.get("source_warnings", []), *warnings],
    }
    return clean


def phase(db, job, owner, label, progress):
    assert_active(db, job, owner)
    job.phase, job.progress = label, progress
    db.commit()


def reference(db, job, query=""):
    return {
        "owner": job.context_snapshot,
        "history": history(db, query),
        "statistics": statistical_signals(db),
    }


def investigate(db, job, owner, query):
    if "research" in job.checkpoints:
        return job.checkpoints["research"]
    phase(db, job, owner, "Investigación de fuentes actuales", 10)
    result = ai.call(
        db,
        job,
        owner,
        "investigacion",
        "Usa la herramienta de búsqueda real para verificar el tema. Prioriza fuentes originales, conserva citas y distingue hechos de interpretación. No inventes fechas. Investiga: "
        + query,
        reference(db, job, query),
        research=True,
        remaining_calls=4,
    )
    checkpoint(db, job, "research", result)
    return result


def store_sources(db, research, idea_id=None, publication_id=None, version_id=None):
    for src in research.get("sources", []):
        if not src.get("url", "").startswith(("https://", "http://")):
            continue
        db.add(
            Source(
                idea_id=idea_id,
                publication_id=publication_id,
                version_id=version_id,
                url=src["url"],
                title=src.get("title", ""),
                excerpt=src.get("excerpt", ""),
                published_at=src.get("published_at"),
            )
        )


def ideas_task(db, job, owner):
    params = job.parameters
    query = (
        params.get("instructions")
        or "Ideas diversas de IA, datos, Python, automatización y proyectos; mezcla noticias y conocimiento útil."
    )
    research = (
        investigate(db, job, owner, query)
        if params.get("research")
        else {"state": "no_solicitada", "sources": []}
    )
    if "proposals" not in job.checkpoints:
        phase(db, job, owner, "Desarrollando enfoques editoriales", 35)
        result = ai.call(
            db,
            job,
            owner,
            "ideas",
            f"Desarrolla hasta {params['quantity']} ideas distintas y valiosas. "
            + (
                "Transforma esta única intención manual en una propuesta concreta: "
                if params.get("manual")
                else "Instrucciones opcionales: "
            )
            + query
            + ". Compara historial y razones de descarte. No rellenes para alcanzar la cantidad: explica faltantes. Incluye exploración y conocimiento sin noticia; no inventes rendimiento ni experiencias. Solo marca actualidad cuando la investigación la respalde.",
            {**reference(db, job, query), "research": research},
            IdeaBatch,
            remaining_calls=params["quantity"] + 2,
        )
        checkpoint(db, job, "proposals", result)
    proposals = job.checkpoints["proposals"]["ideas"][: params["quantity"]]
    saved = list(job.checkpoints.get("saved_ideas", []))
    duplicates = list(job.checkpoints.get("duplicates", []))
    for index, proposal in enumerate(proposals):
        if str(index) in job.checkpoints.get("processed", []):
            continue
        phase(
            db,
            job,
            owner,
            f"Comprobando solapamientos {index + 1}/{len(proposals)}",
            45 + round(45 * index / max(1, len(proposals))),
        )
        candidates = history(
            db, proposal["title"] + " " + proposal["summary"] + " " + proposal["angle"]
        )
        relations = []
        if candidates:
            key = f"relations_{index}"
            if key not in job.checkpoints:
                result = ai.call(
                    db,
                    job,
                    owner,
                    "solapamiento",
                    "Compara tema, intención y enfoque de la propuesta con estos registros. Clasifica duplicado, relacionado, continuación o distinto y explica la diferencia. IDs solo de los candidatos. No consideres sinónimos de título una diferencia de enfoque.",
                    {"proposal": proposal, "candidates": candidates},
                    Relations,
                    remaining_calls=len(proposals) - index,
                )
                checkpoint(db, job, key, result)
            valid_ids = {x["id"] for x in candidates}
            relations = [
                r
                for r in job.checkpoints[key]["relations"]
                if r["id"] in valid_ids and r["classification"] != "distinto"
            ]
        if any(r["classification"] == "duplicado" for r in relations):
            duplicates.append({"title": proposal["title"], "relations": relations})
        else:
            idea = Idea(
                **proposal,
                origin="manual_guiado" if params.get("manual") else "automatico",
                original_input=params.get("instructions", ""),
                context_snapshot=job.context_snapshot,
                batch_id=job.id,
                relations=relations,
                signals=statistical_signals(db)["signals"][:5],
            )
            db.add(idea)
            db.flush()
            store_sources(db, research, idea_id=idea.id)
            saved.append(idea.id)
        job.checkpoints = {
            **job.checkpoints,
            "processed": [*job.checkpoints.get("processed", []), str(index)],
            "saved_ideas": saved,
            "duplicates": duplicates,
        }
        db.commit()
    return {
        "idea_ids": saved,
        "requested": params["quantity"],
        "saved": len(saved),
        "duplicates": duplicates,
        "explanation": job.checkpoints["proposals"].get("explanation", "")
        + (
            f" Se guardaron {len(saved)} propuestas válidas."
            if len(saved) < params["quantity"]
            else ""
        ),
        "research_state": research["state"],
    }


def publication_task(db, job, owner):
    pub = db.get(Publication, job.parameters["publication_id"])
    idea = db.get(Idea, pub.idea_id) if pub.idea_id else None
    params = job.parameters
    query = params.get("angle") or (idea.angle if idea else pub.title)
    research = (
        investigate(db, job, owner, query)
        if params.get("research", False) or (idea and idea.current_news)
        else {"state": "no_solicitada", "sources": []}
    )
    scores = list(job.checkpoints.get("scores", []))
    versions = list(job.checkpoints.get("versions", []))
    if not versions:
        phase(db, job, owner, "Redacción inicial y metadatos", 30)
        data = ai.call(
            db,
            job,
            owner,
            "redaccion",
            "Redacta un artículo WordPress y sus metadatos. Extensión apropiada, sin longitud obligatoria; no incluyas H1 en el cuerpo. Usa fuentes verificadas y enlaces internos reales del historial. Frase clave sugerida: "
            + params.get("keyphrase", "")
            + ". Enfoque: "
            + query
            + ". Notas: "
            + params.get("notes", ""),
            {
                **reference(db, job, query),
                "idea": {"title": idea.title, "summary": idea.summary} if idea else {},
                "research": research,
            },
            Article,
            remaining_calls=3,
        )
        data = grounded_article(db, job, data, research)
        version = save_version(
            db, pub, "wordpress", data, "generacion_inicial", job.context_snapshot
        )
        store_sources(db, research, publication_id=pub.id, version_id=version.id)
        ev = evaluate_version(db, pub, version)
        versions.append(version.id)
        scores.append(ev.score)
        pub.best_wp = version.id
        job.checkpoints = {
            **job.checkpoints,
            "versions": versions,
            "scores": scores,
            "evaluations": [ev.id],
            "managed_revision": pub.revision,
        }
        db.commit()
    while not stop_cycle(scores):
        phase(db, job, owner, f"Mejora SEO {len(scores)}/5", 40 + len(scores) * 6)
        current = db.get(Version, versions[-1])
        from .models import Evaluation

        ev = db.get(Evaluation, job.checkpoints["evaluations"][-1])
        try:
            data = ai.call(
                db,
                job,
                owner,
                "mejora_seo",
                "Corrige de forma focalizada los problemas aplicables que no pasan. Conserva precisión, voz y fuentes. No inventes evidencia para subir el score. No necesitas una nueva búsqueda para esta ronda.",
                {
                    "article": current.data,
                    "problems": [
                        c
                        for c in ev.result["checks"]
                        if c["applicable"] and not c["passed"]
                    ],
                    "research": research,
                },
                Article,
                remaining_calls=3,
            )
        except AppError as exc:
            if exc.code == "limite_gasto":
                checkpoint(db, job, "stop_reason", "limite_gasto")
                break
            raise
        data = grounded_article(db, job, data, research)
        version = save_version(
            db,
            pub,
            "wordpress",
            data,
            "mejora_seo_" + str(len(scores)),
            job.context_snapshot,
        )
        ev = evaluate_version(db, pub, version)
        if ev.score > max(scores):
            pub.best_wp = version.id
        versions.append(version.id)
        scores.append(ev.score)
        job.checkpoints = {
            **job.checkpoints,
            "versions": versions,
            "scores": scores,
            "evaluations": [*job.checkpoints["evaluations"], ev.id],
            "managed_revision": pub.revision,
        }
        db.commit()
    pub.current_wp = pub.best_wp
    db.commit()
    best = db.get(Version, pub.best_wp)
    if "editorial" not in job.checkpoints:
        phase(db, job, owner, "Revisión editorial y de evidencia", 82)
        review = ai.call(
            db,
            job,
            owner,
            "revision_editorial",
            "Revisa claridad, repeticiones, precisión y evidencias. Señala afirmaciones sin fuente y experiencias personales no confirmadas. El score SEO no es prueba factual. No inventes verificaciones.",
            {"article": best.data, "owner": job.context_snapshot, "research": research},
            EditorialReview,
            remaining_calls=2,
        )
        from .models import Evaluation

        best_ev = db.scalar(
            select(Evaluation)
            .where(Evaluation.version_id == best.id)
            .order_by(Evaluation.created_at.desc())
        )
        best_ev.editorial = review
        best_ev.editorial = {
            **review,
            "warnings": [
                *review.get("warnings", []),
                *job.checkpoints.get("source_warnings", []),
            ],
        }
        checkpoint(db, job, "editorial", review)
    if "linkedin_version" not in job.checkpoints:
        phase(db, job, owner, "Adaptación con valor propio para LinkedIn", 92)
        data = ai.call(
            db,
            job,
            owner,
            "linkedin",
            "Adapta este artículo al perfil personal de LinkedIn. Aporta una idea o reflexión propia, no copies la introducción. Máximo 2.650 caracteres para reservar espacio al enlace definitivo. No inventes una URL si WordPress aún no está público. Emojis y hashtags opcionales.",
            {"article": best.data, "owner": job.context_snapshot},
            LinkedInText,
        )
        version = save_version(
            db,
            pub,
            "linkedin",
            data,
            "adaptacion_inicial",
            job.context_snapshot,
            best.id,
        )
        job.checkpoints = {**job.checkpoints, "managed_revision": pub.revision}
        checkpoint(db, job, "linkedin_version", version.id)
    return {
        "publication_id": pub.id,
        "best_version": pub.best_wp,
        "scores": scores,
        "stop_reason": job.checkpoints.get("stop_reason") or stop_cycle(scores),
        "requires_review": max(scores) < 70,
        "editorial": job.checkpoints.get("editorial", {}),
    }


def correction_task(db, job, owner):
    import re

    pub = db.get(Publication, job.parameters["publication_id"])
    version = db.get(Version, pub.current_wp)
    if not version:
        raise AppError("sin_borrador", "No hay un artículo para corregir.", 409)
    source_rows = db.scalars(
        select(Source).where(Source.publication_id == pub.id)
    ).all()
    evidence = {
        "sources": [
            {"url": s.url, "title": s.title, "excerpt": s.excerpt} for s in source_rows
        ]
    }
    if re.search(
        r"actualidad|noticia|últim|ultim|actualiza|verifica|nueva evidencia",
        job.parameters.get("instructions", ""),
        re.I,
    ):
        evidence = investigate(
            db, job, owner, job.parameters["instructions"] + " " + pub.title
        )
    if "corrected" not in job.checkpoints:
        phase(db, job, owner, "Corrección focalizada del artículo", 35)
        ev = evaluate_version(db, pub, version)
        db.commit()
        data = ai.call(
            db,
            job,
            owner,
            "correccion",
            "Modifica el artículo siguiendo estas instrucciones y los problemas SEO concretos. Preserva hechos y fuentes; no inventes experiencias. "
            + job.parameters.get("instructions", ""),
            {
                "article": version.data,
                "evaluation": ev.result,
                "owner": job.context_snapshot,
                "evidence": evidence,
            },
            Article,
            remaining_calls=2,
        )
        data = grounded_article(db, job, data, evidence)
        new = save_version(
            db, pub, "wordpress", data, "correccion_ia", job.context_snapshot
        )
        evaluation = evaluate_version(db, pub, new)
        job.checkpoints = {**job.checkpoints, "managed_revision": pub.revision}
        checkpoint(db, job, "corrected", {"version": new.id, "score": evaluation.score})
    if "editorial" not in job.checkpoints:
        new = db.get(Version, job.checkpoints["corrected"]["version"])
        review = ai.call(
            db,
            job,
            owner,
            "revision_editorial",
            "Revisa el texto corregido y sus evidencias. Señala afirmaciones no respaldadas y experiencias personales pendientes de confirmar. No trates el score SEO como evidencia.",
            {"article": new.data, "owner": job.context_snapshot, "evidence": evidence},
            EditorialReview,
        )
        from .models import Evaluation

        evaluation = db.scalar(
            select(Evaluation)
            .where(Evaluation.version_id == new.id)
            .order_by(Evaluation.created_at.desc())
        )
        evaluation.editorial = {
            **review,
            "warnings": [
                *review.get("warnings", []),
                *job.checkpoints.get("source_warnings", []),
            ],
        }
        checkpoint(db, job, "editorial", review)
    return {"publication_id": pub.id, **job.checkpoints["corrected"]}


def linkedin_task(db, job, owner):
    pub = db.get(Publication, job.parameters["publication_id"])
    version = db.get(Version, pub.current_wp)
    if not version:
        raise AppError("sin_borrador", "No hay artículo que adaptar.", 409)
    if "adapted" not in job.checkpoints:
        phase(db, job, owner, "Actualizando adaptación de LinkedIn", 40)
        old = db.get(Version, pub.current_li) if pub.current_li else None
        data = ai.call(
            db,
            job,
            owner,
            "adaptacion_linkedin",
            "Escribe una adaptación con valor propio para LinkedIn. Máximo 2.650 caracteres, reserva espacio al enlace. La edición anterior es referencia: respeta sus decisiones salvo instrucciones explícitas. "
            + job.parameters.get("instructions", ""),
            {
                "article": version.data,
                "previous": old.data if old else {},
                "owner": job.context_snapshot,
            },
            LinkedInText,
        )
        v = save_version(
            db,
            pub,
            "linkedin",
            data,
            "actualizacion_ia",
            job.context_snapshot,
            version.id,
        )
        job.checkpoints = {**job.checkpoints, "managed_revision": pub.revision}
        checkpoint(db, job, "adapted", v.id)
    return {"publication_id": pub.id, "version": job.checkpoints["adapted"]}


def import_remote(db, pub, post, wp, job):
    seo = {}
    try:
        seo = wp.seo(post["id"])
    except AppError:
        pass  # Historic import remains useful without the optional installed connector.

    def raw(key):
        return post.get(key, {}).get("raw", post.get(key, {}).get("rendered", ""))

    data = Article(
        title=text(raw("title")),
        body=raw("content"),
        excerpt=text(raw("excerpt")),
        slug=post.get("slug", ""),
        categories=post.get("categories", []),
        tags=post.get("tags", []),
        keyphrase=seo.get("keyphrase", ""),
        seo_title=seo.get("seo_title", ""),
        meta_description=seo.get("meta_description", ""),
    ).model_dump()
    version = save_version(
        db, pub, "wordpress", data, "importacion_wordpress", job.context_snapshot
    )
    set_remote(pub, post)
    pub.external_change = False
    db.flush()
    return version


def import_task(db, job, owner):
    wp = WordPress(connection_data(db, "wordpress"))
    page = job.checkpoints.get("import_page", 1)
    imported = job.checkpoints.get("imported", 0)
    conflicts = list(job.checkpoints.get("conflicts", []))
    while page <= 1000:
        phase(
            db, job, owner, f"Importando WordPress, página {page}", min(90, 10 + page)
        )
        posts = wp.request(
            "GET",
            "wp/v2/posts",
            params={
                "context": "edit",
                "status": "publish,draft,pending,future,private",
                "per_page": 100,
                "page": page,
            },
        )
        for post in posts:
            pub = db.scalar(select(Publication).where(Publication.wp_id == post["id"]))
            if pub and pub.remote_fingerprint != remote_hash(post):
                pub.external_change, pub.li_stale = True, True
                conflicts.append(pub.id)
                # Keep local edits; conflict import is an explicit separate action.
                set_remote(pub, post)
            elif not pub:
                pub = Publication(
                    title=text(post["title"]["rendered"]), wp_id=post["id"]
                )
                db.add(pub)
                db.flush()
                import_remote(db, pub, post, wp, job)
                imported += 1
            else:
                set_remote(pub, post)
            if post["status"] == "publish" and pub.idea_id:
                db.get(Idea, pub.idea_id).status = "utilizada"
        job.checkpoints = {
            **job.checkpoints,
            "import_page": page + 1,
            "imported": imported,
            "conflicts": list(set(conflicts)),
        }
        db.commit()
        if len(posts) < 100:
            break
        page += 1
    if "taxonomy" not in job.checkpoints:
        row = db.get(Configuration, "taxonomy") or Configuration(key="taxonomy")
        row.value = {
            "categories": wp.taxonomy("categories"),
            "tags": wp.taxonomy("tags"),
        }
        db.add(row)
        checkpoint(db, job, "taxonomy", True)
    return {"imported": imported, "conflicts": list(set(conflicts))}


def run_task(db, job, owner):
    if job.kind == "ideas":
        return ideas_task(db, job, owner)
    if job.kind == "generate_publication":
        return publication_task(db, job, owner)
    if job.kind == "correct":
        return correction_task(db, job, owner)
    if job.kind == "adapt_linkedin":
        return linkedin_task(db, job, owner)
    if job.kind == "sync_blog":
        return import_task(db, job, owner)
    if job.kind == "metrics":
        phase(db, job, owner, "Consultando estadísticas oficiales", 20)
        results = dict(job.checkpoints.get("metrics", {}))
        errors = {}
        for provider in ("ga4", "search_console"):
            if provider in results:
                continue
            assert_active(db, job, owner)
            try:
                results[provider] = sync_metrics(
                    db, provider, job.parameters["start"], job.parameters["end"]
                )
                checkpoint(db, job, "metrics", results)
            except AppError as exc:
                errors[provider] = exc.public()
        return {"metrics": results, "errors": errors, "partial": bool(errors)}
    pub = db.get(Publication, job.parameters["publication_id"])
    phase(db, job, owner, "Comprobando estado de plataforma", 25)
    if job.kind == "wp_send":
        return send_wordpress(db, pub, job)
    if job.kind == "li_publish":
        return send_linkedin(db, pub, job)
    if job.kind == "wp_check":
        check_wordpress(db, pub)
        return {
            "publication_id": pub.id,
            "wp_status": pub.wp_status,
            "public_verified": pub.public_verified,
            "external_change": pub.external_change,
        }
    if job.kind == "wp_import_version":
        wp = WordPress(connection_data(db, "wordpress"))
        post = wp.post(pub.wp_id)
        version = import_remote(db, pub, post, wp, job)
        db.commit()
        return {"publication_id": pub.id, "version": version.id}
    raise AppError("tipo_trabajo", "Tipo de trabajo no implementado.")
