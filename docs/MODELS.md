# Catálogo y costes

Catálogo inicial `2026-10-05.1`, editable desde Ajustes. Fuentes verificadas el 5 octubre 2026: [precios OpenAI](https://developers.openai.com/api/docs/pricing), [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [precios Anthropic](https://platform.claude.com/docs/en/about-claude/pricing) y [modelos Anthropic](https://platform.claude.com/docs/en/models/overview). Acceso de cuenta se comprueba con credenciales; una opción en catálogo no promete acceso concedido.

| Modelo / proveedor | Entrada USD/MTok | Salida | Lectura caché | Escritura caché 5m | Búsqueda USD/uso |
| --- | ---: | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / OpenAI | 2 | 10 | 0,10 | 2,50 | 0,01 |
| gpt-6-luna / OpenAI | 0,10 | 0,50 | 0,01 | 0,125 | 0,01 |
| claude-sonnet-5-5 / Anthropic | 2 | 10 | 0,20 | 2,50 | 0,01 |
| claude-haiku-4-5 / Anthropic | 1 | 5 | 0,10 | 1,25 | 0,01 |

Tarifas base estándar, contexto corto/global, sin batch/fast mode ni descuentos/conversión. No se solicitan cachés de escritura explícitas en esta versión; se contabilizan si aparecen en usage. El contexto máximo es de 80.000 caracteres, muy por debajo del contexto largo de estos modelos. Revisa las tarifas si cambian modelos, regiones o modalidades.

OpenAI usa `/v1/responses`, `store:false`, herramienta `web_search` real, required durante investigación, max_tool_calls y citas/source records. Anthropic usa `/v1/messages`, la herramienta básica oficialmente compatible `web_search_20250305`, max_uses y citations. No añade ejecución de código ni filtering dinámico facturable; inspecciona errores de herramientas incluso con HTTP 200. Fuentes: [OpenAI web search](https://developers.openai.com/api/docs/guides/tools-web-search), [Claude web search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool).

Las salidas JSON se validan con Pydantic; el límite de tokens, respuestas truncadas o esquemas inválidos dejan el trabajo incompleto y las versiones guardadas intactas. Solo el modelo general rige tareas nuevas. Las descripciones de calidad/rapidez son prudentes, no un ranking demostrado.

## Cálculo

Con aritmética Decimal:

`((entrada − lectura_cache) × tarifa_entrada + lectura_cache × tarifa_cache + salida × tarifa_salida + escritura_cache × tarifa_escritura) / 1.000.000 + búsquedas × tarifa_búsqueda`

En Anthropic input_tokens excluye lecturas/cache writes: se añade la lectura a la entrada registrada y la escritura se cobra aparte. En OpenAI cached_tokens es subconjunto de input_tokens. Las búsquedas y tokens de contenido se contabilizan conforme al usage del proveedor; no se incluye un descuento inventado. Si falta usage, el coste queda desconocido y se reserva el máximo estimado, nunca se muestra cero facturado.

Estimación visible por publicación: 18.000–85.000 tokens de entrada, 7.000–40.000 de salida, 1–máximo de búsquedas, redacción, revisión, adaptación y 0–5 mejoras. Es un rango orientativo, no precio fijo. La reserva de seguridad para el límite es más conservadora que esa estimación: contexto máximo + margen de instrucciones/esquemas + tokens máximos de salida y fases restantes. Puede detener una operación que probablemente costase menos, preservando el progreso.

Cada llamada guarda tarifas y modelo efectivos, uso real, coste calculado y estimación previa. Una respuesta perdida puede estar facturada sin usage; se registra incertidumbre y reserva. El panel muestra últimas 500 llamadas y su alcance, no conciliación completa de una factura ni saldo exacto del proveedor.

Fallback opcional: ante errores compatibles de facturación/cuota, credenciales/permisos o disponibilidad, consulta una alternativa configurada solo si soporta la tarea y cabe en el gasto acumulado más reserva restante. Registra la ruta efectiva y aviso. No cambia el selector ni un trabajo activo. Si fallan ambas rutas, conserva checkpoints y muestra acción siguiente. Tarifas desconocidas impiden una generación con control de gasto.

Errores se distinguen en autenticación, permisos, facturación/cuota, crédito agotado solo cuando el proveedor lo indica, saturación, respuesta perdida y límite de gasto. [Errores OpenAI](https://developers.openai.com/api/docs/guides/error-codes) y [errores Anthropic](https://platform.claude.com/docs/en/api/errors). Un 429 por sí solo nunca se etiqueta como saldo agotado. Consulta los paneles oficiales para saldo/facturación.
