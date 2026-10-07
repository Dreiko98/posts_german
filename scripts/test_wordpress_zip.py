"""Install the delivered ZIP through WordPress's actual admin upload form.

Only touches a fresh loopback sandbox. Never uses production credentials.
"""

import json
import argparse
import subprocess
import time
import uuid
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup
from package_wordpress_plugin import build, ROOT, PLUGIN


def run(args, timeout=180):
    return subprocess.run(args, check=True, capture_output=True, timeout=timeout)


def main(flat=False):
    archive = build(flat)
    port = 18085 if flat else 18084
    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    project = "gstudio-zip-test-" + uuid.uuid4().hex[:8]
    configuration = local / f"{project}.json"
    configuration.write_text(
        json.dumps(
            {
                "services": {
                    "mysql": {
                        "image": "mariadb:11.4.10",
                        "environment": {
                            "MARIADB_DATABASE": "wordpress",
                            "MARIADB_USER": "wordpress",
                            "MARIADB_PASSWORD": "zip-test-only",
                            "MARIADB_ROOT_PASSWORD": "zip-root-test-only",
                        },
                        "healthcheck": {
                            "test": [
                                "CMD",
                                "healthcheck.sh",
                                "--connect",
                                "--innodb_initialized",
                            ],
                            "interval": "3s",
                            "retries": 30,
                        },
                    },
                    "wordpress": {
                        "image": "wordpress:6.9-php8.3-apache",
                        "environment": {
                            "WORDPRESS_DB_HOST": "mysql",
                            "WORDPRESS_DB_USER": "wordpress",
                            "WORDPRESS_DB_PASSWORD": "zip-test-only",
                            "WORDPRESS_DB_NAME": "wordpress",
                            "WORDPRESS_CONFIG_EXTRA": "define('WP_ENVIRONMENT_TYPE', 'local');",
                        },
                        "ports": [f"127.0.0.1:{port}:80"],
                        "depends_on": {"mysql": {"condition": "service_healthy"}},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    compose = ["docker", "compose", "-f", str(configuration), "-p", project]
    base = f"http://127.0.0.1:{port}"
    try:
        print("Arrancando sandbox ZIP aislado…", flush=True)
        run(compose + ["up", "-d"])
        for _ in range(100):
            try:
                if httpx.get(base, timeout=2).status_code < 500:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        setup = """define('WP_INSTALLING', true);
$_SERVER['HTTP_HOST']='127.0.0.1:18084'; $_SERVER['REQUEST_URI']='/'; $_SERVER['SERVER_PROTOCOL']='HTTP/1.1';
require '/var/www/html/wp-load.php'; require_once ABSPATH.'wp-admin/includes/upgrade.php';
wp_install('ZIP test only', 'zip-admin', 'zip@example.invalid', 0, '', 'zip-test-password-only');
update_option('siteurl','http://127.0.0.1:18084'); update_option('home','http://127.0.0.1:18084');
$user=get_user_by('login','zip-admin');
$password=WP_Application_Passwords::create_new_application_password($user->ID,array('name'=>'zip-test'));
file_put_contents('/tmp/zip-test-password',$password[0]);
"""
        run(
            compose
            + [
                "exec",
                "-T",
                "wordpress",
                "php",
                "-r",
                setup.replace("18084", str(port)),
            ]
        )
        print("Subiendo el ZIP desde el formulario real…", flush=True)
        with httpx.Client(follow_redirects=True, timeout=60) as client:
            client.get(base + "/wp-login.php")
            client.post(
                base + "/wp-login.php",
                data={
                    "log": "zip-admin",
                    "pwd": "zip-test-password-only",
                    "wp-submit": "Log In",
                    "redirect_to": base + "/wp-admin/",
                    "testcookie": "1",
                },
            )
            page = client.get(base + "/wp-admin/plugin-install.php?tab=upload")
            soup = BeautifulSoup(page.text, "html.parser")
            form = next(
                (
                    candidate
                    for candidate in soup.select("form")
                    if candidate.select_one('input[name="pluginzip"]')
                ),
                None,
            )
            if form is None:
                (local / "zip-test-upload-debug.html").write_text(
                    page.text, encoding="utf-8"
                )
            assert form, "Plugin upload form inaccessible in test sandbox."
            fields = {
                item["name"]: item.get("value", "")
                for item in form.select("input[name]")
                if item.get("type") != "file"
            }
            with archive.open("rb") as source:
                uploaded = client.post(
                    urljoin(base, form["action"]),
                    data=fields,
                    files={"pluginzip": (archive.name, source, "application/zip")},
                )
            soup = BeautifulSoup(uploaded.text, "html.parser")
            activation = next(
                (
                    a["href"]
                    for a in soup.select("a[href]")
                    if "action=activate" in a["href"]
                ),
                None,
            )
            assert activation, "WordPress did not offer activation after ZIP upload."
            plugin_path = parse_qs(urlparse(activation).query)["plugin"][0]
            expected_folder = archive.stem if flat else PLUGIN
            assert plugin_path == f"{expected_folder}/{PLUGIN}.php", plugin_path
            activated = client.get(urljoin(str(uploaded.url), activation))
            assert activated.status_code == 200
            password = (
                run(
                    compose
                    + ["exec", "-T", "wordpress", "cat", "/tmp/zip-test-password"]
                )
                .stdout.decode()
                .strip()
            )
            health = httpx.get(
                base + "/",
                params={"rest_route": "/german-studio/v1/health"},
                auth=("zip-admin", password),
            )
            assert health.status_code == 200, (
                f"Connector health status: {health.status_code}"
            )
        report = {
            "passed": True,
            "checks": [
                "Portable ZIP entries",
                "Native admin multipart upload",
                "Single-directory activation path",
                "Activation",
                "Authenticated connector health",
            ],
            "activation_path": plugin_path,
            "scope": "Fresh disposable loopback WordPress. No production changes.",
        }
        report_file = (
            "wordpress-flat-zip-test-report.json"
            if flat
            else "wordpress-zip-test-report.json"
        )
        (ROOT / "docs" / report_file).write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print("Instalación ZIP y activación verificadas.", flush=True)
    finally:
        run(compose + ["down", "--timeout", "5"], timeout=30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--flat", action="store_true")
    main(parser.parse_args().flat)
