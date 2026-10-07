import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from .content import fingerprint, normalized, text

RULE_VERSION = "studio-seo-es-1.0.0"


def evaluate(
    article: dict, site_url: str = "", image: bool = False, used_keyphrases=()
):
    body = article.get("body", "")
    soup = BeautifulSoup(body, "html.parser")
    plain = text(body)
    words = re.findall(r"\w+", plain)
    phrase = normalized(article.get("keyphrase", "").strip())
    checks = []

    def add(key, label, weight, passed, advice, applicable=True):
        checks.append(
            {
                "key": key,
                "label": label,
                "weight": weight,
                "passed": bool(passed),
                "applicable": applicable,
                "advice": "" if passed else advice,
            }
        )

    def contains(value):
        return bool(phrase) and phrase in normalized(value)

    title = article.get("seo_title", "")
    meta = article.get("meta_description", "")
    headings = " ".join(
        h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3", "h4"])
    )
    occurrences = normalized(plain).count(phrase) if phrase else 0
    density = occurrences * max(1, len(phrase.split())) * 100 / max(1, len(words))
    links = [urlparse(a.get("href", "")) for a in soup.find_all("a")]
    site = urlparse(site_url).hostname
    add(
        "keyphrase",
        "Frase clave definida",
        5,
        bool(phrase),
        "Define la intención con una frase clave.",
    )
    add(
        "title_phrase",
        "Frase clave en título SEO",
        12,
        contains(title),
        "Incluye la frase clave de forma natural en el título SEO.",
    )
    add(
        "title_length",
        "Longitud del título SEO",
        8,
        25 <= len(title) <= 65,
        "Ajusta el título SEO a aproximadamente 25–65 caracteres; el ancho final depende de la fuente.",
    )
    add(
        "slug",
        "Frase clave en slug",
        8,
        contains(article.get("slug", "").replace("-", " ")),
        "Usa un slug breve que represente la frase clave.",
    )
    add(
        "introduction",
        "Frase clave en introducción",
        10,
        contains(" ".join(words[:100])),
        "Explica el tema en las primeras 100 palabras.",
    )
    add(
        "meta_phrase",
        "Frase clave en metadescripción",
        8,
        contains(meta),
        "Incluye la frase clave en la metadescripción.",
    )
    add(
        "meta_length",
        "Longitud de metadescripción",
        8,
        110 <= len(meta) <= 160,
        "Escribe una metadescripción útil de aproximadamente 110–160 caracteres.",
    )
    add(
        "headings",
        "Encabezados informativos",
        10,
        contains(headings),
        "Organiza el artículo con encabezados y menciona el tema donde encaje.",
    )
    add(
        "density",
        "Uso de frase clave sin saturación",
        10,
        0.3 <= density <= 3,
        "Revisa el uso natural de la frase clave (rango orientativo 0,3–3 %).",
    )
    add(
        "length",
        "Contenido suficiente",
        8,
        len(words) >= 250,
        "Desarrolla el contenido si lo necesita; un texto corto puede ser una decisión editorial válida.",
    )
    add(
        "internal",
        "Enlace interno",
        7,
        any(link.hostname == site for link in links if site),
        "Añade un enlace interno real y relevante.",
        bool(site),
    )
    add(
        "external",
        "Fuente externa enlazada",
        6,
        any(
            link.scheme in ("http", "https") and link.hostname != site for link in links
        ),
        "Enlaza una fuente original verificada.",
    )
    add(
        "image_alt",
        "Texto alternativo de imagen",
        4,
        bool(article.get("image_alt", "").strip()),
        "Describe la imagen manual con alt.",
        image,
    )
    total = sum(c["weight"] for c in checks if c["applicable"])
    score = round(
        100
        * sum(c["weight"] for c in checks if c["applicable"] and c["passed"])
        / max(1, total)
    )
    sentences = [s for s in re.split(r"[.!?]+", plain) if s.strip()]
    long_sentences = sum(len(s.split()) > 25 for s in sentences)
    warnings = []
    if phrase and phrase in {normalized(k) for k in used_keyphrases}:
        warnings.append(
            "La frase clave se ha utilizado en otra publicación. Revisa intención y enfoque."
        )
    return {
        "evaluator": RULE_VERSION,
        "fingerprint": fingerprint(article),
        "score": score,
        "checks": checks,
        "textual_score": score,
        "coverage": round(100 * sum(c["applicable"] for c in checks) / len(checks)),
        "density": round(density, 2),
        "words": len(words),
        "warnings": warnings,
        "readability": {
            "long_sentence_percent": round(
                100 * long_sentences / max(1, len(sentences))
            ),
            "paragraphs": len(soup.find_all("p")),
            "method": "Indicadores orientativos separados del SEO.",
        },
        "pending_site_checks": [
            "Representación final y ancho de snippets en WordPress",
            "Accesibilidad de enlaces en el sitio",
        ]
        + ([] if image else ["Imagen manual y alt pendientes"]),
    }


def stop_cycle(scores):
    if scores[-1] >= 70:
        return "umbral"
    if len(scores) >= 6:
        return "maximo_mejoras"
    if (
        len(scores) >= 3
        and scores[-1] <= max(scores[:-1])
        and scores[-2] <= max(scores[:-2])
    ):
        return "sin_mejora"
    return None
