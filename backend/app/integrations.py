import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlparse
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from sqlalchemy import select
from .network import request_json, public_get
from .security import connection_data
from .errors import AppError
from .config import settings
from .content import text, fingerprint, blocks
from .models import Publication, Version, Idea, File, Metric
from .db import now


class WordPress:
    def __init__(self, config):
        self.base = config.get("url", "").rstrip("/")
        u = urlsplit(self.base)
        if (
            u.scheme != "https"
            or not u.hostname
            or u.username
            or u.password
            or u.query
            or u.fragment
        ):
            raise AppError("wordpress_url", "Configura la URL HTTPS de WordPress.")
        self.auth = (config.get("username", ""), config.get("application_password", ""))

    def request(self, method, path, **kwargs):
        return request_json(
            method, self.base + "/wp-json/" + path.lstrip("/"), auth=self.auth, **kwargs
        )[0]

    def post(self, post_id):
        return self.request("GET", f"wp/v2/posts/{post_id}", params={"context": "edit"})

    def taxonomy(self, kind):
        rows = []
        page = 1
        while page <= 100:
            result = self.request(
                "GET", f"wp/v2/{kind}", params={"per_page": 100, "page": page}
            )
            rows.extend(result)
            if len(result) < 100:
                break
            page += 1
        return rows

    def seo(self, post_id):
        return self.request("GET", f"german-studio/v1/posts/{post_id}/seo")

    def upsert_draft(self, key, content, post_id=None, expected_hash=""):
        return self.request(
            "POST",
            "german-studio/v1/drafts",
            json={
                "key": key,
                "post_id": post_id,
                "expected_hash": expected_hash,
                **content,
            },
        )

    def correlation(self, key):
        return self.request("GET", "german-studio/v1/drafts", params={"key": key})


def remote_hash(post):
    return fingerprint(
        {
            k: post.get(k)
            for k in (
                "title",
                "content",
                "excerpt",
                "slug",
                "featured_media",
                "categories",
                "tags",
            )
        }
    )


def set_remote(pub, post):
    from datetime import datetime, timezone

    url = post.get("link", "")
    history = list(pub.url_history or [])
    if pub.canonical_url and pub.canonical_url not in history:
        history.append(pub.canonical_url)
    if url and url not in history:
        history.append(url)
    pub.url_history, pub.canonical_url = history, url
    pub.wp_id, pub.wp_status = post["id"], post["status"]
    pub.remote_modified, pub.remote_fingerprint = (
        post.get("modified_gmt", ""),
        remote_hash(post),
    )
    pub.synced_at = now()
    if post.get("status") == "publish" and post.get("date_gmt"):
        try:
            pub.published_at = datetime.fromisoformat(post["date_gmt"]).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass


def check_public(post):
    if post.get("status") != "publish" or post.get("password"):
        raise AppError(
            "articulo_no_publico",
            "WordPress debe estar publicado y sin contraseña.",
            409,
            "Publica el artículo desde WordPress y vuelve a comprobar.",
        )
    url = post.get("link", "")
    try:
        response = public_get(url)
    except httpx_errors():
        raise AppError(
            "articulo_inaccesible",
            "La URL definitiva no es accesible públicamente.",
            409,
        )
    if response.status_code != 200 or "text/html" not in response.headers.get(
        "content-type", ""
    ):
        raise AppError(
            "articulo_inaccesible",
            "La URL definitiva no devuelve el artículo público.",
            409,
        )
    soup = BeautifulSoup(response.text, "html.parser")
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href", "").rstrip("/") != url.rstrip("/"):
        raise AppError(
            "url_otro_contenido", "La página pública declara otra URL canónica.", 409
        )
    if urlparse(str(response.url)).path.rstrip("/") != urlparse(url).path.rstrip("/"):
        raise AppError("url_otro_contenido", "La URL redirige a otro contenido.", 409)
    raw_body = post.get("content", {}).get("raw") or post.get("content", {}).get(
        "rendered", ""
    )
    expected = text(raw_body)
    actual = soup.get_text(" ", strip=True)
    sample = " ".join(expected.split()[:20])
    if (
        not sample
        or sample.casefold() not in " ".join(actual.split()).casefold()
        or soup.select("form#loginform, form.post-password-form")
    ):
        raise AppError(
            "contenido_publico_no_verificado",
            "No se ha podido verificar el texto del artículo en la página pública.",
            409,
            "Comprueba la URL y el tema WordPress; no publiques LinkedIn hasta verificarlo.",
        )
    return url


def httpx_errors():
    import httpx

    return (httpx.HTTPError,)


