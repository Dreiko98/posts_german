"""Real UI + FastAPI + PostgreSQL + worker, with provider doubles confined to tests."""

import json
import os
import secrets
import subprocess
import time
import urllib.request
from pathlib import Path
from cryptography.fernet import Fernet
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
out = root / "docs" / "screenshots"
out.mkdir(parents=True, exist_ok=True)
password = secrets.token_urlsafe(20)
env = {
    **os.environ,
    "DATABASE_URL": os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://studio:test-local-only@127.0.0.1:55432/studio_test",
    ),
    "MASTER_KEY": Fernet.generate_key().decode(),
    "APP_ORIGIN": "http://127.0.0.1:5173",
    "DATA_DIR": str(root / ".local" / "e2e-files"),
    "E2E_FIXTURE": "1",
    "E2E_PASSWORD": password,
}
backend_log = (
    open(root / ".local" / "e2e-backend.log", "w", encoding="utf-8")
    if (root / ".local").exists()
    else None
)
(root / ".local").mkdir(exist_ok=True)
if backend_log is None:
    backend_log = open(root / ".local" / "e2e-backend.log", "w", encoding="utf-8")
web_log = open(root / ".local" / "e2e-web.log", "w", encoding="utf-8")
server = subprocess.Popen(
    [
        str(root / ".venv" / "Scripts" / "python.exe")
        if os.name == "nt"
        else str(root / ".venv" / "bin" / "python"),
        "-m",
        "tests.e2e_server",
    ],
    cwd=root / "backend",
    env=env,
    stdout=backend_log,
    stderr=backend_log,
)
npm = "npm.cmd" if os.name == "nt" else "npm"
web = subprocess.Popen(
    [npm, "run", "dev"], cwd=root / "frontend", stdout=web_log, stderr=web_log
)


def ready(url):
    for _ in range(100):
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Test server did not start; see .local logs.")


def shot(page, name):
    if not name.startswith("error-"):
        dismiss = page.get_by_role("button", name="Cerrar aviso", exact=True)
        if dismiss.count():
            dismiss.click()
    page.evaluate(
        """() => { let el=document.getElementById('test-watermark'); if(!el){el=document.createElement('div');el.id='test-watermark';el.textContent='ENTORNO DE PRUEBAS · IA SIMULADA · NO PUBLICA CONTENIDO';Object.assign(el.style,{position:'fixed',bottom:'0',left:'0',right:'0',zIndex:'9999',background:'#213528',color:'#bde9cc',font:'9px Arial',padding:'5px',textAlign:'center'});document.body.appendChild(el)} }"""
    )
    page.screenshot(path=str(out / (name + ".png")), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
        name + " has horizontal overflow"
    )


