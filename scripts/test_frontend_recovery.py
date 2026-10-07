"""Browser regression checks; serve frontend/dist on loopback port 18086 first."""
import json
from playwright.sync_api import sync_playwright, expect


with sync_playwright() as p:
    browser = p.chromium.launch()
    for scenario in ("session_error", "preferences_error", "timeout"):
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        recovered = [False]
        pending = []

        def respond(route):
            path = route.request.url.split("/api", 1)[1]
            status = 200
            data = []
            if path == "/auth/session":
                if scenario == "timeout" and not recovered[0]:
                    pending.append(route)
                    return  # Leave pending to exercise the actual request timeout.
                if scenario == "session_error" and not recovered[0]:
                    status, data = 503, {"error": {"message": "Servicio no disponible"}}
                elif scenario in ("session_error", "timeout"):
                    status, data = 401, {"error": {"code": "sesion_requerida"}}
                else:
                    data = {"username": "test", "csrf": "test"}
            elif path == "/preferences":
                if not recovered[0]:
                    status, data = 503, {"error": {"message": "Servicio no disponible"}}
                else:
                    data = {"app_name": "Test", "provider": "openai", "model": "test"}
            elif path == "/catalog":
                data = {"version": "test", "models": []}
            elif path == "/estimate":
                data = {"currency": "USD", "low": None, "high": None, "assumptions": {}}
            route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

        page.route("**/api/**", respond)
        page.goto("http://127.0.0.1:18086")
        expect(page.get_by_role("heading", name="No se pudo cargar el estudio")).to_be_visible(timeout=22000)
        if scenario == "timeout":
            expect(page.get_by_text("El servidor no ha respondido a tiempo.")).to_be_visible()
        recovered[0] = True
        page.get_by_role("button", name="Volver a intentar").click()
        if scenario == "preferences_error":
            expect(page.locator(".app-shell")).to_be_visible()
        else:
            expect(page.get_by_role("heading", name="Entrar al estudio")).to_be_visible()
        assert not errors, errors
        print(f"PASS {scenario}: visible error and successful retry")
        for route in pending:
            route.abort()
        page.unroute_all(behavior="ignoreErrors")
        page.close()
    browser.close()
