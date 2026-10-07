import ipaddress
import socket
from urllib.parse import urlsplit, urljoin
import httpx
from .errors import AppError, provider_error
from .config import settings


def public_destination(url):
    try:
        u = urlsplit(url)
        if (
            u.scheme not in ("https", "http")
            or not u.hostname
            or u.username
            or u.password
            or u.port not in (None, 80, 443)
        ):
            raise ValueError()
        addresses = {
            x[4][0]
            for x in socket.getaddrinfo(
                u.hostname,
                u.port or (443 if u.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
        if not addresses or any(
            not ipaddress.ip_address(a).is_global for a in addresses
        ):
            raise ValueError()
        # Prefer IPv4 when both are available; many private servers have no IPv6 route.
        return u, sorted(
            addresses,
            key=lambda address: (ipaddress.ip_address(address).version, address),
        )[0]
    except (ValueError, OSError):
        raise AppError(
            "url_no_permitida", "La URL no apunta a un destino público permitido.", 400
        )


def public_get(url, max_bytes=2_000_000):
    """Pin a validated public DNS address, retain TLS SNI, and validate every redirect."""
    with httpx.Client(timeout=15, trust_env=False, follow_redirects=False) as client:
        for _ in range(6):
            u, ip = public_destination(url)
            host = f"[{ip}]" if ":" in ip else ip
            pinned = f"{u.scheme}://{host}{u.path or '/'}" + (
                f"?{u.query}" if u.query else ""
            )
            with client.stream(
                "GET",
                pinned,
                headers={"Host": u.hostname, "User-Agent": "GermanContentStudio/1.0"},
                extensions={"sni_hostname": u.hostname},
            ) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        raise AppError(
                            "pagina_demasiado_grande",
                            "La página supera el límite de lectura.",
                        )
                headers = dict(response.headers)
                headers.pop(
                    "content-encoding", None
                )  # iter_bytes already decompressed the body.
                headers.pop("content-length", None)
                return httpx.Response(
                    response.status_code,
                    headers=headers,
                    content=bytes(content),
                    request=httpx.Request("GET", url),
                )
    raise AppError("redirecciones", "La página tiene demasiadas redirecciones.")


def request_json(method, url, **kwargs):
    with httpx.Client(
        timeout=settings.request_timeout, follow_redirects=False, trust_env=False
    ) as client:
        response = client.request(method, url, **kwargs)
    try:
        data = response.json() if response.content else {}
    except ValueError:
        raise AppError(
            "respuesta_remota", "El servicio devolvió una respuesta no válida.", 502
        )
    if not response.is_success:
        error = provider_error(
            response.status_code, data if isinstance(data, dict) else {}
        )
        retry = response.headers.get("retry-after", "")
        if retry.isdigit():
            error.retry_after = int(retry)
        else:
            try:
                from email.utils import parsedate_to_datetime
                from .db import now

                error.retry_after = max(
                    0, int((parsedate_to_datetime(retry) - now()).total_seconds())
                )
            except (TypeError, ValueError):
                pass
        raise error
    return data, response
