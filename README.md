# Germán Content Studio

Plataforma editorial privada en español: **Ideas**, **Publicaciones** y **Ajustes**. React/TypeScript, FastAPI, PostgreSQL y un worker Python independiente. La generación es bajo demanda; WordPress recibe borradores y LinkedIn solo se publica mediante una acción expresa tras comprobar el artículo público.

## Arrancar

Necesitas Docker Engine con Compose v2. En el servidor Linux, dentro del repositorio:

```bash
cp .env.example .env
```

Edita `.env`: establece una contraseña aleatoria de PostgreSQL y una clave Fernet nueva. Puedes obtener la clave sin instalar Python en el host:

```bash
docker compose build api web
docker compose run --rm --no-deps api python -m app.cli generate-key
docker compose up -d
docker compose exec api python -m app.cli create-user --username german
```

El comando de creación pide la contraseña interactivamente (mínimo 12 caracteres); no hay usuario ni contraseña activos por defecto. Introduce primero los valores de `.env` antes de ejecutar Compose: la clave temporal de ejemplo permite construir, pero debe sustituirse por la clave generada antes de configurar conexiones.

Con Python y `cryptography` instalados, `python scripts/setup_env.py` crea `.env` con valores aleatorios sin sobrescribir un archivo existente. En este workspace ya se ha generado un `.env` local ignorado por Git, pero **no se ha creado un usuario de producción**.

Abre `http://localhost:8080`. Solo `web` publica un puerto, ligado a `127.0.0.1`; API, worker y PostgreSQL son internos. Las migraciones se ejecutan al arrancar la API. Comprueba los cuatro servicios con `docker compose ps`.

Para acceder al servidor doméstico a través de tu SSH/Tailscale existente:

```bash
ssh -N -L 8080:127.0.0.1:8080 usuario@servidor-tailscale
```

Abre la misma URL local. `APP_ORIGIN` debe coincidir exactamente con el origen del navegador: `localhost` y `127.0.0.1` son distintos. No se ha configurado Tailscale, SSH, el router ni exposición pública.

## Configurar y trabajar

1. Completa **Ajustes → Mi contexto**. Distingue hechos confirmados, proyectos actuales y ejemplos históricos de estilo.
2. Guarda las claves de OpenAI o Anthropic en **Conexiones** y pulsa **Comprobar**. La autenticación de un proveedor no demuestra saldo ni acceso a todas las herramientas.
3. Configura WordPress con HTTPS y una contraseña de aplicación. Instala el [conector incluido](wordpress/german-studio-connector/readme.txt) junto a Yoast SEO gratuito y sincroniza el blog.
4. Configura GA4 y Search Console con cuentas de servicio de lectura y actualiza los periodos que quieras comparar.
5. Selecciona proveedor/modelo en la barra superior; consulta la ficha de capacidades, precios y estimación. La selección y límites quedan fijados para cada trabajo.
6. Crea una idea mediante una sola intención o genera un lote. Selecciona, descarta, edita o prepara una publicación.
7. Revisa el artículo y LinkedIn, guarda versiones, añade una imagen/alt y utiliza **Reevaluar** o **Corregir problemas** según necesites.
8. Envía el borrador a WordPress; revisa y publica allí. Después comprueba la publicación y, cuando la adaptación esté vigente, pulsa **Publicar en LinkedIn**.

El worker conserva checkpoints aunque cierres el navegador. Los envíos parciales e inciertos se muestran expresamente. La app nunca inventa métricas cuando no existen conexiones o datos.

## Documentación y verificaciones

- [Uso, estados y límites](docs/USAGE.md)
- [Arquitectura, modelo y seguridad](docs/ARCHITECTURE.md)
- [Integraciones y fuentes oficiales](docs/INTEGRATIONS.md)
- [Fórmula SEO y ciclo de mejoras](docs/SEO.md)
- [Modelos y costes](docs/MODELS.md)
- [Diseño y capturas](docs/DESIGN.md)
- [Backups, restauración y mantenimiento](docs/OPERATIONS.md)
- [Pruebas y matriz de aceptación](docs/VALIDATION.md)
- [Especificación original](docs/specification.md)

Los contratos OpenAPI están disponibles, con sesión, en `/api/openapi.json`. No se publican secretos ni un registro público.

Las APIs de proveedores, OAuth de LinkedIn y las propiedades Google del propietario están implementadas y probadas con dobles; requieren sus credenciales/permisos para verificar conexiones reales. El plugin se ha probado en un WordPress desechable con Yoast real. No se ha modificado germanmallo.com ni publicado en LinkedIn.
