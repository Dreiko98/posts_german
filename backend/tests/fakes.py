import json
from copy import deepcopy
from app.ai import AIResponse
from tests.test_content_seo import good_article


def fake_ai(config, model, prompt, schema, research, limits):
    usage = {
        "input": 1000,
        "output": 500,
        "cached": 0,
        "searches": 1 if research else 0,
    }
    if research:
        return AIResponse(
            "Fuente técnica consultada con búsqueda simulada solo para tests.",
            usage,
            [
                {
                    "url": "https://developer.wordpress.org/rest-api/",
                    "title": "WordPress REST API",
                    "excerpt": "Referencia técnica",
                }
            ],
            "completa",
        )
    name = schema.get("title")
    if name == "IdeaBatch":
        n = 1 if "hasta 1 ideas" in prompt else 3
        value = {
            "ideas": [
                {
                    "title": f"Automatización útil para el proceso {i + 1}",
                    "summary": "Cómo elegir un proceso real y reconocer dónde aporta valor.",
                    "angle": f"Una perspectiva propia sobre el caso {i + 1}",
                    "topic": "Automatización",
                    "content_type": "Divulgación técnica",
                    "rationale": "Conecta con el perfil de datos y automatización.",
                    "project_connection": "",
                    "current_news": False,
                }
                for i in range(n)
            ],
            "explanation": "",
        }
    elif name == "Relations":
        value = {"relations": []}
    elif name == "Article":
        value = good_article()
    elif name == "EditorialReview":
        value = {
            "warnings": [
                "Revisión simulada: confirmar afirmaciones antes de publicar."
            ],
            "personal_claims_to_confirm": [],
            "unsupported_claims": [],
            "readability_notes": [],
        }
    elif name == "LinkedInText":
        value = {
            "text": "Automatizar empieza por entender el problema. A veces un proceso claro aporta más que otra herramienta. ¿Qué decisión merece realmente tu tiempo?"
        }
    else:
        raise AssertionError(name)
    return AIResponse(json.dumps(value, ensure_ascii=False), usage, [])


class FakeWordPress:
    posts = {}
    keys = {}
    meta = {}
    medias = {}
    next_id = 10
    creates = 0
    fail_seo = False
    lose_response = False

    @classmethod
    def reset(cls):
        cls.posts, cls.keys, cls.meta, cls.medias = {}, {}, {}, {}
        cls.next_id, cls.creates, cls.fail_seo, cls.lose_response = 10, 0, False, False

    def __init__(self, config):
        self.base = config.get("url", "https://germanmallo.com")

    def post(self, id):
        return deepcopy(self.posts[id])

    def correlation(self, key):
        return {"post_id": self.keys.get(key)}

    def upsert_draft(self, key, content, post_id=None, expected_hash=""):
        import httpx

        if key in self.keys and post_id is None:
            return {"post_id": self.keys[key]}
        if post_id is None:
            post_id = type(self).next_id
            type(self).next_id += 1
            type(self).creates += 1
            self.keys[key] = post_id
        self.posts[post_id] = {
            "id": post_id,
            "status": "draft",
            "password": "",
            "link": f"https://germanmallo.com/{content['slug']}/",
            "title": {"raw": content["title"], "rendered": content["title"]},
            "content": {"raw": content["content"], "rendered": content["content"]},
            "excerpt": {"raw": content["excerpt"]},
            "slug": content["slug"],
            "categories": content["categories"],
            "tags": content["tags"],
            "featured_media": 0,
            "modified_gmt": "2026-10-05T10:00:00",
        }
        if self.lose_response:
            type(self).lose_response = False
            raise httpx.ReadTimeout("Lost")
        return {"post_id": post_id}

    def seo(self, id):
        return deepcopy(self.meta.get(id, {}))

    def request(self, method, path, **kwargs):
        from app.errors import AppError

        data = kwargs.get("json", {})
        if path.startswith("german-studio/v1/posts/"):
            if self.fail_seo:
                raise AppError("seo_no_persistido", "Simulated metadata failure", 409)
            self.meta[int(path.split("/")[3])] = data
            return data
        if path == "wp/v2/media":
            self.medias[50] = {"id": 50, "alt_text": ""}
            return self.medias[50]
        if path == "wp/v2/media/50":
            if method == "POST":
                self.medias[50].update(data)
            return deepcopy(self.medias[50])
        if path.startswith("wp/v2/posts/"):
            id = int(path.split("/")[-1])
            self.posts[id].update(data)
            return self.posts[id]
        if path == "wp/v2/posts":
            return list(deepcopy(self.posts).values())
        raise AssertionError(path)

    def taxonomy(self, kind):
        return []
