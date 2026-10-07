# Evaluador SEO propio

Referencia conceptual: [análisis SEO gratuito de Yoast](https://yoast.com/features/seo-analysis/) y [motor abierto](https://github.com/Yoast/wordpress-seo/tree/trunk/packages/yoastseo), consultados el 5 octubre 2026. El motor es GPL-3.0; esta versión utiliza una adaptación propia Python y **no incorpora ni redistribuye el motor**. El plugin usa las APIs de metadatos de Yoast gratuito; no depende de Premium ni de un plugin modificado.

Reglas `studio-seo-es-1.0.0`. Puntuación: `round(100 × suma de pesos superados aplicables / suma de pesos aplicables)`. Mismo texto/metadatos/imagen, contexto de sitio, frases usadas y reglas producen el mismo resultado. Cada resultado tiene huella y fecha; una evaluación obsoleta no se muestra como válida.

| Criterio | Peso | Regla inicial |
| --- | ---: | --- |
| Frase clave definida | 5 | No vacía. |
| Frase clave en título SEO | 12 | Coincidencia normalizada sin distinguir acentos/mayúsculas. |
| Longitud del título SEO | 8 | 25–65 caracteres. |
| Frase clave en slug | 8 | Guiones normalizados a espacios. |
| Frase clave en introducción | 10 | Primeras 100 palabras. |
| Frase clave en metadescripción | 8 | Coincidencia normalizada. |
| Longitud de metadescripción | 8 | 110–160 caracteres. |
| Encabezados | 10 | h2/h3/h4 informativo con frase clave. |
| Densidad | 10 | 0,3–3 %; ocurrencias × palabras de frase / palabras totales. |
| Desarrollo | 8 | Al menos 250 palabras, como indicador, no longitud editorial obligatoria. |
| Enlace interno | 7 | Host real de WordPress configurado. |
| Fuente externa enlazada | 6 | URL HTTP(S) en otro host. |
| Alt | 4 | Solo aplicable cuando existe imagen manual; alt no vacío. |

Cobertura: criterios aplicables / criterios definidos. Sin imagen, el score es textual y la comprobación de imagen queda pendiente. Añadir/cambiar archivo o alt modifica la huella. El score no certifica accesibilidad de URLs, fuentes, experiencia personal ni el resultado del tema WordPress.

Legibilidad se muestra aparte: porcentaje de frases de más de 25 palabras y número de párrafos. Una revisión IA separada lista problemas editoriales, afirmaciones sin fuente y experiencias personales que requieren confirmación. No crea el score técnico. Usar una frase clave ya vista genera aviso separado.

El ancho de snippets depende de fuente y dispositivo; esta versión aproxima con caracteres. No incluye la morfología/funciones lingüísticas completas de Yoast español ni equivalencia exacta de semáforos. El propietario debe revisar el resultado en WordPress y su plugin.

## Ciclo

Investigación → redacción inicial → evaluación → hasta cinco mejoras focalizadas. Termina al llegar a 70, alcanzar seis redacciones, agotar presupuesto o acumular dos rondas que no superan la mejor puntuación previa. Guarda todas las versiones y selecciona la mejor. Si no alcanza 70, queda revisión pendiente; no borra texto ni publica. Las búsquedas no se repiten por cada mejora SEO.

Los tests incluyen un texto desarrollado con metadatos/enlaces relevantes y uno de una sola palabra, comprobación de determinismo, límites de seis versiones, parada sin mejora y conservación de la mejor versión. El umbral no es una garantía SEO: las advertencias editoriales y de evidencia permanecen visibles aunque se alcance.
