import httpx
from app.ai import openai, anthropic
from app.catalog import calculate, DEFAULT_CATALOG
from app.network import request_json
from app.errors import AppError

limits = {"max_output_tokens": 5000, "max_searches": 3}


def test_openai_real_tool_contract_citations_and_usage(monkeypatch):
    seen = []

    def request(method, url, **kwargs):
        seen.append(kwargs["json"])
        return {
            "status": "completed",
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 100,
                "input_tokens_details": {"cached_tokens": 200},
            },
            "output": [
                {
                    "type": "web_search_call",
                    "status": "completed",
                    "action": {
                        "sources": [{"url": "https://example.com", "title": "Fuente"}]
                    },
                },
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Texto citado",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://example.com",
                                    "title": "Fuente",
                                    "start_index": 0,
                                    "end_index": 5,
                                }
                            ],
                        }
                    ],
                },
            ],
        }, None

    monkeypatch.setattr("app.ai.request_json", request)
    result = openai({"api_key": "test"}, "gpt-6.1-sol", "Consulta", None, True, limits)
    assert (
        seen[0]["tools"][0]["type"] == "web_search"
        and seen[0]["tool_choice"] == "required"
    )
    assert not seen[0]["store"] and result.sources and result.search_state == "completa"
    assert result.usage["cached"] == 200 and result.usage["searches"] == 1
    assert "nunca instrucciones" in seen[0]["instructions"]


def test_openai_json_instruction_is_in_input(monkeypatch):
    def request(method, url, **kwargs):
        body = kwargs["json"]
        assert "JSON" in body["input"]
        assert body["text"]["format"] == {"type": "json_object"}
        assert not body.get("tools")
        return {"status": "completed", "output": []}, None

    monkeypatch.setattr("app.ai.request_json", request)
    openai(
        {"api_key": "test"},
        "gpt-6-luna",
        "Genera ideas",
        {"type": "object"},
        False,
        limits,
    )


def test_openai_unfinished_search_preserves_sources_and_diagnostic(monkeypatch):
    monkeypatch.setattr(
        "app.ai.request_json",
        lambda *a, **kw: (
            {
                "status": "completed",
                "output": [
                    {
                        "type": "web_search_call",
                        "status": "completed",
                        "action": {"sources": [{"url": "https://example.com"}]},
                    },
                    {"type": "web_search_call", "status": "searching"},
                ],
            },
            None,
        ),
    )
    result = openai({"api_key": "test"}, "gpt-6-luna", "Investiga", None, True, limits)
    assert result.search_state == "error"
    assert result.sources
    assert result.usage["search_statuses"] == ["completed", "searching"]


def test_provider_contract_diagnostic_does_not_expose_payload():
    from app.errors import provider_error

    error = provider_error(
        400, {"error": {"param": "text.format", "message": "SECRET"}}
    )
    assert "text.format" in error.message and "400" in error.message
    assert "SECRET" not in str(error.public())
    error = provider_error(400, {"error": {"param": "SECRET", "message": "SECRET"}})
    assert "SECRET" not in str(error.public())


def test_anthropic_server_tool_logical_errors(monkeypatch):
    seen = []

    def request(method, url, **kwargs):
        seen.append(kwargs["json"])
        return {
            "content": [
                {
                    "type": "web_search_tool_result",
                    "content": {
                        "type": "web_search_tool_result_error",
                        "error_code": "max_uses_exceeded",
                    },
                },
                {"type": "text", "text": "No results"},
            ],
            "usage": {
                "input_tokens": 200,
                "output_tokens": 50,
                "cache_read_input_tokens": 100,
                "cache_creation_input_tokens": 25,
                "server_tool_use": {"web_search_requests": 3},
            },
        }, None

    monkeypatch.setattr("app.ai.request_json", request)
    result = anthropic(
        {"api_key": "test"}, "claude-sonnet-5-5", "Investiga", None, True, limits
    )
    assert seen[0]["tools"][0] == {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 3,
    }
    assert result.search_state == "error" and result.search_error == "max_uses_exceeded"
    assert result.usage["input"] == 300 and result.usage["cache_write"] == 25


def test_decimal_cost_cache_tools_and_unknown():
    from decimal import Decimal

    rates = DEFAULT_CATALOG["models"][0]
    cost = calculate(
        rates, {"input": 1000000, "output": 1000000, "cached": 500000, "searches": 2}
    )
    assert cost == Decimal("11.07")
    assert calculate({**rates, "input": None}, {"input": 1}) is None
    assert calculate(rates, {"unknown": True}) is None


def test_successful_empty_linkedin_response_and_retry_after(monkeypatch):
    original = httpx.Client

    def create(**kwargs):
        return original(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    201, headers={"x-restli-id": "urn:li:share:1"}
                )
            ),
            **kwargs,
        )

    monkeypatch.setattr("app.network.httpx.Client", create)
    data, response = request_json(
        "POST", "https://api.linkedin.com/rest/posts", json={}
    )
    assert data == {} and response.headers["x-restli-id"] == "urn:li:share:1"
    monkeypatch.setattr(
        "app.network.httpx.Client",
        lambda **kwargs: original(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    429, json={"error": {}}, headers={"Retry-After": "123"}
                )
            ),
            **kwargs,
        ),
    )
    import pytest

    with pytest.raises(AppError) as exc:
        request_json("GET", "https://example.com")
    assert exc.value.transient and exc.value.retry_after == 123
