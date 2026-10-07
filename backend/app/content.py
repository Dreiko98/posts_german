import hashlib
import json
import re
import unicodedata
import bleach
from bs4 import BeautifulSoup

TAGS = [
    "p",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "a",
    "strong",
    "em",
    "blockquote",
    "pre",
    "code",
    "br",
    "figure",
    "img",
]


def fingerprint(data):
    return hashlib.sha256(
        json.dumps(
            data, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def clean_html(body):
    soup = BeautifulSoup(body, "html.parser")
    for node in soup(["script", "style", "iframe", "object"]):
        node.decompose()
    for node in soup.find_all("h1"):
        node.name = "h2"
    for comment in soup.find_all(
        string=lambda x: isinstance(x, __import__("bs4").Comment)
    ):
        comment.extract()
    cleaned = bleach.clean(
        str(soup),
        tags=TAGS,
        attributes={"a": ["href", "title"], "img": ["src", "alt"]},
        protocols=["https", "http"],
        strip=True,
    )
    return re.sub(r"\[(?:IMAGE|IMAGEN|TODO|INSERTAR)[^\]]*\]", "", cleaned, flags=re.I)


def text(body):
    return BeautifulSoup(body, "html.parser").get_text(" ", strip=True)


def normalized(value):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", value.casefold())
        if unicodedata.category(c) != "Mn"
    )


def terms(value):
    stop = {
        "para",
        "como",
        "sobre",
        "desde",
        "este",
        "esta",
        "esto",
        "una",
        "con",
        "que",
        "por",
        "los",
        "las",
        "del",
        "sin",
        "más",
    }
    return set(re.findall(r"\w{3,}", normalized(value))) - stop


def relevant(query, items, limit=25):
    q = terms(query)
    ranked = sorted(
        items,
        key=lambda x: (
            len(q & terms(json.dumps(x, ensure_ascii=False))) / max(1, len(q))
        ),
        reverse=True,
    )
    return ranked[:limit]


def blocks(body):
    """Serialize supported HTML as native core blocks; other safe HTML as core/html."""
    soup = BeautifulSoup(clean_html(body), "html.parser")
    result = []
    for node in soup.contents:
        name = getattr(node, "name", None)
        if not name:
            if str(node).strip():
                result.append(
                    f"<!-- wp:paragraph --><p>{bleach.clean(str(node))}</p><!-- /wp:paragraph -->"
                )
            continue
        if name == "p":
            kind, attrs = "paragraph", ""
        elif name in ("h2", "h3", "h4"):
            kind, attrs = "heading", " " + json.dumps({"level": int(name[1])})
            node["class"] = ["wp-block-heading"]
        else:
            kind, attrs = "html", ""
        result.append(f"<!-- wp:{kind}{attrs} -->\n{node}\n<!-- /wp:{kind} -->")
    return "\n\n".join(result)
