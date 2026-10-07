# Arquitectura y datos

`web` sirve el build estático y reenvía `/api/` a FastAPI con el mismo origen. `api` gestiona autenticación, edición y aceptación de operaciones duraderas (HTTP 202). `worker` reclama trabajos PostgreSQL, comparte adaptadores y servicios de aplicación con la API y persiste fases. `db` mantiene datos, cola y registros de coste. No hay Redis, cron editorial, SaaS ni publicación automática.

## Entidades

| Tabla | Función y relaciones |
| --- | --- |
| users, sessions, login_attempts | Usuario privado, sesiones revocables y limitación persistente por IP. |
| contexts | Perfil actual editable con revisión; generaciones/versiones conservan snapshot. |
| configuration | Preferencias, catálogo versionado, taxonomías reales y heartbeat de worker. |
| connections | Configuración pública permitida y credenciales cifradas con Fernet. |
| ideas | Intención, enfoque, razones, estados, relaciones semánticas y señales disponibles. |
| publications | Agrupa canales independientes; idea opcional y única, IDs remotos, URLs históricas, fechas y huellas. |
| versions | Contenido y metadatos inmutables por canal; LinkedIn apunta a su versión base WordPress. |
| evaluations | Resultado determinista y revisión editorial para una huella exacta y versión de reglas. |
| sources | Procedencia, URL, fragmento, fecha de consulta y fecha publicada solo si se conoce. |
| files | Original persistente, MIME real, tamaño, alt, ID de Medios y resultado incierto de subida. |
| metrics | Proveedor, periodos, dimensiones, indicadores, cobertura y publicación ligada a ID WP mediante URLs actuales/históricas. |
| jobs | Parámetros/modelo/contexto congelados, fase, checkpoints, lease, heartbeat, cancelación y errores. |
| ai_calls | Proveedor/modelo realmente usado, uso/caché/búsquedas, tarifas congeladas, estimación, coste calculado e incertidumbre. |
| notifications, oauth_states | Avisos internos y estados OAuth breves, de un solo uso y ligados a sesión. |

Fechas internas UTC y presentación Europe/Madrid. `published_at` proviene de `date_gmt` de WordPress; si falta no se inventa antigüedad. Las URLs históricas se mantienen al cambiar el slug. SQLAlchemy define contratos de persistencia; las migraciones Alembic están congeladas e incluyen fecha de publicación e índices GIN españoles.

## Seguridad

Contraseñas Argon2id; primer usuario y recuperación desde CLI del servidor. Cookies HttpOnly/SameSite=Lax con caducidad; escrituras requieren Origin exacto y token CSRF. Cinco intentos fallidos por IP en 15 minutos, con bloqueo transaccional PostgreSQL. Cambiar contraseña revoca otras sesiones. No existe registro público. La instancia es de un propietario: toda operación privada requiere su sesión; versiones se validan contra su publicación y no pueden cruzar recursos.

Fernet necesita `MASTER_KEY` externa a PostgreSQL. Configuraciones de conexiones tienen listas de campos públicos y secretos permitidos; las claves no vuelven al navegador. Se omiten payloads/secretos en errores y logs; las rutas API no generan access logs para evitar registrar códigos OAuth. El catálogo y snapshots no incluyen claves.

El HTML guardado elimina scripts, estilos, eventos y protocolos peligrosos. La vista previa usa iframe sin permisos de scripts; las URLs generadas sin procedencia guardada se retiran y dejan advertencia editorial. Referencias, fuentes e historial se envían como datos no confiables separados de instrucciones. La IA no tiene herramientas ni autoridad de publicación.

Las comprobaciones públicas resuelven y validan todas las IPs, fijan una IP pública conservando SNI/Host, vuelven a validar redirecciones y limitan la lectura a 2 MB. Bloquean loopback, redes privadas, link-local, metadatos, credenciales en URL y puertos arbitrarios. Las conexiones configuradas expresamente por el propietario se tratan aparte: WordPress debe ser HTTPS y las APIs oficiales tienen endpoints fijos. Un JSON Google no puede cambiar el endpoint de emisión de tokens.

## Cola y concurrencia

Reclamación mediante `FOR UPDATE SKIP LOCKED`, lease de 150 segundos y heartbeat cada 15. Checkpoints/versiones se guardan transaccionalmente; un worker recuperado reutiliza fases terminadas. Un token de propietario del lease impide que un worker antiguo continúe fases. La pérdida de respuestas IA deja una reserva y posible facturación registrada.

Una clave activa única por publicación serializa generación y envíos; la UI acepta operaciones duraderas sin retener el navegador. La edición local verifica revisión y bloquea escrituras durante trabajos activos. Reanudar un trabajo antiguo se bloquea si la publicación ha cambiado después: debe iniciarse una operación nueva sobre la versión actual.

Máximo tres intentos técnicos, backoff y Retry-After. Cuota/facturación, credenciales y permisos no se reintentan en bucle. Cancelar impide nuevas fases; no garantiza cancelar una petición ya enviada. LinkedIn no repite creaciones inciertas; WordPress reconcilia con el conector antes de repetir.

## Límites prácticos

Uso personal, un propietario. Listados UI limitados a 500 elementos y trabajos/notificaciones recientes a 50; el histórico completo sigue persistido. La recuperación de solapamientos utiliza índices de términos españoles, registros recientes y revisión semántica de candidatos relevantes (hasta 30 en el prompt), sin base vectorial externa. No garantiza detectar todo solapamiento conceptual si no hay términos compartidos; la revisión humana sigue siendo necesaria.
