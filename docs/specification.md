# Prompt definitivo para Codex: plataforma editorial personal de Germán Mallo

## 1. Tu encargo y forma de trabajar

Actúa como un ingeniero de software sénior con criterio de producto. Construye una web app completa, mantenible y lista para desplegar mediante Docker Compose en mi servidor doméstico. Debes implementar el producto descrito en este documento, no limitarte a un plan, un diseño de interfaz o una demostración con datos ficticios.

Este documento es la especificación funcional autoritativa y contiene decisiones ya acordadas. No necesito otra ronda general de preguntas para redefinir el producto. Resuelve los detalles rutinarios con criterio, registra tus decisiones y pregunta solamente cuando una información indispensable no se pueda inferir ni resolver de manera reversible. Trabaja hasta entregar la aplicación, las integraciones implementadas, las pruebas pertinentes y la documentación de instalación.

Antes de modificar un repositorio, inspecciona su estructura, las instrucciones aplicables y su estado de Git. Preserva cambios existentes. Si hay código de PostPilot disponible, examínalo y reutiliza únicamente lo que encaje; si no lo hay, construye un proyecto independiente. La falta de código anterior no bloquea el desarrollo.

Comprueba la documentación oficial vigente de APIs, modelos, precios y dependencias antes de implementar sus contratos. No copies modelos antiguos, endpoints obsoletos o precios del TFG. Fija versiones compatibles y utiliza migraciones de base de datos. Lleva un plan de trabajo y verifica cada bloque antes de continuar.

No publiques contenido real ni modifiques mi web o LinkedIn como parte de pruebas automáticas. Implementa los botones reales y verifica con dobles de prueba o un entorno de pruebas. Las acciones reales sobre plataformas se ejecutarán cuando yo las solicite expresamente o pulse el botón correspondiente en la aplicación. No expongas la aplicación a Internet durante el desarrollo. No necesito que contrates servicios ni que configures reenvíos de puertos.

Si faltan credenciales o permisos, termina el código, la configuración y las pruebas simuladas; muestra la integración como no conectada y documenta cómo completarla. No sustituyas una integración por una pantalla decorativa ni digas que has comprobado una conexión real si no lo has hecho.

## 2. Qué producto estamos construyendo

Quiero una plataforma privada para crear contenido para mi blog WordPress y mi perfil personal de LinkedIn. Tendrá exactamente dos módulos principales: **Ideas** y **Publicaciones**, más **Ajustes**.

Su diferencia respecto a un generador genérico es que utiliza conjuntamente:

1. Contexto actualizado sobre quién soy, mis proyectos y cómo escribo.
2. Ideas existentes, descartadas, borradores y artículos publicados para evitar solapamientos.
3. Estadísticas reales de GA4 y Google Search Console para orientar los temas y enfoques.
4. Búsqueda web en tiempo de ejecución cuando la actualidad o la verificación del contenido lo requieran.
5. Un ciclo de redacción, evaluación SEO reproducible y revisión editorial.
6. Mi supervisión y edición antes de publicar.

Todo funciona bajo demanda. Yo decido cuándo generar ideas, cuántas generar y cuándo crear publicaciones. No hay una cuota semanal de artículos ni publicación automática por calendario.

PostPilot es la inspiración conceptual: generación contextualizada con datos y evaluación del contenido. Simplifica su lógica para este uso personal. No necesitamos datos financieros, SABI, Business Health Score, Prophet, clustering empresarial, gestión de clientes, varios usuarios comerciales, campañas o un producto SaaS.

Nombre provisional: **Germán Content Studio**. Haz que el nombre sea configurable; no lo trates como una marca definitiva.

## 3. Perfil y estrategia editorial

Referencias:

- Web: https://germanmallo.com/
- Blog: https://germanmallo.com/blog/
- Perfil facilitado por el propietario: https://www.linkedin.com/in/german-mallo/
- Si está disponible como adjunto, memoria de PostPilot: `memoria_44927333F(2).pdf`. Es una referencia, no una dependencia para entender este encargo.

Soy Germán Mallo Faure, graduado en Ciencia de Datos por la Universitat Politècnica de València, con experiencia en desarrollo, IA aplicada y automatización. Mi perfil combina Python, datos, APIs, aplicaciones, RAG, herramientas y soluciones a problemas reales. La información actualizada de mi ficha prevalecerá sobre descripciones antiguas del blog.

El contenido debe conservar su carácter divulgativo y, cuando encaje, dirigir de forma natural hacia las soluciones y automatizaciones que desarrollo. Quiero mostrar criterio y capacidad para resolver problemas, sin convertir todos los artículos en textos de venta ni añadir llamadas comerciales agresivas.

El público es amplio: estudiantes, profesionales, empresarios y personas que llegan desde LinkedIn o la web. La explicación debe ser accesible y conservar precisión; ajusta el nivel a la idea concreta.

Hay varios tipos de contenido: divulgación técnica, proyectos y aprendizajes propios, reflexiones y opiniones, actualidad comentada, sistemas y herramientas, productividad y negocio. Mi voz suele ser directa y cercana, con ejemplos y analogías. Puede ser crítica y tener personalidad. No impongas una estructura idéntica ni un cierre comercial a todos los textos.

Tienes libertad creativa porque supervisaré los borradores. Usa hechos personales proporcionados o confirmados. Si propones una anécdota o experiencia en primera persona que no consta en el contexto, identifícala en la revisión como algo que debo confirmar, sin inventar que he usado una herramienta, trabajado con un cliente o conseguido un resultado concreto.

