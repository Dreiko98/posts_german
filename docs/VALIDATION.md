# Validación de la entrega

## Analítica editorial — 7 de octubre de 2026

Se añadió una sección Analítica con importación diaria independiente de métricas por periodos, series interactivas, rankings por artículo/tema/formato, consultas y canales, recomendaciones accionables, Wilson, anomalías MAD, proyección de referencia con backtest, Spearman y datos de producción/coste IA. Métodos, límites y uso: [ANALYTICS.md](ANALYTICS.md).

Validación: **65 pruebas backend aprobadas**, TypeScript/Vite y Ruff; navegador en escritorio y 390 px (pestañas, gráfico, prellenado de idea sin llamada IA y ausencia de desbordamiento). Capturas de regresión en screenshots/analytics-*-test.png son datos simulados explícitos. Backup previo guardado en `.local/before-analytics-20261007`, migración 0004 aplicada y nueva versión desplegada localmente.

Importación real autorizada de estadísticas, sin escritura en las plataformas ni llamadas IA: 7 julio–4 octubre, 90 días. GA4: 81 filas diarias del sitio y 662 del detalle; Search Console: 90 filas del sitio y 164 del detalle de consultas (parcial). Trabajo terminado sin errores. Dashboard real validado contra 75 publicaciones, 64 consultas agregadas y una recomendación elegible. Proyección de clics disponible; vistas sin proyección por falta de observaciones consecutivas. Endpoint protegido: 401 sin sesión. Los cuatro servicios están saludables.

## Recuperación del arranque — 7 de octubre de 2026

Diagnóstico de investigación OpenAI posterior: el primer intento guardó fuentes pero alguna llamada web no finalizó; el reintento del propietario completó la investigación y el paso de ideas fue rechazado por el proveedor. La respuesta original de rechazo no se conservaba, por lo que no se puede confirmar su parámetro exacto. Se hizo explícita la instrucción JSON también en el input, se recordó el límite de llamadas web al modelo y se añadieron estados de herramientas al diagnóstico y HTTP/parámetros conocidos a los errores, sin exponer respuestas remotas. Siete pruebas de adaptadores aprobadas con dobles, incluidas tres regresiones nuevas. La aceptación real de la petición corregida queda pendiente del siguiente reintento del propietario; no se iniciaron llamadas pagadas para probarla.

La API y el worker estaban sin salud; los registros de la API mostraban agotamiento del pool PostgreSQL. Docker/WSL tampoco respondía a operaciones de reinicio o ejecución dentro de los contenedores. Se recuperó Docker tras detener sus procesos y reiniciar WSL (la única distribución instalada era docker-desktop), conservando los volúmenes. Se reconstruyeron y arrancaron los cuatro servicios con Compose.

Se añadieron límites de espera en las peticiones del navegador y en la adquisición/conexión PostgreSQL. Los errores durante la carga inicial muestran una pantalla con reintento. Estos límites no corrigen por sí solos un bloqueo de Docker.

Validación: build TypeScript/Vite y Ruff aprobados; tres regresiones de Chromium en `scripts/test_frontend_recovery.py` (sesión no disponible, ajustes no disponibles, petición sin respuesta, con recuperación mediante reintento). Navegador contra la aplicación real: login visible y cero errores JavaScript; `/api/health` devuelve 200 y la sesión sin autenticar devuelve el 401 esperado, en lugar de 500. No se probaron credenciales reales de login ni se publicó contenido.

Para repetir las regresiones, servir `frontend/dist` en loopback 18086 y ejecutar `.venv/Scripts/python.exe scripts/test_frontend_recovery.py`.

Fecha: **5 de octubre de 2026**. Las pruebas con proveedores simulados están exclusivamente en `backend/tests`; la imagen de producción los excluye. No se ha escrito en germanmallo.com, consultado propiedades privadas ni publicado en LinkedIn.

## Resultados

