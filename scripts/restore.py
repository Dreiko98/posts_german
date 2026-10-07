import argparse
import json
import os
import tarfile
import time
from pathlib import Path, PurePosixPath
from deployment import Deployment, checksum


def restore(source, config, project, port=None):
    source = Path(source).resolve()
    config = Path(config).resolve()
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    for name in ("database.dump", "files.tar.gz", "config.env"):
        if manifest.get(name) != checksum(source / name):
            raise RuntimeError("El backup no supera la comprobación de integridad.")
    with tarfile.open(source / "files.tar.gz") as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or member.issym()
                or member.islnk()
                or not (member.isfile() or member.isdir())
            ):
                raise RuntimeError("El archivo de backup contiene rutas no permitidas.")
    if config.exists():
        raise RuntimeError(
            "No se sobrescribe una configuración existente. Elige un proyecto nuevo y una ruta .env nueva."
        )
    config.parent.mkdir(parents=True, exist_ok=True)
    restored_config = (source / "config.env").read_text(encoding="utf-8")
    if port is not None:
        if not 1 <= port <= 65535:
            raise ValueError("El puerto debe estar entre 1 y 65535.")
        lines = [
            line
            for line in restored_config.splitlines()
            if not line.startswith(("WEB_PORT=", "APP_ORIGIN=", "COOKIE_SECURE="))
        ]
        restored_config = (
            "\n".join(lines)
            + f"\nWEB_PORT={port}\nAPP_ORIGIN=http://localhost:{port}\nCOOKIE_SECURE=false\n"
        )
    config.write_text(restored_config, encoding="utf-8")
    os.chmod(config, 0o600)
    deployment = Deployment(config, project, port)
    deployment.run(["up", "-d", "db"])
    for _ in range(60):
        try:
            deployment.run(
                ["exec", "-T", "db", "pg_isready", "-U", "studio", "-d", "studio"]
            )
            break
        except Exception:
            time.sleep(1)
    count = (
        deployment.run(
            [
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "studio",
                "-d",
                "studio",
                "-Atc",
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'",
            ]
        )
        .decode()
        .strip()
    )
    if count != "0":
        raise RuntimeError(
            "La base de destino no está vacía. Se aborta sin sobrescribir datos."
        )
    deployment.run(
        [
            "exec",
            "-T",
            "db",
            "pg_restore",
            "-U",
            "studio",
            "-d",
            "studio",
            "--exit-on-error",
        ],
        input_file=source / "database.dump",
    )
    deployment.run(
        [
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "--user",
            "root",
            "api",
            "tar",
            "-xzf",
            "-",
            "-C",
            "/data",
        ],
        input_file=source / "files.tar.gz",
    )
    deployment.run(
        [
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "--user",
            "root",
            "api",
            "chown",
            "-R",
            "10001:10001",
            "/data",
        ]
    )
    deployment.run(["up", "-d"])
    return deployment


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Restaura en un proyecto nuevo, con base vacía y configuración nueva."
    )
    p.add_argument("source")
    p.add_argument("--env-file", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--port", type=int)
    a = p.parse_args()
    restore(a.source, a.env_file, a.project, a.port)
    print(
        "Restauración terminada. Verifica login, imágenes y conexiones antes de usar plataformas."
    )