Todo el contenido y la interfaz estarán inicialmente en español. Revisa la web actual para orientar el contexto inicial, pero no mezcles información de homónimos ni conviertas los likes o recomendaciones de LinkedIn en experiencias profesionales propias. Si LinkedIn bloquea la lectura, admite una carga manual de texto o documentos.

## 4. Arquitectura y despliegue

Stack acordado:

- Frontend: React y TypeScript, con una herramienta de build ligera como Vite.
- Backend: Python y FastAPI; validación de contratos mediante Pydantic.
- Base de datos: PostgreSQL, ORM y migraciones versionadas, por ejemplo SQLAlchemy y Alembic.
- Worker: proceso Python separado que comparte la lógica de aplicación con la API.
- Despliegue: Docker Compose con cuatro servicios: `web`, `api`, `worker`, `db`.

`web` servirá el frontend y reenviará las rutas de API para mantener un único origen. API y worker pueden compartir imagen. Usa una cola persistente de trabajos en PostgreSQL; no añadas Redis o una plataforma de orquestación solo para este volumen. Si necesitas Node para reutilizar análisis SEO, intégralo de forma controlada en el worker o justifica una adaptación equivalente.

La interfaz seguirá funcionando mientras una generación larga se ejecuta. Devuelve un identificador de trabajo al iniciar tareas, muestra progreso por fases y actualiza por polling o SSE. Una operación no debe depender de que el navegador permanezca abierto.

El acceso inicial será mediante túnel SSH sobre Tailscale. Expón por defecto únicamente el puerto de entrada web en loopback del servidor y documenta el reenvío del túnel. PostgreSQL y servicios internos no publicarán puertos al exterior. No configures Tailscale, SSH ni el router sin una instrucción específica.

La app requiere usuario y contraseña aunque el acceso sea privado. No implementes registro público. Incluye un procedimiento seguro de creación del primer usuario, contraseñas con hash, sesión mediante cookie HttpOnly, protección adecuada de operaciones de escritura y límite de intentos de login. Ajusta HTTPS/cookies al acceso local y documenta cómo se endurece si en el futuro se expone por dominio.

Las claves de proveedores, credenciales WordPress y tokens OAuth se gestionan en backend. Si se configuran desde Ajustes, guárdalas cifradas y utiliza una clave maestra externa a la base de datos. Nunca devuelvas secretos completos al frontend ni los registres en logs. Incluye `.env.example` con nombres de variables y valores de ejemplo no sensibles. No incluyas credenciales por defecto activas.

Datos e imágenes persistirán en volúmenes. Incluye comprobaciones de salud, apagado ordenado y documentación de copia y restauración conjunta de datos, archivos y material necesario para descifrar conexiones.

## 5. Modelo de información

Diseña entidades y relaciones claras. Como mínimo:

### Contexto del propietario

- Perfil actual, trayectoria, conocimientos, proyectos, objetivos y público.
- Preferencias de tono, ejemplos y aspectos a evitar.
- Hechos o experiencias personales confirmados.
- Procedencia de información importada y fechas de actualización.

Debe ser editable. Distingue información personal vigente de ejemplos históricos de estilo. Guarda una referencia o snapshot del contexto usado en cada generación.

### Ideas

- ID, origen `manual_guiado` o `automatico`, entrada original del usuario, título provisional, resumen, enfoque, temática y tipo de contenido.
- Justificación editorial, conexión con mis proyectos, fuentes, actualidad y contenidos relacionados.
- Estado: pendiente, seleccionada, utilizada o descartada.
- Motivo de descarte, notas personales, fechas y lote de generación si corresponde.
- Enlace a publicación asociada cuando exista.

Una idea pasa a utilizada cuando el artículo asociado se publica en WordPress. Un borrador local no significa que ya esté publicada. Una idea descartada se conserva y se puede recuperar.

### Publicaciones y canales

- Una publicación agrupa artículo WordPress y adaptación LinkedIn.
- Relación opcional con idea: los artículos históricos importados pueden no tener una idea propia.
- Identificadores remotos, URL canónica actual y fechas de sincronización.
- Estados independientes por canal; no utilices un único booleano `published` para ambos.
- Versión actual, mejor versión del ciclo SEO y versión que se envió a cada plataforma.
- Categorías, etiquetas, imagen, metadatos y fuentes.
- Detección de cambios externos mediante fecha remota y/o huella del contenido.

En primera versión, una idea tiene como máximo una publicación asociada. Si ya existe, el botón debe abrirla. Una derivación con enfoque nuevo puede crear una idea nueva relacionada.

### Versiones y evaluaciones

Guarda versiones al generar, aplicar correcciones IA o guardar una edición significativa; no crees una por cada pulsación. Cada evaluación apunta al contenido y metadatos concretos analizados, con huella, versión del evaluador y fecha. Una edición deja la evaluación anterior pendiente de actualizar, en lugar de mostrarla como válida para el texto nuevo.

La adaptación LinkedIn registra de qué versión del artículo procede. Cambios relevantes del artículo producen aviso de adaptación pendiente. No sobrescribas automáticamente mis ediciones de LinkedIn al detectar cambios en WordPress.

### Fuentes, métricas, archivos y trabajos

