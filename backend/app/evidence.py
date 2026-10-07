from urllib.parse import urlsplit, urlunsplit
from bs4 import BeautifulSoup


def normalize_url(url):
    try:
        u = urlsplit(url)
        if (
            u.scheme not in ("http", "https")
            or not u.hostname
            or u.username
            or u.password
        ):
            return None
        return urlunsplit((u.scheme, u.netloc.lower(), u.path.rstrip("/"), u.query, ""))
    except ValueError:
        return None


def restrict_generated_links(article, allowed_urls):
    """Retain only links with recorded provenance; imported/manual edits stay editable."""
    allowed = {normalize_url(url) for url in allowed_urls} - {None}
    soup = BeautifulSoup(article["body"], "html.parser")
    warnings = []
    for node in soup.find_all("a", href=True):
        href = node["href"]
        if normalize_url(href) not in allowed:
            warnings.append(
                f"Enlace propuesto sin fuente guardada, retirado del cuerpo: {href[:500]}"
            )
            node.unwrap()
    return {**article, "body": str(soup)}, warnings