try:
    ready("http://127.0.0.1:8000/api/health")
    ready("http://127.0.0.1:5173")
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto("http://127.0.0.1:5173")
        expect(page.get_by_role("heading", name="Entrar al estudio")).to_be_visible()
        shot(page, "login-desktop")
        page.set_viewport_size({"width": 390, "height": 844})
        shot(page, "login-mobile")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_label("Usuario", exact=True).fill("e2e")
        page.get_by_label("Contraseña", exact=True).fill(password)
        page.get_by_role("button", name="Entrar", exact=True).click()
        expect(page.get_by_role("heading", name="Ideas.", exact=True)).to_be_visible()
        shot(page, "ideas-empty-desktop")
        page.get_by_role(
            "button", name="Crear idea manualmente", exact=False
        ).first.click()
        page.get_by_label("¿Qué tienes en mente?").fill(
            "Quiero escribir sobre automatización útil"
        )
        page.get_by_role("button", name="Desarrollar mi idea").click()
        expect(page.locator(".idea-card")).to_have_count(1, timeout=30000)
        page.get_by_role("button", name="Seleccionar idea", exact=True).click()
        expect(page.locator(".idea-card .badge")).to_have_text("Seleccionada")
        page.get_by_role("button", name="Descartar idea", exact=True).click()
        page.get_by_label("Motivo").fill("Preferir un enfoque más concreto")
        page.get_by_role("dialog").get_by_role(
            "button", name="Descartar idea", exact=True
        ).click()
        expect(page.locator(".idea-card .badge")).to_have_text("Descartada")
        page.get_by_role("button", name="Recuperar idea").click()
        expect(page.locator(".idea-card .badge")).to_have_text("Pendiente")
        page.get_by_role("button", name="Generar con IA", exact=False).first.click()
        page.get_by_label("Cantidad de ideas").fill("3")
        page.get_by_role("button", name="Generar propuestas").click()
        expect(page.locator(".idea-card")).to_have_count(4, timeout=30000)
        shot(page, "ideas-desktop")
        page.set_viewport_size({"width": 390, "height": 844})
        shot(page, "ideas-mobile")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("button", name="Crear publicación", exact=False).first.click()
        page.get_by_role("dialog").get_by_role(
            "button", name="Preparar publicación", exact=True
        ).click()
        expect(page.get_by_label("Cuerpo del artículo")).not_to_have_value(
            "", timeout=30000
        )
        expect(page.get_by_role("button", name="Trabajos y progreso")).to_be_visible()
        expect(page.get_by_role("heading", name="Umbral SEO alcanzado")).to_be_visible(
            timeout=30000
        )
        shot(page, "editor-desktop")
        page.set_viewport_size({"width": 390, "height": 844})
        shot(page, "editor-mobile")
        page.set_viewport_size({"width": 1440, "height": 1000})
        original = page.get_by_label("Cuerpo del artículo").input_value()
        page.get_by_label("Cuerpo del artículo").fill(
            original + "<p>Una edición manual.</p>"
        )
        page.get_by_role("button", name="Guardar", exact=True).click()
        expect(page.get_by_role("heading", name="Evaluación pendiente")).to_be_visible()
        page.get_by_role("button", name="Reevaluar", exact=True).click()
        expect(page.get_by_role("heading", name="Umbral SEO alcanzado")).to_be_visible()
        page.get_by_role("button", name="LinkedIn Borrador local", exact=False).click()
        expect(
            page.get_by_role("button", name="Publicar en LinkedIn", exact=True)
        ).to_be_disabled()
        page.get_by_label("Texto LinkedIn").fill(
            "Mi adaptación editada, conservada como versión local."
        )
        page.get_by_role("button", name="Guardar", exact=True).click()
        page.get_by_role("button", name="Versiones", exact=False).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        expect(page.locator(".version-row")).to_have_count(4)
        page.get_by_role("button", name="Cerrar diálogo").click()
        page.get_by_role("button", name="Publicaciones", exact=True).first.click()
        expect(page.locator(".publication-row")).to_have_count(1)
        shot(page, "publications-desktop")
        page.set_viewport_size({"width": 390, "height": 844})
        shot(page, "publications-mobile")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("button", name="Ajustes", exact=True).click()
        expect(page.get_by_text("Un contenido que se parece a ti")).to_be_visible()
        shot(page, "settings-desktop")
        page.set_viewport_size({"width": 390, "height": 844})
        shot(page, "settings-mobile")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("button", name="Conexiones", exact=True).click()
        expect(page.get_by_role("heading", name="WordPress + Yoast")).to_be_visible()
        shot(page, "connections-desktop")
        page.set_viewport_size({"width": 390, "height": 844})
        shot(page, "connections-mobile")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("button", name="Publicaciones", exact=True).first.click()
        page.get_by_role("button", name="Sincronizar blog").click()
        page.get_by_role("button", name="Trabajos y progreso").click()
        expect(
            page.get_by_text("La conexión wordpress no está configurada.")
        ).to_be_visible(timeout=30000)
        shot(page, "error-desktop")
        page.set_viewport_size({"width": 390, "height": 844})
        shot(page, "error-mobile")
        page.get_by_role("button", name="Cerrar diálogo").click()
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("button", name="Cerrar sesión", exact=True).click()
        expect(page.get_by_role("heading", name="Entrar al estudio")).to_be_visible()
        assert not errors, errors
        browser.close()
    (out / "e2e-report.json").write_text(
        json.dumps(
            {
                "passed": True,
                "screenshots": len(list(out.glob("*.png"))),
                "browser_errors": errors,
                "environment": "Real FastAPI, PostgreSQL and worker; test-only provider doubles; no production publishing.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "E2E completado: login, ideas, estados, generación, editor, versiones, SEO, bloqueo LinkedIn, errores, móvil y logout."
    )
finally:
    server.terminate()
    web.terminate()
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(web.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        web.wait(timeout=10)
    server.wait(timeout=10)
    backend_log.close()
    web_log.close()