- Fuentes: URL, título, fecha publicada si puede verificarse, fecha consultada, fragmento/resumen utilizado y relación con idea/publicación/versión. No inventes una fecha si solo conoces cuándo se consultó.
- Métricas: proveedor, artículo, periodo, dimensiones, indicadores, calidad/completitud y fecha de consulta.
- Archivos: imagen original, tipo, tamaño, texto alternativo e identificador WordPress cuando se suba.
- Trabajos: tipo, parámetros, fases, estado, checkpoints, cancelación, errores, intentos, lease y heartbeat.
- Llamadas IA: proveedor/modelo efectivamente usado, tokens, herramientas de búsqueda, tarifas aplicadas, moneda, coste estimado y coste calculado.

Usa fechas UTC internamente y presentación Europe/Madrid. Vincula estadísticas al ID del artículo WordPress y mantiene la correspondencia con URL histórica/actual cuando cambia el slug; no hagas desaparecer los resultados históricos.

## 6. Módulo Ideas: dos entradas obligatorias

### A. Crear idea manualmente, asistida por IA

Botón **Crear idea manualmente**. Acepta un texto libre, notas o enlace. Ejemplo: «Quiero hacer una idea sobre lo último de OpenAI».

Este flujo también usa IA: transforma mi intención en una idea concreta, investiga si necesita actualidad, define un enfoque propio, compara el historial y guarda una propuesta editable. No lo conviertas en un formulario que únicamente almacena el título introducido. La primera versión debe permitir hacerlo con una sola entrada de texto; los campos adicionales son opcionales.

### B. Generar con IA

Botón **Generar con IA**. Pido X ideas, con cantidad configurable y un límite razonable por operación. Puedo añadir temática o instrucciones opcionales, pero el uso habitual debe ser elegir cantidad y generar.

Combina contexto, historial, resultados y actualidad. Mezcla según relevancia:

- Noticias directamente relacionadas con IA, datos, automatización o tecnología.
- Noticias de otros ámbitos con una conexión razonada y útil con mis temas.
- Contenido de conocimiento, reflexiones, experiencias o proyectos sin depender de una noticia reciente.

No fuerces conexiones absurdas ni conviertas todas las propuestas en noticias. Tampoco rellenes el lote con propuestas pobres para alcanzar X. Si no consigues X propuestas suficientemente distintas, devuelve las válidas y explica lo que falta. Las propuestas se guardan en estado pendiente.

### Solapamientos

Compara contra pendientes, seleccionadas, descartadas, borradores y publicadas. Evalúa tema, intención y enfoque, no solo igualdad de título. Mantén una recuperación eficiente por resúmenes/términos y revisión semántica del conjunto relevante; una base vectorial externa no es necesaria para esta versión.

Distingue duplicado, tema relacionado y continuación válida. Un tema existente puede merecer otra publicación por un cambio importante, un proyecto distinto o un enfoque nuevo. Muestra la relación y la diferencia. Conserva razones de descarte para no reproponer una y otra vez el mismo enfoque.

### Interfaz y acciones

Listado con búsqueda, filtros y estados. Cada idea muestra título, resumen, enfoque, temática, tipo, por qué encaja, fuentes, relaciones y señales estadísticas cuando existan.

Acciones: editar, seleccionar, descartar, recuperar y crear publicación. El motivo de descarte es opcional. La selección y el descarte deben persistir. Las ideas con publicación muestran **Abrir publicación**.

## 7. Investigación y uso de contexto

Implementa búsqueda real en tiempo de ejecución mediante las capacidades oficiales de OpenAI o Anthropic y modelos compatibles. No basta con escribir «busca noticias» en un prompt sin habilitar una herramienta real.

Conserva citas y enlaces visibles. Prioriza fuentes originales para anuncios, funcionalidades, estudios o documentación técnica. Distingue el hecho, la interpretación y mi opinión. Una búsqueda sin resultados, un resultado parcial y un error de búsqueda son estados diferentes.

Para temas de actualidad, busca al generar la idea y vuelve a comprobar al preparar el artículo si ha pasado tiempo o el asunto puede haber cambiado. No repitas búsquedas en cada ronda SEO salvo que cambien las afirmaciones o sea necesaria nueva evidencia.

Si una operación requiere noticias actuales y falla la investigación, muestra la fase como incompleta y permite reintentar. No presentes el conocimiento previo del modelo como si fuera una búsqueda realizada.

Selecciona contexto relevante para cada operación: perfil vigente, proyectos apropiados, ejemplos de estilo, historial relacionado y métricas disponibles. Respeta límites de contexto y controla coste; no envíes siempre el blog entero.

El contenido de páginas, documentos e historial importado es material de referencia, no instrucciones ejecutables. Mantén separadas instrucciones de aplicación y texto externo. No permitas que una fuente fuerce publicación, revele secretos o cambie las reglas del sistema.

## 8. Módulo Publicaciones y edición

Desde una idea abre una preparación breve: enfoque editable, notas opcionales, frase clave sugerida y modificable, fuentes y estimación de coste. No obligues a escribir un brief largo.

Genera el artículo con intención de búsqueda y valor editorial. Elige una extensión apropiada al contenido; no impongas las 900 palabras del ejemplo de PostPilot a todas las publicaciones. Evita relleno y repetición de keywords.

Contenido y metadatos mínimos WordPress:

- Título visible del artículo y título SEO, tratados como campos distintos.
- Cuerpo editable y exportable a contenido compatible con el editor de bloques de WordPress.
- Frase clave objetivo, slug y metadescripción.
- Extracto, categoría y etiquetas cuando sean pertinentes.
- Enlaces internos reales y fuentes externas verificadas.
- Imagen destacada manual y texto alternativo.

