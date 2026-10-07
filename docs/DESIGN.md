# Sistema visual

Referencia inspeccionada el **5 octubre 2026**: [germanmallo.com](https://germanmallo.com/) y [blog](https://germanmallo.com/blog/), en 1440×1000 y 390×844. `reference/` conserva capturas y estilos computados. Se verificaron fondo `rgb(18,18,18)`, GeneralSans, tipografía amplia, superficies oscuras, grises y verde. No se han copiado hojas del tema ni recursos decorativos del servidor.

| Token | Valor | Procedencia/adaptación |
| --- | --- | --- |
| Fondo / profundidad | #121212 / #0F0F0F | Referencia de la web. |
| Superficie / tarjeta | #1C1C1C / #151918 | Referencia aplicada a formularios/listados. |
| Acento | #00FF85 | Marca, foco, acción principal y progreso. Texto oscuro sobre botón verde. |
| Texto / secundario | #F5F7F6 / #C6CECA | Blanco/gris de referencia. |
| Texto auxiliar | #A8B4AD | Adaptación para contraste en superficies. |
| Bordes | blanco al 9/16 % | Líneas finas de referencia. |
| Radios | 5 / 8 / 14 px | Escala derivada del tema. |
| Tipografía | Manrope local, Segoe UI/Arial | Sustitución de General Sans: no se ha redistribuido sin comprobar derechos de su archivo. Manrope se empaqueta desde @fontsource, licencia OFL, sin hotlinks. |
| Transición | 255 ms | Referencia; se anula con reduced-motion. |
| Espaciado | Base 8 px; paneles 20–28; página 22–45 | Adaptación a herramienta diaria. |
| Aviso/error | #FFD08A / #FF9B9B | Adaptación con texto/icono, nunca solo color. |

Los tokens se centralizan en `frontend/src/styles.css`. Los grandes encabezados de la web se reducen en el editor. Navegación de tres áreas, tarjetas con enfoque y acciones, metadatos junto al texto y panel SEO separado. Imágenes manuales conservan su proporción. Formularios, diálogos nativos, selectores, pestañas y notificaciones comparten superficies y bordes. Foco visible y teclado, `dialog` con Escape/trampa nativa de foco, labels de campos y nombres accesibles en acciones con iconos.

Capturas de la app en `screenshots/`: login, Ideas vacío y con propuestas, Publicaciones, editor, Ajustes, conexiones y errores. Hay variantes desktop/mobile de pantallas principales. **Todas las capturas con datos llevan marca de entorno de pruebas y IA simulada**; esos registros no están en la instancia de producción.

La prueba E2E verifica ausencia de overflow horizontal a 390 px, edición/guardado, modales y recorridos funcionales; revisión visual realizada sobre referencia, login, Ideas, Publicaciones, editor, Ajustes y conexiones. El cuerpo editable usa 16 px en escritorio/14 px móvil; advertencias y estados incluyen texto. No se utiliza una landing comercial, identidad azul/púrpura, esferas ni carruseles.
