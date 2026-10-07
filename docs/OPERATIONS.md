# Operación y recuperación

Docker Compose conserva `database` y `files`. No uses `down -v` en tu instancia: elimina volúmenes. `docker compose restart` conserva datos. API ejecuta migraciones al inicio; worker arranca tras healthcheck API. Apagado ordenado con 120 segundos de gracia, sin nuevas tareas tras SIGTERM. Healthcheck worker comprueba heartbeat actualizado también durante trabajos largos.

## Backup completo

Desde el repositorio y con Docker disponible:

```bash
python scripts/backup.py /ruta/nueva/backup-2026-10-05
```

Detiene temporalmente web/API/worker, conserva PostgreSQL activo y crea dump binario consistente, original de archivos, `.env` con MASTER_KEY y manifest SHA-256. Reanuda servicios al terminar incluso ante error. El destino debe ser nuevo. Guarda el directorio cifrado fuera del servidor; la clave maestra y credenciales son sensibles y necesarias para recuperación. No publiques `.env` ni el backup. Los scripts Python funcionan en Windows y Linux.

## Restaurar sin sobrescribir una instalación

Construye las imágenes en el host y utiliza una configuración nueva y un nombre de proyecto distinto. El script Python comprueba hashes, rutas del tar y base vacía; nunca borra ni sobrescribe datos existentes.

```bash
python scripts/restore.py /ruta/backup --env-file /ruta/config-recuperada.env --project studio-recuperado --port 8081
```

La opción `--port` guarda en la configuración recuperada un puerto en loopback, APP_ORIGIN local acorde y cookies para HTTP local. Sin `--port`, detén la instancia antigua para no colisionar. Para administrar el proyecto recuperado:

```bash
docker compose --env-file /ruta/config-recuperada.env -p studio-recuperado ps
```

No se necesitan dependencias Python externas para backup/restore (`scripts/verify_restore.py` sí utiliza cryptography para sus fixtures). La restauración corrige propietario del volumen a UID 10001. Verifica login, descifrado de conexiones, imagen original y versiones antes de enviar a proveedores.

La prueba `scripts/verify_restore.py` crea dos proyectos Compose desechables, cifra una credencial de test, guarda un archivo, realiza backup/restauración, comprueba descifrado/bytes/permisos y reinicia. Resultado en `backup-test-report.json`. Detiene proyectos al acabar y conserva sus volúmenes; solo utiliza datos de pruebas, sin sobrescribir la instancia principal.

## Recuperación de cuenta y trabajos

```bash
docker compose exec api python -m app.cli reset-password --username german
```

Requiere acceso al servidor, pide contraseña y revoca sesiones. Si pierdes MASTER_KEY, restaura la copia correcta o vuelve a autorizar conexiones; la app no puede recuperar secretos cifrados con otra clave.

Un worker reiniciado recupera lease expirado y checkpoints. Un envío LinkedIn incierto no se reintenta automáticamente; revisa el perfil y registra ID. WordPress consulta la clave de correlación. Una reanudación antigua con cambios locales posteriores se bloquea para no sobrescribirlos. Cancelar detiene nuevas fases, pero no revierte llamadas externas ya iniciadas.

## Si se utiliza un dominio en el futuro

Configura HTTPS en un proxy explícitamente autorizado, APP_ORIGIN exacto y COOKIE_SECURE=true. Conserva servicios internos sin puertos, contraseña fuerte y backups cifrados. Actualiza callback OAuth a ese origen, revisa política de proxy y no confíes en encabezados enviados directamente por Internet. Este desarrollo no configura dominio, router ni túneles.

## Mantenimiento

Dependencias directas fijadas, lock completo Python y package-lock npm. Revisa fuentes oficiales antes de actualizar modelos/tarifas o LinkedIn-Version. Actualiza migraciones de forma aditiva, respalda antes y verifica el restore. Los tests solo admiten bases `*_test`; nunca les pases la DATABASE_URL de producción. Los proveedores se simulan exclusivamente en `backend/tests`, excluido de la imagen de producción.
