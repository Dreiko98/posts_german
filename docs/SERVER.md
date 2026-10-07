# Estudio en mallocenter

Desplegado el 7 de octubre de 2026 por SSH, con Docker Compose.

- Servidor: `germanmallo@mallocenter`.
- Proyecto Docker: `german-content-studio` (web, api, worker y db).
- Directorio estable: `/home/germanmallo/apps/german-content-studio/current`.
- Versión inicial: `releases/20261007T101634Z`.
- Web del servidor: `127.0.0.1:8090`.
- Dirección de uso desde el PC: `http://localhost:8080`, mediante el túnel SSH.
- Los contenedores arrancan automáticamente cuando Docker arranca.

## Abrir desde el PC

El PC necesita acceso SSH a mallocenter por Tailscale. Ejecuta:

```powershell
ssh -N -L 127.0.0.1:8080:127.0.0.1:8090 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 germanmallo@mallocenter
```

Mantén la terminal abierta y visita `http://localhost:8080`. También puedes ejecutar `Abrir-estudio-servidor.ps1` desde la carpeta del proyecto. Tailscale puede solicitar una comprobación de identidad al conectar.

Conservas el usuario y la contraseña existentes. Se han migrado los artículos, ideas, versiones, estadísticas y credenciales cifradas. El callback de LinkedIn sigue siendo `http://localhost:8080/api/oauth/linkedin/callback`.

El estudio Docker del PC permanece detenido para evitar dos copias activas. Los demás servicios del servidor conservan sus puertos. El estudio del servidor escucha únicamente en loopback; este despliegue no configura acceso público, Cloudflare ni el router.

## Administrar en el servidor

```bash
ssh germanmallo@mallocenter
cd /home/germanmallo/apps/german-content-studio/current
docker compose ps
docker compose logs --tail=100 api worker
docker compose restart api worker web
```

## Copias y recuperación

La copia inicial se conserva en el servidor en `/home/germanmallo/backups/german-content-studio/20261007T101634Z/backup`, y en el PC en `.local/studio-backup-20261007T101634Z`. Incluye la configuración y la clave maestra: guarda estos archivos de forma privada.

Para hacer una nueva copia coherente, dentro de `current`:

```bash
python3 scripts/backup.py "/home/germanmallo/backups/german-content-studio/manual-$(date -u +%Y%m%dT%H%M%SZ)"
```

Este comando detiene temporalmente web, api y worker, y los vuelve a arrancar. No hay copias programadas configuradas. Conserva otra copia fuera del servidor. La restauración exige una base vacía y una configuración nueva; consulta `scripts/restore.py --help` y la documentación de recuperación del proyecto.

Para volver a la copia del PC: detén el estudio del servidor (`docker compose stop` dentro de `current`), cierra el túnel SSH y ejecuta `docker compose start` en `D:\Escritorio\posts_german`. La copia del PC contiene los datos del momento de la migración; no incluye cambios posteriores hechos en el servidor.

## Comprobaciones del despliegue

Se verificaron 75 publicaciones, 77 versiones, 997 filas analíticas, una idea, un usuario y seis conexiones. Las seis conexiones superaron una comprobación desde el servidor, sin generar contenido ni publicar en las plataformas. Se comprobó el acceso web por el túnel y la respuesta de salud de la API.