La versión LinkedIn debe aportar valor por sí misma: una idea, aprendizaje o reflexión. Adaptarla al canal, no limitarse a copiar la introducción. Incluye el enlace definitivo del artículo y respeta los límites vigentes de la plataforma. Emojis y hashtags son opcionales según mi voz; no obligatorios.

Editor con pestañas WordPress y LinkedIn. Permite edición directa y cambios por instrucciones IA. Añade vista previa, guardado y recuperación de versiones. La previsualización de la app es aproximada; el tema WordPress determina el resultado final.

Acciones separadas: **Reevaluar** solo analiza; **Corregir problemas** modifica; **Actualizar adaptación de LinkedIn** regenera su versión preservando la anterior.

El cuerpo generado no debe contener marcadores internos de IA, instrucciones de imágenes, citas inexistentes o HTML inseguro. No incluyas un doble H1 si el tema ya representa el título como H1. Mantén edición nativa razonable en WordPress; prueba la serialización de los bloques utilizados.

## 9. Algoritmo SEO y revisión editorial

La referencia es **Yoast SEO gratuito**. No necesitamos Premium. Comprueba qué partes de su motor abierto pueden utilizarse con la versión y licencia correspondientes. No dependas de un plugin modificado o de funciones Premium.

Prioriza análisis reproducible de los criterios técnicos; una segunda llamada IA revisa aspectos editoriales, pero no es la autoridad que inventa el resultado SEO.

Entre las comprobaciones aplicables: frase clave en título SEO, slug, introducción, metadescripción y encabezados; uso natural y densidad; estructura; ancho/longitud de título y metadescripción; enlaces internos y externos; longitud adecuada; legibilidad; posibles frases clave ya utilizadas; imágenes y alt cuando estén presentes.

Comprueba los criterios exactos actuales por idioma y versión. No prometas equivalencia exacta con Yoast si implementas aproximaciones. Separa análisis SEO, legibilidad, revisión editorial y verificación de fuentes. Diferencia controles del texto de comprobaciones que dependen del sitio y de la representación final en WordPress.

### Puntuación y ciclo acordados

La app mostrará una puntuación propia **0–100**, no un «porcentaje oficial de Yoast». Documenta su fórmula y fija sus reglas de manera versionada. Si normalizas resultados de Yoast, conserva los resultados originales y describe la transformación. En un evaluador propio, usa pesos explícitos y una fórmula determinista, por ejemplo suma ponderada normalizada de criterios aplicables; valida los umbrales con ejemplos, no los elijas para que todos los artículos aprueben.

Hay **una generación inicial + hasta cinco rondas de mejora**, es decir, como máximo seis versiones de redacción dentro del ciclo SEO. Los reintentos técnicos tienen su propio límite, cuentan como gasto y no deben generar rondas SEO infinitas.

Algoritmo:

1. Preparar investigación, enfoque e intención, elegir frase clave.
2. Redactar artículo y metadatos.
3. Evaluar contenido y metadatos exactos, revisar calidad editorial y evidencia.
4. Si la puntuación es al menos 70, dar por terminado el ciclo SEO y mostrar las advertencias editoriales o de fuentes pendientes por separado.
5. Si es menor, pasar al redactor una lista concreta de problemas y pedir correcciones focalizadas.
6. Reevaluar la versión resultante; guardar todas las versiones y conservar la mejor.
7. Terminar al alcanzar 70, agotar cinco mejoras, llegar al límite de coste o detectar falta de mejora sostenida. Define y prueba esta última condición; un valor inicial razonable son dos rondas consecutivas sin mejora.
8. Si no se alcanza el umbral, dejar el mejor borrador como requiere revisión, con explicación. Nunca borrarlo ni presentarlo como aprobado.

No apruebes afirmaciones sin evidencia porque subió el SEO. La revisión editorial y factual mostrará sus pendientes aunque el ciclo SEO termine. No trates las advertencias como una publicación automática: siempre superviso.

La ausencia de imagen manual puede dejar comprobaciones de imagen pendientes. Identifica la puntuación textual y la cobertura de análisis, sin aparentar que el artículo completo ha superado todas las comprobaciones de WordPress. Añadir imagen/metadatos modifica la huella de evaluación. Mantén separadas legibilidad y SEO si mezclar ambas oculta problemas.

## 10. WordPress y conector Yoast

Conecta por REST API de WordPress sobre HTTPS y contraseña de aplicación. Soporta importación paginada, categorías, etiquetas y artículos históricos. Las lecturas autenticadas necesarias deben estar en backend.

La REST API propia de Yoast es de lectura. Implementa un pequeño plugin propio incluido en el repositorio para guardar de forma autenticada y autorizada frase clave, título SEO y metadescripción. Usa una lista de campos permitidos, validación y APIs/hooks apropiados para la versión instalada. No expongas escritura arbitraria de metadatos. Documenta instalación, actualización y desinstalación sin borrar contenido innecesariamente.

Sube la imagen mediante Media API y guarda alt antes de asociarla. Comprueba tipo y tamaño, usa nombres seguros y evita re-subidas repetidas si ya existe el identificador remoto.

Botones:

- **Enviar borrador a WordPress**: crea con estado `draft`.
- **Actualizar borrador en WordPress**: actualiza el mismo ID si sigue siendo un borrador editable.
- **Abrir en WordPress**: lleva a la revisión nativa.
- **Comprobar publicación**: recupera estado y URL actuales.

En esta versión publico el artículo finalmente desde WordPress. No conviertas el botón de enviar borrador en publicar.

Guarda confirmación de contenido, campos SEO e imagen por separado. Si el artículo se crea pero falla un metadato, muestra envío parcial y permite reparar ese punto sin crear otro artículo. Lee de vuelta los campos guardados.

