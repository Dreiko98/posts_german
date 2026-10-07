import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path("docs/reference")
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    findings = []
    for label, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height})
        for path, name in [("/", "home"), ("/blog/", "blog")]:
            try:
                page.goto(
                    "https://germanmallo.com" + path,
                    wait_until="domcontentloaded",
                    timeout=45000,
                )
                page.wait_for_timeout(3000)
                page.screenshot(path=str(out / f"{name}-{label}.png"), full_page=False)
                findings.append(
                    {
                        "screen": f"{name}-{label}",
                        "styles": page.evaluate(
                            """() => [...document.querySelectorAll('body,h1,h2,p,button,a')].slice(0,35).map(e=>({tag:e.tagName,text:e.innerText?.slice(0,70),color:getComputedStyle(e).color,background:getComputedStyle(e).backgroundColor,font:getComputedStyle(e).fontFamily,size:getComputedStyle(e).fontSize}))"""
                        ),
                    }
                )
            except Exception as e:
                findings.append(
                    {"screen": f"{name}-{label}", "error": type(e).__name__}
                )
        page.close()
    browser.close()
    (out / "computed-styles.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