def check_wordpress(db, pub):
    if not pub.wp_id:
        raise AppError(
            "sin_articulo_remoto", "Envía primero el borrador a WordPress.", 409
        )
    wp = WordPress(connection_data(db, "wordpress"))
    post = wp.post(pub.wp_id)
    changed = bool(
        pub.remote_fingerprint and pub.remote_fingerprint != remote_hash(post)
    )
    pub.external_change = pub.external_change or changed
    if changed:
        pub.li_stale = True
    set_remote(pub, post)
    pub.public_verified = False
    try:
        check_public(post)
        pub.public_verified = True
    except AppError:
        pass
    if post["status"] == "publish" and pub.idea_id:
        idea = db.get(Idea, pub.idea_id)
        idea.status = "utilizada"
        idea.revision += 1
    db.commit()
    return post


def send_wordpress(db, pub, job):
    wp = WordPress(connection_data(db, "wordpress"))
    version = db.get(Version, pub.current_wp)
    if not version:
        raise AppError(
            "sin_borrador", "Genera o guarda el artículo antes de enviarlo.", 409
        )
    data = version.data
    if pub.wp_id:
        remote = wp.post(pub.wp_id)
        if remote["status"] not in ("draft", "pending"):
            raise AppError(
                "wordpress_no_borrador",
                "El artículo remoto ya no es un borrador editable.",
                409,
            )
        if (
            pub.external_change
            or (
                pub.remote_fingerprint and pub.remote_fingerprint != remote_hash(remote)
            )
            or (
                pub.remote_modified
                and pub.remote_modified != remote.get("modified_gmt", "")
            )
        ):
            pub.external_change = True
            db.commit()
            raise AppError(
                "cambios_externos",
                "Hay cambios externos en WordPress.",
                409,
                "Importa la versión remota o resuelve el conflicto antes de enviar.",
            )
    else:
        found = wp.correlation(pub.id)
        if found.get("post_id"):
            pub.wp_id = found["post_id"]
            remote = wp.post(pub.wp_id)
            set_remote(pub, remote)
            db.commit()
    content = {
        "title": data["title"],
        "content": blocks(data["body"]),
        "excerpt": data.get("excerpt", ""),
        "slug": data.get("slug", ""),
        "categories": data.get("categories", []),
        "tags": data.get("tags", []),
    }
    pub.confirmations = {"content": False, "seo": False, "image": not bool(pub.file_id)}
    pub.wp_status = "enviando"
    db.commit()
    try:
        result = wp.upsert_draft(pub.id, content, pub.wp_id, pub.remote_modified)
    except httpx_errors():
        pub.wp_status = "incierto"
        db.commit()
        raise AppError(
            "wordpress_incierto",
            "Se perdió la respuesta de WordPress.",
            409,
            "Reintenta el envío: el conector reconciliará la clave de creación.",
        )
    pub.wp_id = result["post_id"]
    pub.sent_wp = version.id
    db.commit()
    remote = wp.post(pub.wp_id)
    if text(
        remote.get("title", {}).get("raw", remote.get("title", {}).get("rendered", ""))
    ) != text(data["title"]) or clean_remote_body(remote) != text(data["body"]):
        pub.wp_status = "parcial"
        db.commit()
        raise AppError(
            "wordpress_contenido_parcial",
            "WordPress creó el artículo, pero el contenido leído no coincide.",
            409,
        )
    pub.confirmations = {**pub.confirmations, "content": True}
    set_remote(pub, remote)
    db.commit()
    try:
        wp.request(
            "POST",
            f"german-studio/v1/posts/{pub.wp_id}/seo",
            json={
                k: data.get(k, "")
                for k in ("keyphrase", "seo_title", "meta_description")
            },
        )
        confirmed = wp.seo(pub.wp_id)
        if any(
            confirmed.get(k) != data.get(k, "")
            for k in ("keyphrase", "seo_title", "meta_description")
        ):
            raise AppError(
                "seo_no_persistido",
                "La lectura posterior no confirma todos los campos SEO.",
                409,
            )
        pub.confirmations = {**pub.confirmations, "seo": True}
        db.commit()
        if pub.file_id:
            file = db.get(File, pub.file_id)
            if file.upload_uncertain and not file.wp_id:
                raise AppError(
                    "imagen_incierta",
                    "La subida anterior de la imagen tiene resultado incierto.",
                    409,
                    "Consulta Medios en WordPress y registra el ID en Ajustes de la imagen.",
                )
            if not file.wp_id:
                file.upload_uncertain = True
                db.commit()
                try:
                    raw = Path(file.path).read_bytes()
                    media = wp.request(
                        "POST",
                        "wp/v2/media",
                        content=raw,
                        headers={
                            "Content-Type": file.mime,
                            "Content-Disposition": f'attachment; filename="{Path(file.path).name}"',
                        },
                    )
                    file.wp_id = media["id"]
                    file.upload_uncertain = False
                    db.commit()
                except AppError:
                    file.upload_uncertain = False
                    db.commit()
                    raise
            wp.request("POST", f"wp/v2/media/{file.wp_id}", json={"alt_text": file.alt})
            media = wp.request(
                "GET", f"wp/v2/media/{file.wp_id}", params={"context": "edit"}
            )
            if media.get("alt_text") != file.alt:
                raise AppError(
                    "alt_no_persistido",
                    "No se pudo confirmar el texto alternativo.",
                    409,
                )
            wp.request(
                "POST", f"wp/v2/posts/{pub.wp_id}", json={"featured_media": file.wp_id}
            )
            remote = wp.post(pub.wp_id)
            if remote.get("featured_media") != file.wp_id:
                raise AppError(
                    "imagen_no_persistida",
                    "No se pudo confirmar la imagen destacada.",
                    409,
                )
            pub.confirmations = {**pub.confirmations, "image": True}
    except (AppError, *httpx_errors()):
        pub.wp_status = "parcial"
        db.commit()
        raise
    set_remote(pub, wp.post(pub.wp_id))
    pub.external_change = False
    db.commit()
    return {
        "publication_id": pub.id,
        "wp_id": pub.wp_id,
        "confirmations": pub.confirmations,
    }