Detecta ediciones remotas antes de actualizar un borrador previamente enviado. No sobrescribas cambios externos silenciosamente. Si ya está publicado, el flujo normal de actualización de borrador no debe devolverlo a draft ni editarlo inadvertidamente.

Para reintentos de creación, utiliza una clave de correlación propia persistida también en el conector y una búsqueda/verificación antes de crear. La creación debe poder reconciliar una respuesta perdida. Si no puede confirmarse el resultado, mantén estado incierto para comprobarlo; no repitas a ciegas.

## 11. LinkedIn y bloqueo por artículo público

Solo perfil personal. Usa la API oficial, OAuth y permisos vigentes. Documenta los requisitos de creación/configuración de aplicación y el callback accesible desde mi navegador mediante el túnel, sin asumir que el servidor deba estar expuesto públicamente.

La API de creación de posts no permite crear el borrador nativo previsto inicialmente. Por tanto, el borrador de LinkedIn se guarda **en nuestra app** y se publica desde ella cuando yo pulso el botón.

Regla obligatoria, comprobada también en backend:

**No se puede publicar en LinkedIn hasta que el artículo asociado en WordPress esté publicado y su URL definitiva sea accesible públicamente.**

Antes de cada envío:

1. Recupera el artículo por su ID; debe estar en estado `publish`, sin contraseña ni condición privada.
2. Recupera su URL definitiva y comprueba su accesibilidad sin autenticación. No basta con un HTTP 200 de una página de login, un error o una redirección a otro contenido.
3. Verifica que la adaptación no esté desactualizada de manera relevante y avisa si necesita revisión.
4. Inserta o actualiza el enlace del artículo, evitando URLs de preview o duplicadas.
5. Envía únicamente al pulsar **Publicar en LinkedIn**.
6. Guarda identificador remoto y resultado.

Publicar WordPress no dispara automáticamente LinkedIn. Deshabilitar el botón en frontend no sustituye la validación del backend. Usa bloqueos para impedir dos envíos simultáneos de la misma publicación.

No trates `feedDistribution: NONE` ni una visibilidad distinta como un borrador personal. No dependas de automatización de navegador o cookies privadas como integración principal.

Comprueba cómo enviar un post con enlace y, si se utiliza tarjeta de artículo, qué campos y assets requiere la API; no supongas que el scraping de la URL funciona en todos los modos. Un post de texto con URL es una salida válida para primera versión. La miniatura manual es obligatoria como capacidad de WordPress, no como generador automático de tarjetas LinkedIn.

La lectura de publicaciones históricas personales puede requerir permisos restringidos. Permite carga manual cuando no estén disponibles. No prometas analítica de LinkedIn ni extracción automática de todo el perfil si no hay acceso. En primera versión las estadísticas automáticas exigidas son GA4 y Search Console.

Tras un timeout de envío, no reintentes creación automáticamente si no puedes comprobar el resultado: muestra estado incierto y explica cómo reconciliarlo. Evita prometer entrega exactamente una vez cuando una API externa no permite verificarla.

## 12. Estadísticas y aprendizaje editorial

Conecta las APIs oficiales GA4 Data API y Search Console con permisos de lectura. Configura propiedad GA4 y propiedad Search Console. Incluye pruebas de conexión y avisos por permisos insuficientes, datos inexistentes o informes parciales.

Actualización mediante **Actualizar datos**, mostrando cuándo ocurrió. No añadas búsquedas de noticias en segundo plano ni un plan editorial automático.

Indicadores relevantes:

- Search Console: clics, impresiones, CTR, posición media y consultas por página cuando estén disponibles.
- GA4: sesiones/vistas según el informe, interacción y eventos pertinentes configurados.
- Tráfico desde LinkedIn si puede distinguirse por origen/medio o UTM. Puedes añadir UTM al enlace preservando la URL de referencia.

Agrupa por temática, enfoque y formato. Compara ventanas equivalentes, considera antigüedad del artículo y tamaño de muestra. No mezcles sesiones GA4 con clics Search Console como si midieran lo mismo ni hagas medias simples de ratios cuando corresponde ponderar por sus denominadores.

Muestra señales interpretables, no causalidad ni garantías: «este tema ha recibido más clics en este periodo» y «hay pocos datos para concluir». Si no hay datos, genera con contexto e historial y muestra su ausencia. No inventes rendimiento ni volúmenes de búsqueda.

Mantén una proporción de exploración para no recomendar exclusivamente temas ya exitosos. Selecciones, descartes y correcciones orientan el contexto futuro sin entrenar obligatoriamente un modelo propio.

## 13. Proveedores, selector general y costes

Tengo saldo API de OpenAI y Anthropic. Implementa ambos adaptadores y **un único selector general** de proveedor y modelo visible en frontend. Su elección se aplica a las tareas IA nuevas: ideas, investigación compatible, redacción, revisión y adaptación. No muestres selectores separados por tarea en esta versión.

El proveedor/modelo se fija al iniciar una operación. Un cambio del selector no altera un trabajo en marcha. Una revisión editorial puede ser otra llamada al mismo modelo con instrucciones distintas; no necesitas otro proveedor obligado para hacer de revisor.

Cada opción debe mostrar:

- Nombre del proveedor y modelo, disponibilidad/capacidades.
- Una frase breve y prudente sobre calidad esperada de redacción, rapidez y coste.
- Precio base utilizado y fecha/origen de verificación.
- Estimación de coste de preparar una publicación completa, incluyendo WordPress, LinkedIn, investigación y revisión.