- **57 pruebas de backend aprobadas**, con PostgreSQL real: sesiones/CSRF/cifrado, cola, contratos de adaptadores, costes, SEO, versiones, recuperación, integraciones y restricciones de publicación. Una advertencia de deprecación de Starlette TestClient/httpx; no hubo fallos.
- **E2E aprobado** con navegador Chromium, React, FastAPI, PostgreSQL y worker reales; proveedor IA sustituido solo durante la prueba. Login/logout, idea manual, lote de tres, selección/descarte/recuperación, publicación única, edición de ambos canales, versiones, evaluación obsoleta, bloqueo LinkedIn y error por conexión ausente. Cero errores JavaScript y cero desbordamientos horizontales a 390 px. [Informe y capturas](screenshots/e2e-report.json).
- **WordPress 6.9.4 y Yoast 28.6 reales**, en sandbox local: autenticación, creación simultánea con una correlación única, lectura posterior, campos SEO y lista permitida, conflicto por edición externa y parseo/serialización de bloque nativo. [Informe](wordpress-test-report.json).
- **Verificación adicional, 7 octubre 2026:** ZIP regenerado con carpeta raíz y permisos portables; instalación mediante el formulario multipart real de un WordPress nuevo, enlace de activación con una sola carpeta y API autenticada del conector aprobados. [Informe de instalación ZIP](wordpress-zip-test-report.json). No se modificó el sitio del propietario.
- **Paquete alternativo plano, 7 octubre 2026:** `german-studio-connector-flat.zip` pasa integridad y contiene solo PHP/readme en su raíz. La comprobación nativa adicional de esta variante quedó pendiente porque Docker bloqueó el arranque del nuevo sandbox; se detuvieron sus procesos auxiliares locales. El sandbox de la prueba anterior continuó visible y su parada tampoco respondió. No se reinició Docker ni se modificó la instancia principal o el sitio del propietario. El script admite `--flat`, puerto 18085 y tiempos máximos para comandos de Docker.
- **Backup y restauración reales** en proyectos Compose aislados: base vacía, checksums, archivos originales, descifrado con MASTER_KEY respaldada, permisos UID 10001 y persistencia tras reiniciar. [Informe](backup-test-report.json).
- Build TypeScript/Vite y Docker Compose aprobados. Cuatro servicios principales saludables. Instalación de migraciones 0001–0003 en una base vacía y `alembic check` sin diferencias.
- Ruff aprobado; auditoría npm de producción sin vulnerabilidades detectadas. Estos checks no equivalen a una auditoría de seguridad exhaustiva.
- Inspección pública de la referencia actual y revisión visual de login, Ideas, Publicaciones, editor, Ajustes y conexiones en escritorio/móvil. [Sistema visual](DESIGN.md).

## Matriz de los 23 criterios de aceptación

| Nº | Evidencia | Alcance / límite |
|---|---|---|
| 1 | Compose, migraciones desde vacío y restauración/reinicio | Instalación local real; servidor doméstico aún por configurar. |
| 2 | `test_security.py`, E2E login/logout | Sesión privada, CSRF, Origin, password hash y secretos cifrados. |
| 3 | `test_generation.py`, E2E manual/lote | IA sustituida en pruebas; llamadas oficiales implementadas. |
| 4 | Historial indexado español y revisión semántica con duplicados/continuaciones | Recuperación de candidatos acotada; puede omitir similitudes lejanas. |
| 5 | Métricas vacías, errores de búsqueda y procedencia de enlaces | Estados sin datos; sin contenido de ejemplo en producción. |
| 6 | Versionado inmutable y editor E2E de WordPress/LinkedIn | Cuerpo HTML editable con vista previa; no editor visual Gutenberg. |
| 7 | `test_content_seo.py`: resultado determinista | Evaluador propio versionado, distinto del resultado de Yoast. |
| 8 | Generación con seis evaluaciones máximas y parada por dos sin mejora | Conserva la mejor y muestra pendientes. |
| 9 | Cambio del artículo y de imagen/alt invalidan evaluación | LinkedIn queda desactualizado ante cambios del artículo. |
| 10 | Lectura posterior de contenido/SEO/imagen en integración; SEO en WP real | Media a través de dobles; sitio del propietario pendiente. |
| 11 | Correlación concurrente en WP real, pérdida de respuesta y reparación parcial | LinkedIn incierto exige reconciliación, sin repetir creación. |
| 12 | Tests parametrizados de estados WP, login/redirect/canonical y E2E botón | Comprobación repetida por backend antes del envío. |
| 13 | Contrato Posts API, URL definitiva, doble envío bloqueado | Publicación real pendiente de OAuth/permisos y acción del propietario. |
| 14 | Conflicto externo real en plugin y tests de importación | No sobrescribe el contenido remoto en conflicto. |
| 15 | Agregaciones ponderadas, URLs históricas, muestras y ventanas iguales | GA4/GSC con dobles; propiedades reales pendientes. |
| 16 | Snapshot de modelo/contexto/límites en trabajos | Selector afecta solo a nuevas operaciones. |
| 17 | Tests de fallback/capacidad/presupuesto y checkpoints parciales | El proveedor alternativo debe tener credenciales y herramienta. |
| 18 | Errores billing/cuota/permisos/429/503 y Retry-After | Saldo exacto desconocido; no se presenta como cero. |
| 19 | Claim atómico, lease expirado, checkpoints, restauración/reinicio | Llamada remota iniciada no es reversible al cancelar. |
| 20 | Cálculo Decimal, caché/búsquedas, costes desconocidos y reserva incierta | Tarifa local fechada; revisar cambios de proveedores. |
| 21 | Instrucciones aisladas, referencia adversaria y enlaces con procedencia | La IA no dispone de herramientas de publicación. |
| 22 | Acciones de interfaz conectadas a API, estados sin credenciales | Se requiere completar conexiones para utilizar plataformas. |
| 23 | Referencia pública, tokens, 15 capturas y pruebas responsive | Manrope local sustituye General Sans; no se redistribuye el tema. |