def clean_remote_body(remote):
    return text(
        remote.get("content", {}).get(
            "raw", remote.get("content", {}).get("rendered", "")
        )
    )


def linkedin_text(value, url, history):
    for old in sorted(set(history + [url]), key=len, reverse=True):
        if old:
            value = value.replace(old, "")
    value = value.strip() + "\n\n" + url
    if len(value) > 3000:
        raise AppError(
            "linkedin_longitud",
            "El texto con enlace supera 3.000 caracteres.",
            409,
            "Acorta la adaptación antes de publicar.",
        )
    return value


def send_linkedin(db, pub, job):
    if pub.li_status in ("publicado", "incierto", "enviando"):
        raise AppError(
            "linkedin_ya_enviado",
            "LinkedIn ya está publicado o tiene un envío incierto.",
            409,
            "Comprueba el perfil antes de reconciliar.",
        )
    post = check_wordpress(db, pub)
    url = check_public(post)
    if pub.li_stale:
        raise AppError(
            "linkedin_desactualizado",
            "La adaptación necesita revisión tras cambios del artículo.",
            409,
            "Revisa y guarda la adaptación o regénérala.",
        )
    v = db.get(Version, pub.current_li)
    if not v:
        raise AppError(
            "linkedin_sin_texto", "Guarda primero una adaptación de LinkedIn.", 409
        )
    config = connection_data(db, "linkedin")
    if not config.get("person_id"):
        raise AppError(
            "linkedin_perfil", "Falta el identificador del perfil OAuth.", 409
        )
    commentary = linkedin_text(v.data["text"], url, pub.url_history)
    pub.li_status, pub.sent_li = "enviando", v.id
    db.commit()
    try:
        _, response = request_json(
            "POST",
            "https://api.linkedin.com/rest/posts",
            headers={
                "Authorization": f"Bearer {config.get('access_token', '')}",
                "LinkedIn-Version": settings.linkedin_version,
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json={
                "author": "urn:li:person:" + config["person_id"],
                "commentary": commentary,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
        )
    except AppError as exc:
        pub.li_status = "incierto" if exc.status >= 500 else "local"
        db.commit()
        if pub.li_status == "incierto":
            raise AppError(
                "linkedin_incierto",
                "LinkedIn devolvió un error después del envío; el resultado es incierto.",
                409,
                "Comprueba tu perfil y reconcilia el post. No se repetirá la creación automáticamente.",
            )
        raise
    except httpx_errors():
        pub.li_status = "incierto"
        db.commit()
        raise AppError(
            "linkedin_incierto",
            "La respuesta se perdió; el post puede haberse publicado.",
            409,
            "Comprueba el perfil y registra el ID remoto; no se repetirá automáticamente.",
        )
    pub.li_id = response.headers.get("x-restli-id")
    pub.li_status = "publicado" if pub.li_id else "incierto"
    db.commit()
    return {"publication_id": pub.id, "li_id": pub.li_id, "status": pub.li_status}


def google_token(config, scopes):
    info = config.get("service_account")
    if isinstance(info, str):
        info = json.loads(info)
    if not isinstance(info, dict):
        raise AppError(
            "google_credenciales",
            "Configura el JSON de una cuenta de servicio con permisos de lectura.",
            409,
        )
    # Never follow untrusted credential token endpoints.
    if info.get("token_uri") != "https://oauth2.googleapis.com/token":
        raise AppError(
            "google_token_uri", "El endpoint del JSON de Google no está permitido."
        )
    creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
    creds.refresh(Request())
    return creds.token


def ga4_report(config, start, end):
    prop = config.get("property_id", "")
    if not str(prop).isdigit():
        raise AppError("ga4_propiedad", "Usa el ID numérico de la propiedad GA4.")
    token = google_token(config, ["https://www.googleapis.com/auth/analytics.readonly"])
    offset, rows, metadata = 0, [], {}
    while True:
        data, _ = request_json(
            "POST",
            f"https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport",
            headers={"Authorization": "Bearer " + token},
            json={
                "dateRanges": [{"startDate": start, "endDate": end}],
                "dimensions": [{"name": "pagePath"}, {"name": "sessionSourceMedium"}],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "screenPageViews"},
                    {"name": "engagedSessions"},
                    {"name": "eventCount"},
                ],
                "limit": 10000,
                "offset": offset,
            },
        )
        rows.extend(data.get("rows", []))
        metadata = data.get("metadata", {})
        offset += len(data.get("rows", []))
        if (
            offset >= data.get("rowCount", 0)
            or not data.get("rows")
            or offset >= 100000
        ):
            return rows, metadata, offset < data.get("rowCount", 0)


