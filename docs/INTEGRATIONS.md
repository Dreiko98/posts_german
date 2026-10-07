# Conexiones e integración

Contratos consultados el **5 octubre 2026**. Los endpoints son implementaciones reales HTTP; las credenciales solo se usan en backend. Falta configurar cuentas del propietario: ningún resultado con mocks acredita permisos reales.

## WordPress

HTTPS y contraseña de aplicación de un usuario autorizado para editar entradas. [Autenticación oficial](https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/), [entradas](https://developer.wordpress.org/rest-api/reference/posts/), [Medios](https://developer.wordpress.org/rest-api/reference/media/). Importación paginada de estados publicados y no públicos, categorías/etiquetas y versiones locales. No se importan los comentarios ni se rastrea el perfil LinkedIn.

Instala [german-studio-connector.zip](../wordpress/german-studio-connector.zip) desde Plugins → Añadir plugin → Subir plugin, o copia `wordpress/german-studio-connector` en `wp-content/plugins`. Activa el conector y deja Yoast SEO gratuito activo. El conector declara versión y versión de Yoast en GET `/german-studio/v1/health`. POST `/drafts` acepta solo campos de entrada, crea draft y usa una clave UUID, tabla con índice único y bloqueo MySQL GET_LOCK. Las tablas WP deben ser InnoDB para la transacción de creación; la meta `_gstudio_request_key` permite reconciliar. GET `/drafts?key=…` consulta el ID antes de reintentar.

GET/POST `/posts/{id}/seo` permite exclusivamente frase clave, título SEO y metadescripción. Verifica `edit_post` y utiliza `WPSEO_Meta::set_value/get_value` con sanitización de Yoast. Reconstruye indexables para la representación REST. La [API REST de Yoast](https://developer.yoast.com/customization/apis/rest-api/) es de lectura; no se utiliza como endpoint de escritura. [Clase de metadatos oficial](https://github.com/Yoast/wordpress-seo/blob/trunk/inc/class-wpseo-meta.php) e [integración](https://developer.yoast.com/development/integrating/).

Tras enviar, la app lee contenido/metadatos/imagen por separado. Ante fallo parcial conserva ID; ante pérdida de respuesta de creación consulta correlación antes de repetir. Una imagen ya subida reutiliza ID; resultado incierto exige reconciliación manual en Medios. Cambios de fecha o huella bloquean actualizaciones. La app no publica entradas ni modifica un artículo publicado con el flujo normal.

**Prueba nativa realizada:** WordPress 6.9.4, PHP 8.3 y Yoast gratuito 28.6 en contenedores locales desechables. Autenticación, dos creaciones concurrentes con el mismo UUID, lectura posterior SEO, rechazo de meta arbitraria, conflictos y parser nativo de bloques. Esto no verifica los plugins/tema instalados en germanmallo.com. Actualiza el conector sustituyendo archivos; desactivar/desinstalar conserva entradas y correlaciones, según `readme.txt`.

### Instalación del ZIP y rutas

Sube directamente `wordpress/german-studio-connector.zip` desde el formulario WordPress, sin descomprimir ni volver a comprimir su carpeta. La ruta instalada debe ser `wp-content/plugins/german-studio-connector/german-studio-connector.php`, con una sola carpeta del plugin. No subas la carpeta `wordpress` del repositorio.

Si la activación muestra «El archivo del plugin no existe», comprueba que no use una ruta antigua o repetida como `german-studio-connector/german-studio-connector/german-studio-connector.php`. Vuelve al listado de plugins y usa el botón de activación actual. Si el plugin no aparece, reinstala el ZIP; si una carpeta residual bloquea la instalación, renombra únicamente esa carpeta desde el administrador de archivos del hosting y vuelve a subir el paquete. No cambies las carpetas de otros plugins.

`python scripts/package_wordpress_plugin.py` genera el ZIP con rutas POSIX, una carpeta raíz explícita y permisos de archivos portables. `python scripts/test_wordpress_zip.py` prueba el formulario de subida real y la activación en un WordPress nuevo aislado en loopback 18084, sin montar la carpeta fuente. Informe: `wordpress-zip-test-report.json`.

Como alternativa ante una instalación anidada, [german-studio-connector-flat.zip](../wordpress/german-studio-connector-flat.zip) contiene directamente el PHP y el readme, sin carpetas internas. Súbelo tal cual desde WordPress; el instalador crea `german-studio-connector-flat/german-studio-connector.php`. Usa el botón de activación recién generado. No reutilices enlaces de la instalación anterior. Se genera con `python scripts/package_wordpress_plugin.py --flat`; su prueba de subida/activación se ejecuta con `python scripts/test_wordpress_zip.py --flat` en el puerto local 18085.

## LinkedIn personal

[Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-09), [OAuth Authorization Code](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow), [Share on LinkedIn](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin), [OpenID Connect](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2).

Crea una app en LinkedIn Developers y solicita los productos y permisos requeridos; su aprobación/disponibilidad depende de LinkedIn. Configura `client_id`, `client_secret` y callback exacto `http://localhost:8080/api/oauth/linkedin/callback`, igual a APP_ORIGIN. Debe estar registrado y ser accesible desde el navegador mediante tu túnel; no necesitas hacer público el servidor. Si LinkedIn rechaza el callback local de tu app, configura un origen HTTPS autorizado que siga siendo accesible de forma privada y actualiza APP_ORIGIN/cookies. No se afirma que cualquier app tenga todos los permisos concedidos.

La autorización solicita `openid profile w_member_social`, usa estado de un solo uso ligado a sesión y recupera `sub` mediante userinfo. Tokens se cifran; guarda caducidad y reautoriza cuando expire. No se presupone refresh token para apps sin ese producto.

Envía un post de texto con URL a `/rest/posts`, `LinkedIn-Version: 202609`, `X-Restli-Protocol-Version: 2.0.0`, autor personal, visibilidad PUBLIC, distribución MAIN_FEED y lifecycleState PUBLISHED. No simula borrador nativo con NONE. Límite de texto conservador 3.000 caracteres, incluyendo enlace. La versión del contrato se configura por entorno y deberá actualizarse antes de su retirada.

Antes del envío, WordPress debe ser publish, sin contraseña; la URL pública debe responder con el contenido correspondiente, sin login/redirección a otra página/canonical ajeno. Revisa la adaptación vigente. Cada operación requiere clic expreso y se serializa por publicación. Un timeout/error ambiguo conserva estado incierto, sin reintentar creación. Registra manualmente ID tras revisar el perfil. No se promete lectura automática de posts personales restringidos ni analítica LinkedIn; usa importación manual de texto si no hay acceso.

## Google Analytics 4 y Search Console

[GA4 Data API](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart), [Search Analytics query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query). Crea una cuenta de servicio y activa ambas APIs en Google Cloud. Añade su email como usuario de lectura a las propiedades correspondientes. Guarda el JSON cifrado y configura ID numérico GA4/propiedad Search Console exacta (`sc-domain:…` o URL). El backend emite tokens con scopes analytics.readonly/webmasters.readonly; solo acepta el token_uri oficial Google.

GA4 consulta pagePath y sessionSourceMedium, sesiones, vistas, sesiones con interacción y eventos. Pagina y conserva señales de umbrales/muestreo/límites como parcial. Search Console consulta página/consulta, clics, impresiones, CTR y posición; devuelve filas principales, siempre identificadas como cobertura parcial. Consulta ventanas equivalentes bajo demanda. No busca noticias ni actualiza automáticamente por calendario.

Las métricas se vinculan a publicaciones con ID WP y conjunto de URLs históricas. CTR = clics/impresiones; posición = suma(posición × impresiones)/suma(impresiones). GA4 conserva ratios por sesiones. Las sesiones por página pueden duplicar una sesión entre páginas; no se anuncian como sesiones únicas del sitio. Origen/medio LinkedIn se identifica cuando existe; no se inventa atribución ni datos con pocos registros.

## Estado de verificación

| Integración | Implementación | Verificación realizada | Pendiente del propietario |
| --- | --- | --- | --- |
| OpenAI | Responses + web_search + JSON validado + usage | Contratos/dobles; fuentes oficiales consultadas | Clave API, acceso a modelos y herramientas; llamadas reales. |
| Anthropic | Messages + web_search_20250305 + errores lógicos + usage | Contratos/dobles | Clave API y búsqueda habilitada en organización; llamadas reales. |
| WordPress/Yoast | Importación, taxonomías, Medios, borradores y conector | Mocks y conector/Yoast reales en sandbox local | Instalar plugin y verificar permisos/tema en tu web. |
| LinkedIn | OAuth y Posts, bloqueo por URL pública | Mocks de publicación/errores y comprobaciones backend | App/productos/permisos, OAuth y envío expreso real. |
| GA4/Search Console | API de lectura, periodos y correspondencias | Mocks de contratos, agregación y datos ausentes | JSON de cuenta de servicio, propiedades y permisos; informes reales. |

No se ejecutaron escrituras contra plataformas del propietario ni peticiones IA con saldo real. Las capturas de pruebas identifican expresamente los proveedores simulados.
