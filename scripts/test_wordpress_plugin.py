"""Exercise the real connector and Yoast on a disposable loopback-only WordPress."""

import concurrent.futures
import base64
import json
import subprocess
import time
import uuid
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]
local = root / ".local"
local.mkdir(exist_ok=True)
compose = ["docker", "compose", "-f", str(root / "scripts" / "wordpress-sandbox.yaml")]


def run(args, **kwargs):
    return subprocess.run(
        args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs
    )


run(compose + ["up", "-d"])
for _ in range(100):
    try:
        if httpx.get("http://127.0.0.1:18081/", timeout=2).status_code < 500:
            break
    except httpx.HTTPError:
        pass
    time.sleep(0.5)
plugin = local / "wordpress-seo.zip"
with httpx.Client(timeout=90, follow_redirects=True) as client:
    response = client.get(
        "https://downloads.wordpress.org/plugin/wordpress-seo.28.6.zip"
    )
    response.raise_for_status()
    plugin.write_bytes(response.content)
run(compose + ["cp", str(plugin), "wordpress:/tmp/yoast.zip"])
run(
    compose
    + [
        "exec",
        "-T",
        "wordpress",
        "php",
        "-r",
        "$z=new ZipArchive(); $z->open('/tmp/yoast.zip'); $z->extractTo('/var/www/html/wp-content/plugins');",
    ]
)
run(
    compose
    + ["cp", str(root / "scripts" / "wp_sandbox_setup.php"), "wordpress:/tmp/setup.php"]
)
run(compose + ["exec", "-T", "wordpress", "php", "/tmp/setup.php"])
password = (
    run(compose + ["exec", "-T", "wordpress", "cat", "/tmp/test-app-password"])
    .stdout.decode()
    .strip()
)
base = "http://127.0.0.1:18081/wp-json"
auth = ("test-admin", password)
with httpx.Client(timeout=60, auth=auth) as client:
    health = client.get(base + "/german-studio/v1/health")
    assert health.status_code == 200, health.text
    assert health.json()["yoast_version"] == "28.6"
    forbidden = httpx.get(base + "/german-studio/v1/health")
    assert forbidden.status_code == 401
    key = str(uuid.uuid4())
    data = {
        "key": key,
        "title": "Borrador de pruebas, no publicar",
        "content": "<!-- wp:paragraph -->\n<p>Contenido de prueba con edición nativa.</p>\n<!-- /wp:paragraph -->",
        "slug": "prueba-" + key[:8],
        "excerpt": "Extracto de pruebas",
        "categories": [],
        "tags": [],
    }

    def send(_):
        return client.post(base + "/german-studio/v1/drafts", json=data)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, [1, 2]))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    ids = [r.json()["post_id"] for r in results]
    assert ids[0] == ids[1]
    id = ids[0]
    correlation = client.get(base + "/german-studio/v1/drafts", params={"key": key})
    assert correlation.json()["post_id"] == id
    read = client.get(base + f"/wp/v2/posts/{id}", params={"context": "edit"}).json()
    assert read["status"] == "draft"
    seo = {
        "keyphrase": "borrador de pruebas",
        "seo_title": "Borrador de pruebas: artículo editorial privado",
        "meta_description": "Este contenido permite comprobar que el conector guarda los metadatos SEO de un borrador de forma autenticada y autorizada.",
    }
    result = client.post(base + f"/german-studio/v1/posts/{id}/seo", json=seo)
    assert result.status_code == 200, result.text
    assert client.get(base + f"/german-studio/v1/posts/{id}/seo").json() == seo
    bad = client.post(
        base + f"/german-studio/v1/posts/{id}/seo",
        json={**seo, "arbitrary_meta": "should-fail"},
    )
    assert bad.status_code == 400
    # Simulate an external edit. Only the disposable WordPress is ever modified.
    client.post(
        base + f"/wp/v2/posts/{id}",
        json={"content": "<p>Edición externa conservada.</p>"},
    ).raise_for_status()
    conflict = client.post(
        base + "/german-studio/v1/drafts",
        json={**data, "post_id": id, "expected_hash": "2000-01-01T00:00:00"},
    )
    assert conflict.status_code == 409
    # Serialization roundtrip through WordPress's actual block parser.
    encoded = base64.b64encode(data["content"].encode()).decode()
    code = (
        "require '/var/www/html/wp-load.php'; $b=parse_blocks(base64_decode('"
        + encoded
        + "')); if($b[0]['blockName']!=='core/paragraph'){exit(1);} echo serialize_blocks($b);"
    )
    native = run(
        compose + ["exec", "-T", "wordpress", "php", "-r", code]
    ).stdout.decode()
    assert native == data["content"]
report = {
    "passed": True,
    "wordpress": run(
        compose
        + [
            "exec",
            "-T",
            "wordpress",
            "php",
            "-r",
            "include '/var/www/html/wp-includes/version.php'; echo $wp_version;",
        ]
    )
    .stdout.decode()
    .strip(),
    "yoast": "28.6",
    "checks": [
        "Authentication",
        "Concurrent draft correlation",
        "Readback",
        "SEO allowlist and persistence",
        "External edit conflict",
        "Native core/paragraph parse/serialize",
    ],
    "scope": "Disposable loopback WordPress; no changes to germanmallo.com.",
}
(root / "docs" / "wordpress-test-report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(
    "Conector WordPress real verificado: autenticación, doble creación, SEO persistido, conflictos y bloques nativos."
)
