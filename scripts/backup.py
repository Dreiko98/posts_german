import argparse
import json
import os
from pathlib import Path
from deployment import Deployment, ROOT, checksum


def backup(destination, deployment):
    target = Path(destination).resolve()
    target.mkdir(parents=True, exist_ok=False)
    os.chmod(target, 0o700)
    try:
        deployment.run(["stop", "web", "api", "worker"])
        deployment.run(
            ["exec", "-T", "db", "pg_dump", "-U", "studio", "-d", "studio", "-Fc"],
            output=target / "database.dump",
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
                "-czf",
                "-",
                "-C",
                "/data",
                ".",
            ],
            output=target / "files.tar.gz",
        )
        (target / "config.env").write_bytes(deployment.config.read_bytes())
        os.chmod(target / "config.env", 0o600)
        manifest = {
            name: checksum(target / name)
            for name in ("database.dump", "files.tar.gz", "config.env")
        }
        (target / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
    finally:
        deployment.run(["start", "api", "worker", "web"])
    return target


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Backup coherente de PostgreSQL, archivos y clave externa. Se detienen temporalmente los escritores."
    )
    p.add_argument("destination")
    p.add_argument("--env-file", default=str(ROOT / ".env"))
    p.add_argument("--project", default="german-content-studio")
    a = p.parse_args()
    backup(a.destination, Deployment(a.env_file, a.project))
    print(
        "Backup completo. Guarda la carpeta cifrada y fuera del servidor; incluye la clave maestra."
    )
