# Uso y estados

**Crear idea manualmente** desarrolla una intención con IA; no es un formulario que solo guarde un título. **Generar con IA** propone hasta la cantidad solicitada (máximo 20 configurable); rechaza duplicados semánticos relevantes y explica propuestas faltantes. La investigación es una fase real con herramienta del proveedor. Si no se ejecuta, devuelve resultados vacíos, parciales o error, queda incompleta y no se redactan noticias a partir de conocimiento previo como si se hubieran buscado.

Estados de idea: pendiente → seleccionada o descartada; recuperar vuelve a pendiente y conserva el motivo anterior. Utilizada se asigna al comprobar un artículo WordPress publicado. Una publicación local no cambia la idea a utilizada. Crear publicación dos veces abre la misma, protegido también por restricción de base de datos.

Una publicación tiene dos canales. WordPress puede estar local/draft/pending/future/private/publish/parcial/incierto; LinkedIn permanece local hasta envío explícito, publicado o incierto. Un artículo histórico puede carecer de idea. El enlace definitivo se lee de WordPress, no se adivina.

Guardar crea una versión significativa, sin una por pulsación. Cambiar texto/metadatos/imagen invalida el análisis anterior; cambiar WordPress marca LinkedIn pendiente. Guardar LinkedIn después de revisar lo vincula a la versión actual. Recuperar una versión antigua conserva el historial y comprueba si su versión base sigue vigente.

**Reevaluar** ejecuta reglas técnicas, sin modificar el texto ni hacer una llamada IA. **Corregir problemas** genera una nueva versión y revisión editorial. Las instrucciones que piden actualidad o nueva verificación activan investigación. **Actualizar adaptación** guarda una nueva versión LinkedIn y conserva ediciones previas como referencia. La preparación inicial limita el ciclo SEO a seis redacciones; nuevas correcciones explícitas del propietario son operaciones independientes.

**Enviar borrador** solo crea draft. **Actualizar borrador** comprueba estado, fecha y huella remotos. Si cambia el remoto, importa su versión mediante la acción explícita; nunca se sobreescribe silenciosamente ni se devuelve un artículo publicado a draft. Contenido, SEO e imagen tienen confirmaciones independientes y se pueden reparar sin crear un artículo nuevo.

**Comprobar publicación** consulta WordPress y comprueba la URL sin autenticación, con identidad de contenido y canonical. Un resultado HTTP 200 de login o de otra página no habilita LinkedIn. El worker repite el control inmediatamente antes de publicar; el estado mostrado en UI no sustituye ese control.

Si un envío LinkedIn queda incierto, revisa el perfil y registra el ID encontrado. La app no permite reanudar automáticamente ese trabajo; no promete entrega exactamente una vez. Si no puedes confirmar el resultado, mantenlo incierto. Una imagen con respuesta perdida requiere registrar su ID de Medios verificado antes de continuar.

En **Ajustes → Conexiones**, actualizar métricas consulta solo los periodos elegidos. Los informes se distinguen entre disponibles, parciales y sin datos. Los CTR y posiciones se agregan por sus denominadores; GA4 no se mezcla con clics de Search Console. Los recuentos por página no son sesiones únicas del sitio. Las señales son descriptivas, sin garantías de posicionamiento ni causalidad.

La importación manual de contexto acepta TXT/Markdown UTF-8 hasta 2 MB. Para PDF/Word copia o exporta el texto; no se interpreta un documento como instrucciones. Los ejemplos de estilo son históricos y no reemplazan la ficha profesional actual.