No presentes opiniones sobre calidad como rankings demostrados ni una estimación como precio fijo. Obtén tarifas de documentación oficial; el endpoint de listado de modelos no necesariamente da precios ni explica capacidades. Mantén un catálogo versionado y editable de modelos comprobados. Excluye embeddings, modelos obsoletos y opciones que no puedan cumplir las tareas que anuncias. Si una búsqueda necesita una ruta/modelo distinto, resuélvelo explícitamente en el adaptador, explica su coste y registra lo realmente utilizado; no lo ocultes.

Calcula un rango previo con supuestos visibles: contexto, longitud esperada, llamadas de revisión, coste de búsqueda, salida LinkedIn y posibles mejoras SEO. Calcula después los costes con el usage real de cada llamada, incluyendo caché y herramientas cuando corresponda. El resultado es el coste calculado por la app, no una conciliación garantizada con la factura.

Muestra moneda de las tarifas; si hay conversión a euros, explicita tipo y fecha. No inventes una conversión o descuento. Usa aritmética decimal para importes.

Si falla el principal, podrá pasar a una alternativa compatible dentro de un **límite configurable de coste**, con aviso visible y registro. Aplica el límite al gasto acumulado esperado restante de la operación, no solo a una tarifa aislada. Si no puede continuar, conserva el progreso. Separa fallos transitorios, autenticación, permisos, cuota, límite de gasto y saldo agotado; los fallos permanentes no se arreglan con reintentos infinitos.

Notifica en frontend cuando el proveedor indique falta de crédito. Si el error solo permite concluir que hay un problema de facturación o cuota, utiliza esa descripción. No conviertas todos los 429 en «sin saldo». No prometas consultar saldo exacto o avisar antes de agotarlo sin una API oficial fiable. Muestra estado desconocido cuando corresponda, gasto registrado por la app y enlace al panel del proveedor.

## 14. Tareas persistentes y recuperación

Implementa cola PostgreSQL con reclamación atómica, lease y heartbeat. Maneja trabajos pendientes, en ejecución, terminados, fallidos, cancelados, interrumpidos y resultados parciales. No ejecutes trabajos duraderos únicamente como background tasks en memoria de FastAPI.

Guarda checkpoints de investigación, versiones y resultados de evaluación. Al recuperar un trabajo, reutiliza fases completadas y reconciliar efectos externos antes de repetirlos. Evita trabajadores duplicados sobre el mismo trabajo.

Reintentos técnicos limitados, backoff y respeto a instrucciones del proveedor. Ten en cuenta que una llamada IA cuya respuesta se pierde puede haberse facturado aunque no tengas usage; registra esa incertidumbre. Cancelar una tarea impide nuevas fases, aunque no garantice cancelar una llamada externa ya enviada.

Incluye límites de tiempo, tokens, búsquedas, cantidad de ideas y coste. Valida respuestas estructuradas por esquema y maneja salidas inválidas sin perder borradores. Las fuentes o herramientas pueden fallar dentro de una respuesta HTTP exitosa: inspecciona también su resultado lógico.

## 15. Interfaz y experiencia

Diseño limpio, profesional, responsive, cómodo en escritorio y móvil, completamente en español. Navegación: Ideas, Publicaciones, Ajustes. **La estética debe basarse explícitamente en la web actual https://germanmallo.com/**. Este requisito es obligatorio y se concreta en la sección 20: extrae su lenguaje visual y adáptalo a la aplicación editorial. No construyas un dashboard genérico que solo utilice mi nombre ni importes WordPress/Elementor como dependencia de la app.

- Ideas: dos entradas claras, cantidad, filtros, estados, detalle, fuentes y acciones.
- Publicaciones: listado con estados por canal, score actual o pendiente, última edición y trabajo asociado.
- Editor: pestañas de canales, metadatos, imagen, instrucciones IA, vista previa, revisiones y problemas concretos.
- Ajustes: mi contexto, conexiones, generación/catálogo, límites y cuenta.
- Barra superior: proveedor/modelo general y acceso a notificaciones.

Incluye estados vacíos, carga, errores, conexión incompleta y datos parciales. Las credenciales se muestran enmascaradas. Los botones no harán nada ficticio. Los datos de ejemplo estarán limitados a pruebas o un modo de demostración identificado, nunca confundidos con métricas reales.

El menú de generación/edición de miniaturas queda fuera de esta versión. Sí debe funcionar subida manual, preview y alt. No añadas otros módulos, calendarios, envío de emails, prospección, gestión de clientes o notificaciones externas no solicitadas.

## 16. Contratos de API de la aplicación

Define OpenAPI y modelos tipados. Puedes ajustar nombres de rutas a la estructura del repositorio, manteniendo como mínimo estas capacidades:

- Login, logout, sesión actual y gestión de mi contraseña.
- Lectura/edición del contexto y sus referencias.
- CRUD de ideas, cambios de estado, creación guiada y generación de lotes como trabajos.
- Preparación/generación de publicación desde una idea y consulta/edición de cada canal.
- Listado, recuperación de versiones, reevaluación y corrección como acciones separadas.
- Subida de imagen y actualización de alt.
- Conexiones, prueba de conexión, catálogo de modelos y estimación de costes.
- Sincronización del blog y métricas.
- Envío/actualización del borrador WordPress y comprobación de publicación.
- Publicación LinkedIn con validación de artículo público.
- Estado/progreso/cancelación de trabajos y notificaciones.

