# Analítica editorial

La sección **Analítica** cruza las observaciones diarias de GA4 y Search Console con artículos, versiones actuales, evaluaciones SEO vigentes, categorías WordPress, ideas (incluidos descartes) y costes IA registrados. La lectura es bajo demanda; no hay publicación automática ni llamadas IA al abrir el panel.

## Uso

1. Sincronizar el blog desde Publicaciones para conservar IDs, categorías y URLs históricas.
2. Abrir Analítica; seleccionar hasta 180 días. Pulsar **Ver periodo** y después **Importar datos diarios**. Se crea un trabajo persistente, visible en Trabajos. Por defecto se muestran 90 días hasta tres días antes de hoy.
3. **Evolución y decisiones**: totales del sitio, gráfico diario, media móvil de siete observaciones consecutivas, recomendaciones con evidencia, acceso al artículo y preparación de una idea.
4. **Qué funciona**: filtrar artículos por título y tema, ordenar por vistas/clics/vistas por día/cambio; comparar temas y formatos, antigüedad, CTR y su intervalo aproximado.
5. **Demanda y canales**: consultas reales, impresiones, clics, CTR y posición ponderada; origen/medio de tráfico por página, incluido LinkedIn cuando consta en GA4.
6. **Análisis estadístico**: anomalías, patrones semanales, proyección descriptiva, correlaciones y estado/coste de producción editorial.
7. Exportar CSV de las series diarias. Preparar idea únicamente abre el formulario con un brief; el usuario confirma la generación y su gasto por separado.

## Datos y calidad

- `analytics_rows`: proveedor, propiedad, conjunto (site/content), fecha, dimensiones, valores y calidad. `analytics_batches`: periodo solicitado, procedencia, metadatos de cobertura y fecha de importación. Migración 0004. Las métricas originales por periodos permanecen en su tabla independiente.
- Los totales GA4 se consultan por fecha, separadamente del detalle fecha/página/origen. No se suman sesiones de páginas como sesiones únicas del sitio. Los totales Search Console se consultan por fecha y búsqueda web; el detalle añade página/consulta.
- Una actualización sustituye el rango de observaciones de ese proveedor/propiedad/conjunto en una transacción. Los rangos solapados no duplican visitas y las filas desaparecidas de la respuesta se retiran. Se conserva el registro de importaciones. No se mezclan propiedades anteriores tras cambiar la conexión.
- Hasta 100.000 filas por conjunto; una respuesta truncada, umbrales, muestreo o pérdida de filas se identifica como parcial. Search Console no ofrece un historial completo de consultas y puede omitir búsquedas anónimas.
- Un día sin observación aparece como hueco, nunca como cero inventado. Los periodos anteriores al seguimiento tampoco se extrapolan. GA4 usa la fecha de su propiedad; Search Console usa Pacific Time.
- Vinculación por rutas actuales e históricas del blog. Las filas no vinculadas cuentan en la cobertura; los totales incluyen toda la propiedad. Para propiedades GA4 que midan varios dominios con rutas idénticas se necesita ampliar la vinculación por hostname antes de interpretar los rankings.
- La categoría histórica viene de WordPress; los formatos sin clasificación no se infieren como un hecho. SEO solo se usa si su evaluación coincide con la versión/fingerprint actuales.
- LinkedIn no proporciona mediante esta conexión estadísticas del perfil; el panel solo muestra tráfico que GA4 atribuye a LinkedIn. No se inventan likes ni impresiones.

## Métodos v1

- CTR = suma de clics / suma de impresiones. Posición = suma(posición × impresiones) / suma de impresiones. Engagement = sesiones con interacción / sesiones. Intervalo Wilson al 95%, aproximado por posibles dependencias entre observaciones.
- Comparación descriptiva entre mitades del periodo: vistas por día observado, mínimo siete días por mitad. Puede estar sesgada por días sin registro; no equivale a crecimiento por día natural.
- Anomalías: ventana previa de hasta 28 días, mínimo 14 observaciones; |valor − mediana| > 3,5 × max(1, 1,4826 × MAD) y cambio absoluto mínimo 5. No determina la causa.
- Proyección: mínimo 42 días consecutivos observados, máximo 56 usados. Se reserva la última semana para comparar MAE de media de siete días y repetición de la semana previa; se elige el menor y se proyectan siete días. Banda ±2 MAE, explícitamente no calibrada como intervalo probabilístico. Es un modelo de referencia, no una garantía ni una previsión de negocio.
- Patrones por día: media de observaciones y n visibles; no identifica el mejor día para publicar.
- Spearman con rangos medios para empates, mínimo diez artículos con siete días observados; longitud, antigüedad y SEO frente a vistas por día observado. No acredita causalidad y no ajusta por todas las variables de confusión.
- Recomendaciones: optimizar artículos con >=100 impresiones y posición 4–20; comparar CTR con al menos dos artículos con posición cercana (±3), si existen. Revisar caídas superiores al 30% con >=100 vistas. Probar continuaciones de temas con >=3 artículos medidos y >=100 vistas. Explorar consultas con >=100 impresiones y posición >=8, filtrando coincidencias léxicas con ideas, incluidos descartes. La revisión semántica se realiza posteriormente en el flujo habitual de generación.
- Prioridades heurísticas `editorial-analytics-v1`: impresiones × brecha CTR (o 0,01 sin pares), vistas × caída, vistas de tema × 0,01, impresiones de consulta × 0,02. No son estimaciones de clics incrementales.
- Costes: llamadas registradas por fecha Europe/Madrid; costes calculados separados de reservas inciertas. El estado del banco de ideas es actual, no un histórico de transiciones. No se calcula ROI sin ingresos/objetivos observados.

## Verificación

65 pruebas backend aprobadas tras migrar PostgreSQL de prueba. Regresiones nuevas: actualización solapada/idempotencia, separación totales/detalle/propiedades, URLs históricas, huecos, ponderación, Wilson, backtest, empates y muestras insuficientes, sesión y validación de rangos. `scripts/test_analytics_browser.py` verifica pestañas, gráfico, móvil sin desbordamiento y preparación de brief sin iniciar IA; sus capturas en docs/screenshots utilizan datos simulados explícitos. Build TypeScript/Vite y Ruff aprobados.

Fuentes oficiales: [dimensiones y métricas GA4](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema), [Search Analytics query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).