def search_console_report(config, start, end):
    from urllib.parse import quote

    prop = config.get("site_url", "")
    if not prop:
        raise AppError("gsc_propiedad", "Configura la propiedad Search Console.")
    token = google_token(
        config, ["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    rows, offset = [], 0
    while offset < 100000:
        data, _ = request_json(
            "POST",
            "https://www.googleapis.com/webmasters/v3/sites/"
            + quote(prop, safe="")
            + "/searchAnalytics/query",
            headers={"Authorization": "Bearer " + token},
            json={
                "startDate": start,
                "endDate": end,
                "dimensions": ["page", "query"],
                "rowLimit": 25000,
                "startRow": offset,
                "dataState": "final",
            },
        )
        batch = data.get("rows", [])
        rows.extend(batch)
        if len(batch) < 25000:
            break
        offset += 25000
    return rows


def sync_metrics(db, provider, start, end):
    if date.fromisoformat(start) > date.fromisoformat(end):
        raise AppError("periodo", "La fecha inicial debe ser anterior a la final.")
    conf = connection_data(db, provider)
    pubs = db.scalars(select(Publication).where(Publication.wp_id.is_not(None))).all()
    mapping = {}
    for pub in pubs:
        for url in set(pub.url_history + [pub.canonical_url]):
            mapping[urlparse(url).path.rstrip("/")] = pub.id
    if provider == "ga4":
        rows, metadata, partial = ga4_report(conf, start, end)
        quality = (
            "parcial"
            if partial
            or metadata.get("subjectToThresholding")
            or metadata.get("samplingMetadatas")
            else "disponible"
        )
        transformed = [
            {
                "dimensions": {
                    "page": r["dimensionValues"][0]["value"],
                    "source_medium": r["dimensionValues"][1]["value"],
                },
                "values": dict(
                    zip(
                        ["sessions", "views", "engaged_sessions", "events"],
                        [float(v["value"]) for v in r["metricValues"]],
                    )
                ),
            }
            for r in rows
        ]
    else:
        rows = search_console_report(conf, start, end)
        quality = "parcial"  # Search Analytics returns top rows, never promises complete query history.
        transformed = [
            {
                "dimensions": {"page": r["keys"][0], "query": r["keys"][1]},
                "values": {
                    k: r[k] for k in ("clicks", "impressions", "ctr", "position")
                },
            }
            for r in rows
        ]
    for row in transformed:
        pub_id = mapping.get(urlparse(row["dimensions"]["page"]).path.rstrip("/"))
        existing = db.scalar(
            select(Metric).where(
                Metric.provider == provider,
                Metric.period_start == start,
                Metric.period_end == end,
                Metric.publication_id == pub_id,
                Metric.dimensions == row["dimensions"],
            )
        )
        if existing:
            existing.values, existing.quality, existing.updated_at = (
                row["values"],
                quality,
                now(),
            )
        else:
            db.add(
                Metric(
                    provider=provider,
                    period_start=start,
                    period_end=end,
                    publication_id=pub_id,
                    dimensions=row["dimensions"],
                    values=row["values"],
                    quality=quality,
                )
            )
    if not rows:
        dim = {"report": "empty"}
        existing = db.scalar(
            select(Metric).where(
                Metric.provider == provider,
                Metric.period_start == start,
                Metric.period_end == end,
                Metric.dimensions == dim,
            )
        )
        if not existing:
            db.add(
                Metric(
                    provider=provider,
                    period_start=start,
                    period_end=end,
                    dimensions=dim,
                    values={},
                    quality="sin_datos",
                )
            )
    db.commit()
    return {
        "provider": provider,
        "rows": len(rows),
        "quality": quality if rows else "sin_datos",
    }