Trabajos largos devuelven aceptación e ID de trabajo; las consultas de estado devuelven fases y resultados guardados. Errores con código estable, explicación en español y siguiente acción cuando corresponda. Valida propiedad/permisos, concurrencia de edición y tamaños de entrada.

No permitas que URLs de fuentes o comprobaciones públicas accedan arbitrariamente a servicios internos, loopback o metadatos de infraestructura. Valida destinos y redirecciones. Las conexiones explícitamente configuradas se tratan por separado de URLs no confiables.

## 17. Pruebas y criterios de aceptación

Escribe pruebas útiles sobre riesgos y comportamientos reales, no tests que solo repitan la implementación. Usa PostgreSQL también en los tests que dependan de sus bloqueos o semántica. Verifica el recorrido principal con pruebas de integración y E2E; no requieras publicar en producción para aprobar.

La entrega debe demostrar:

1. Docker Compose arranca con migraciones y configuración documentada; datos/archivos sobreviven reinicios.
2. Sin sesión no se accede a datos ni operaciones. Login y logout funcionan, sin secretos visibles.
3. Crear idea manualmente invoca IA y desarrolla mi intención; generar X ideas guarda propuestas y sus estados.
4. El historial detecta duplicados semánticos relevantes y permite continuaciones con enfoque diferente.
5. No hay métricas, fuentes, fechas ni búsquedas ficticias cuando faltan datos o servicios.
6. Las dos adaptaciones son editables y conservan versiones.
7. Evaluar dos veces una entrada idéntica con las mismas reglas produce el mismo score SEO.
8. El ciclo respeta una inicial + cinco mejoras como máximo; conserva la mejor versión y devuelve pendientes si no aprueba.
9. Cambiar el contenido invalida la evaluación anterior y puede marcar la adaptación LinkedIn desactualizada.
10. WordPress recibe un borrador con contenido, imagen y campos SEO; la lectura posterior verifica su persistencia.
11. Un fallo parcial o doble clic no crea varios artículos; una respuesta perdida se reconcilia o queda incierta.
12. LinkedIn se bloquea tanto en UI como backend cuando WordPress está draft, future, private, protegido, inaccesible o en error.
13. Un artículo público permite publicar LinkedIn únicamente por acción explícita, usando URL definitiva.
14. Las ediciones externas se detectan y no se sobrescriben silenciosamente.
15. GA4 y Search Console se pueden actualizar; datos escasos/parciales se distinguen de un rendimiento bajo.
16. El selector general afecta a nuevas tareas y no cambia las activas.
17. El fallback respeta capacidades y límite de coste, lo notifica y conserva trabajo cuando ambos proveedores fallan.
18. Se distinguen saldo, cuota, permisos y saturación; no hay reintentos infinitos por facturación.
19. Cerrar navegador/reiniciar worker no pierde versiones completadas ni provoca envíos remotos duplicados.
20. Costes estimados y calculados se separan y contabilizan búsquedas/revisiones; una tarifa faltante se marca como desconocida.
21. Una fuente externa no puede alterar instrucciones de sistema ni autorizar publicaciones.
22. La interfaz no contiene acciones decorativas presentadas como integraciones terminadas.
23. Login, Ideas, Publicaciones, editor y Ajustes comparten un sistema visual reconociblemente basado en germanmallo.com, con tokens documentados, contraste legible y adaptación móvil comprobada.

Prueba también una restauración de backup y revisa visualmente las pantallas principales, estados vacíos, errores, móvil y editor. Documenta qué verificaciones reales no pudieron ejecutarse por falta de permisos o credenciales.

## 18. Orden de implementación y entregables

Implementa progresivamente, manteniendo el producto ejecutable:

1. Estructura, Compose, base de datos, migraciones, login, secretos y trabajos.
2. Contexto, importación WordPress e historial.
3. Adaptadores IA, búsqueda, catálogo, estimación y las dos entradas de ideas.
4. Editor, generación de artículos, evaluación SEO, correcciones, versiones y LinkedIn local.
5. Plugin conector, borradores WordPress y publicación LinkedIn condicionada.
6. GA4/Search Console, recomendaciones, costes, recuperación y pruebas completas.

No dejes la analítica o una integración prometida como un TODO sin explicarlo. Si hay una restricción real externa, termina su parte implementable y describe el bloqueo concreto.

Entregables mínimos:

- Repositorio completo de frontend, API, worker y migraciones.
- Dockerfiles y Compose reproducible, dependencias fijadas y healthchecks.
- Plugin WordPress propio con instrucciones de instalación.
- `.env.example`, setup inicial y configuración de conexiones sin secretos.
- Documentación funcional, arquitectura, modelo de datos y estados.
- Explicación de la fórmula SEO y de su relación/limitaciones frente a Yoast.
- Documentación de modelos, capacidades y cálculo de costes, con fuentes/fechas.
- Pruebas y comandos para ejecutarlas.
- Manual de acceso mediante túnel, backups y recuperación.
- Sistema de diseño derivado de germanmallo.com: tokens, componentes y capturas de las pantallas principales en escritorio y móvil.
- Lista clara de integraciones probadas realmente, probadas con mocks y pendientes de conexión.

Al terminar, informa de lo construido, cómo arrancarlo, qué comprobaciones pasaron, qué configuración debo aportar y qué limitaciones reales permanecen. No entregues solamente un plan ni una interfaz con simulaciones como si fuera el producto completo.

## 19. Documentación oficial de partida

Estas referencias orientan las integraciones; consulta sus versiones actuales durante el desarrollo:

