class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        action: str = "",
        transient: bool = False,
        retry_after: int = 0,
    ):
        self.code, self.message, self.status, self.action, self.transient = (
            code,
            message,
            status,
            action,
            transient,
        )
        self.retry_after = retry_after
        super().__init__(message)

    def public(self):
        return {"code": self.code, "message": self.message, "action": self.action}


def provider_error(status: int, data: dict):
    connector_errors = {
        "external_change": (
            "cambios_externos",
            "El artículo WordPress ha cambiado desde su última lectura.",
            "Importa la versión remota antes de actualizar.",
        ),
        "not_draft": (
            "wordpress_no_borrador",
            "El artículo remoto ya no es un borrador editable.",
            "Revísalo desde WordPress.",
        ),
        "busy": (
            "wordpress_ocupado",
            "WordPress está procesando este borrador.",
            "Comprueba el estado antes de reintentar.",
        ),
        "yoast_missing": (
            "yoast_no_instalado",
            "El conector requiere Yoast SEO gratuito.",
            "Instala y activa Yoast SEO gratuito.",
        ),
        "yoast_indexable": (
            "yoast_indexable",
            "Los metadatos se guardaron, pero Yoast necesita reindexación.",
            "Revisa el análisis SEO desde WordPress.",
        ),
    }
    if data.get("code") in connector_errors:
        code, message, action = connector_errors[data["code"]]
        return AppError(code, message, 409, action)
    error = data.get("error", {})
    if not isinstance(error, dict):
        error = {}
    code = str(error.get("code") or error.get("type") or "")
    if code in ("insufficient_quota", "billing_error"):
        return AppError(
            "facturacion_cuota",
            "El proveedor indica un problema de facturación o cuota.",
            409,
            "Revisa el panel del proveedor.",
        )
    if "credit balance" in str(error.get("message", "")).lower():
        return AppError(
            "credito_agotado",
            "El proveedor indica crédito insuficiente.",
            409,
            "Añade crédito en el panel del proveedor.",
        )
    if status == 401:
        return AppError(
            "autenticacion_proveedor",
            "Credenciales del proveedor no válidas.",
            409,
            "Revisa la conexión en Ajustes.",
        )
    if status == 403:
        return AppError(
            "permisos_proveedor",
            "La conexión no tiene los permisos necesarios.",
            409,
            "Revisa permisos y acceso al modelo.",
        )
    if status == 429:
        return AppError(
            "saturacion",
            "El proveedor ha limitado temporalmente las solicitudes.",
            503,
            "Espera y reintenta.",
            True,
        )
    if status >= 500 or status == 408:
        return AppError(
            "proveedor_temporal",
            "El proveedor no está disponible temporalmente.",
            503,
            "Reintenta más tarde.",
            True,
        )
    parameter = error.get("param")
    known_parameters = {
        "model",
        "input",
        "text.format",
        "text.format.type",
        "max_output_tokens",
        "max_tool_calls",
        "tools",
        "tool_choice",
        "instructions",
    }
    detail = f" (HTTP {status}"
    if isinstance(parameter, str) and parameter in known_parameters:
        detail += f"; parámetro: {parameter}"
    detail += ")."
    return AppError(
        "contrato_proveedor",
        "El proveedor rechazó la solicitud" + detail,
        409,
        "Revisa configuración, modelo y requisitos del proveedor.",
    )
