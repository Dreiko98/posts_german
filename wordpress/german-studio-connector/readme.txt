=== German Studio Connector ===
Requires at least: 6.6
Requires PHP: 8.1
Stable tag: 1.0.0
License: GPLv2 or later

Instala la carpeta en wp-content/plugins y actívala. Requiere Yoast SEO gratuito para guardar metadatos SEO.
Usa HTTPS y una contraseña de aplicación de un usuario con capacidad edit_posts/edit_post.
No expone escritura arbitraria de metadatos ni publica artículos. GET /health informa de la versión de Yoast.
Actualiza sustituyendo los archivos. Desactivar conserva entradas, metadatos y tabla de correlación.
No se borra la tabla al desinstalar: evita perder correlaciones y duplicar borradores en futuras reinstalaciones.
Si eliminas manualmente la tabla, conserva primero backup y _gstudio_request_key en postmeta.
La reconciliación presupone tablas InnoDB para atomicidad; comprueba el motor de wp_posts y wp_postmeta.