- WordPress posts: https://developer.wordpress.org/rest-api/reference/posts/
- WordPress authentication: https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/
- WordPress Media API: https://developer.wordpress.org/rest-api/reference/media/
- Yoast REST API y limitaciones: https://developer.yoast.com/customization/apis/rest-api/
- Integración Yoast: https://developer.yoast.com/development/integrating/
- Criterios del análisis SEO: https://yoast.com/features/seo-analysis/
- GA4 Data API: https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart
- Search Console Search Analytics: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- LinkedIn Posts API: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
- LinkedIn OAuth: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow
- OpenAI búsqueda web: https://developers.openai.com/api/docs/guides/tools-web-search
- OpenAI errores: https://developers.openai.com/api/docs/guides/error-codes
- Claude búsqueda web: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
- Claude errores: https://platform.claude.com/docs/en/api/errors

Comprueba precios, permisos, modelos y requisitos vigentes antes de hacer afirmaciones o fijar un catálogo. Cuando no haya una capacidad disponible, muestra la limitación y conserva el flujo acordado sin inventar endpoints ni sustituir decisiones del propietario.

## 20. Dirección visual obligatoria: germanmallo.com

Quiero que la estética de la app se base en **https://germanmallo.com/**. Antes de diseñar las pantallas, inspecciona la web actual y su blog en escritorio y móvil. Usa la versión actual como referencia; no copies el aspecto de capturas antiguas ni los valores genéricos de Elementor que no representen los estilos realmente aplicados.

La inspección de los estilos públicos realizada el 5 de octubre de 2026 identifica este punto de partida, que debes confirmar al implementar:

| Elemento | Referencia encontrada | Aplicación en la web app |
| --- | --- | --- |
| Fondo | Oscuros `#121212` y `#0F0F0F` | Tema oscuro inicial, con superficies distinguibles para trabajar. |
| Superficies | `#1C1C1C`; tarjetas con `#151918` | Listados, tarjetas de ideas, menús y paneles del editor. |
| Acento | Verde `#00FF85` | Acción principal, selección, detalles de marca y progreso. |
| Texto | Blanco y grises secundarios; en tarjetas, `#C6CECA` y `#BCC6C0` | Jerarquía legible y contraste suficiente. |
| Tipografía | `GeneralSans` / General Sans y fallback sans-serif | Titulares con personalidad y texto de trabajo cómodo. |
| Bordes | Líneas finas con baja opacidad | Separación de secciones y paneles. |
| Radios | Variables del tema de 5, 8 y 15 px; tarjetas alrededor de 14 px | Sistema coherente de controles, tarjetas y diálogos. |
| Movimiento | Transiciones breves, en torno a 0,255 s en el tema | Feedback discreto y respeto a movimiento reducido. |

Referencias técnicas observadas: `wp-content/themes/monogram/assets/css/main.min.css`, `wp-content/themes/monogram-child/style.css`, `wp-content/themes/monogram-child/germa-areas.css` y estilos de la home. Son referencias para identificar la identidad visual, no una instrucción de copiar todas esas hojas ni redistribuir el tema.

La web utiliza titulares de gran tamaño, espaciado generoso, etiquetas breves y una estética tecnológica sobria con acento verde. Traslada esa personalidad al producto, ajustando la escala a una herramienta de uso diario:

- Navegación y encabezados con la identidad de Germán Mallo, jerarquía clara y uso contenido del verde.
- Tarjetas de ideas basadas en las superficies, bordes y tipografía de la web, con acciones y estados fáciles de comparar.
- Editor con espacio amplio de lectura, controles organizados y panel de evaluación sin competir con el texto.
- Formularios, selectores, tablas, pestañas, diálogos, notificaciones y estados vacíos diseñados como parte del mismo sistema.
- Imágenes manuales con tratamiento consistente y sin deformar ni recortar información importante.
- Colores de aviso/error diferenciados del acento de marca, acompañados por texto o iconos; el color no será el único indicador.
- Tipografía de cuerpo y contrastes adecuados para escribir y leer durante mucho tiempo. Si empleas verde luminoso como fondo de botón, utiliza texto oscuro con contraste suficiente.

Define tokens CSS centralizados para colores, superficies, texto, bordes, radios, espaciado, tipografía y transiciones. Documenta cuáles vienen de la referencia y cuáles son adaptaciones para usabilidad. Usa General Sans si puedes incorporarla correctamente; si no, elige una fuente disponible con carácter similar e identifica la sustitución. No hagas depender el aspecto de recursos temporales o de hotlinks al servidor de la web.

Adapta el lenguaje visual de la web a un panel editorial: los grandes titulares de una landing no deben consumir toda la pantalla del editor. Las animaciones, esferas, carruseles o efectos decorativos de la home no son requisitos de la aplicación. Prioriza lectura, rapidez, navegación por teclado, foco visible y responsive.

No añadas una landing comercial o una web pública: aplica esta estética a login y a las pantallas funcionales acordadas. No uses una plantilla administrativa sin adaptar, una identidad azul/púrpura ajena o efectos visuales que sustituyan funciones.

Valida visualmente login, Ideas, listado de Publicaciones, editor y Ajustes en escritorio y móvil. Incluye capturas de la app y una explicación breve del sistema visual derivado. Si la referencia no se puede consultar, utiliza la paleta y características documentadas aquí e indica qué parte no pudo verificarse; continúa con el trabajo.

**Empieza inspeccionando el entorno, el repositorio y la referencia visual. Después implementa este producto de principio a fin y valida los criterios de aceptación.**