## Repetir pruebas

Requiere Docker Desktop, Python 3.11+ y Node 24. Instala `backend/requirements-dev.txt` en un entorno virtual y ejecuta `npm ci` en `frontend`. Los ejemplos de backend usan PowerShell y `.venv` en la raíz:

```powershell
docker run -d --name german-studio-test-db -e POSTGRES_USER=studio -e POSTGRES_PASSWORD=test-local-only -e POSTGRES_DB=studio_test -p 127.0.0.1:55432:5432 postgres:17.9-alpine
$env:DATABASE_URL='postgresql+psycopg://studio:test-local-only@127.0.0.1:55432/studio_test'
$env:MASTER_KEY=(& .venv/Scripts/python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
Push-Location backend
../.venv/Scripts/alembic.exe upgrade head
../.venv/Scripts/alembic.exe check
../.venv/Scripts/python.exe -m pytest -q
Pop-Location
.venv/Scripts/ruff.exe check backend scripts
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe scripts/run_e2e.py
```

Si el contenedor de pruebas ya existe, usa `docker start german-studio-test-db`. Espera a que `pg_isready` responda antes de migrar. Los tests vacían las tablas de esa base; rechazan nombres que no terminen en `_test`. En Linux utiliza los ejecutables de `.venv/bin` y `export` para las variables. E2E necesita libres 5173 y 8000; su fixture añade la marca de pruebas y nunca usa la configuración de conexiones de producción.

```powershell
Push-Location frontend
npm run build
npm audit --omit=dev
npx prettier --check "src/**/*.{ts,tsx,css}"
Pop-Location
.venv/Scripts/python.exe scripts/test_wordpress_plugin.py
.venv/Scripts/python.exe scripts/test_wordpress_zip.py
.venv/Scripts/python.exe scripts/verify_restore.py
docker compose ps
```

El script WordPress crea un sandbox propio en 18081 con Yoast descargado de wordpress.org. Detén sus servicios con `docker compose -f scripts/wordpress-sandbox.yaml down`. La prueba de restauración utiliza 18082/18083, proyectos nuevos y credenciales aleatorias; conserva los volúmenes de prueba. Nunca ejecutes pruebas destructivas contra una base real.

## Integraciones pendientes de conexión real

| Integración | Verificado | Falta aportar |
|---|---|---|
| OpenAI / Anthropic | Requests, búsqueda/citas, uso, errores y fallback con dobles; documentación oficial | Clave API, facturación y acceso al modelo/herramienta. |
| WordPress + Yoast | Plugin real en sandbox; envío/media/recuperación en tests | HTTPS, usuario con permisos, contraseña de aplicación e instalación del plugin en el sitio. |
| LinkedIn personal | OAuth y Posts implementados; contrato y restricciones probados | Aplicación con productos/scopes, callback accesible y consentimiento personal. No se ha probado consentimiento ni publicación reales. |
| GA4 | Cliente de lectura, paginación, agregaciones y muestras | Propiedad y cuenta de servicio autorizada. |
| Search Console | Cliente de lectura, URLs históricas y datos parciales | Propiedad exacta y cuenta de servicio autorizada. |

Ningún test con dobles demuestra disponibilidad, calidad factual de los textos, permisos ni saldo de una cuenta real. La revisión editorial y las comprobaciones del sitio siguen siendo parte del flujo. Las limitaciones de importación, recuperación de historial, evaluación SEO y métricas se describen en [Uso](USAGE.md), [Arquitectura](ARCHITECTURE.md), [SEO](SEO.md) e [Integraciones](INTEGRATIONS.md).
