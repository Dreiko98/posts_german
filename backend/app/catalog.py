import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from .models import Configuration
from .schemas import Preferences
from .errors import AppError

DEFAULT_CATALOG = json.loads(
    Path(__file__).with_name("catalog.json").read_text(encoding="utf-8")
)


def preferences(db):
    from .config import settings

    row = db.get(Configuration, "preferences")
    return Preferences.model_validate(
        row.value if row else {"app_name": settings.app_name}
    ).model_dump()


def catalog(db):
    row = db.get(Configuration, "catalog")
    return row.value if row else DEFAULT_CATALOG


def model_option(db, provider, model):
    for m in catalog(db)["models"]:
        if m["provider"] == provider and m["id"] == model:
            return m
    raise AppError(
        "modelo_no_disponible",
        "El modelo no está en el catálogo comprobado.",
        409,
        "Elige un modelo o actualiza el catálogo en Ajustes.",
    )


def money(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise ValueError()
        return result
    except (InvalidOperation, ValueError):
        raise AppError("importe_invalido", "Usa un importe decimal positivo.")


def calculate(rates, usage):
    if usage.get("unknown"):
        return None
    for key in ("input", "output", "cached", "search"):
        if rates.get(key) is None:
            return None
    base = max(0, usage.get("input", 0) - usage.get("cached", 0))
    amount = (
        Decimal(base) * money(rates["input"])
        + Decimal(usage.get("output", 0)) * money(rates["output"])
        + Decimal(usage.get("cached", 0)) * money(rates["cached"])
    ) / Decimal(1000000)
    if usage.get("cache_write", 0):
        if rates.get("cache_write") is None:
            return None
        amount += (
            Decimal(usage["cache_write"])
            * money(rates["cache_write"])
            / Decimal(1000000)
        )
    return amount + Decimal(usage.get("searches", 0)) * money(rates["search"])


def estimate(rates, max_searches=3):
    low = calculate(rates, {"input": 18000, "output": 7000, "searches": 1})
    high = calculate(rates, {"input": 85000, "output": 40000, "searches": max_searches})
    return {
        "currency": "USD",
        "low": str(low) if low is not None else None,
        "high": str(high) if high is not None else None,
        "assumptions": {
            "input_tokens": "18.000–85.000",
            "output_tokens": "7.000–40.000",
            "research_searches": f"1–{max_searches}",
            "seo_improvements": "0–5",
            "included": [
                "Investigación",
                "WordPress local",
                "Revisión editorial",
                "LinkedIn local",
            ],
            "excluded": ["Hosting", "Conversión a euros", "Conciliación de factura"],
        },
    }
