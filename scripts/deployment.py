import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Deployment:
    def __init__(self, config, project="german-content-studio", port=None):
        self.config = Path(config).resolve()
        self.project = project
        self.env = dict(os.environ)
        if port:
            self.env["WEB_PORT"] = str(port)
            self.env["APP_ORIGIN"] = f"http://localhost:{port}"
        self.command = [
            "docker",
            "compose",
            "--project-directory",
            str(ROOT),
            "--env-file",
            str(self.config),
            "-f",
            str(ROOT / "compose.yaml"),
            "-p",
            project,
        ]

    def run(self, args, output=None, input_file=None):
        with (
            open(input_file, "rb")
            if input_file
            else __import__("contextlib").nullcontext(None) as source
        ):
            if output:
                with open(output, "wb") as target:
                    subprocess.run(
                        self.command + args,
                        env=self.env,
                        check=True,
                        stdin=source,
                        stdout=target,
                        stderr=subprocess.PIPE,
                    )
                return b""
            result = subprocess.run(
                self.command + args,
                env=self.env,
                stdin=source,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode:
                message = result.stderr.decode(errors="replace")[-3000:]
                for line in self.config.read_text(encoding="utf-8").splitlines():
                    if "=" in line:
                        key, value = line.split("=", 1)
                        if key in ("POSTGRES_PASSWORD", "MASTER_KEY") and value:
                            message = message.replace(value, "[REDACTED]")
                raise RuntimeError("Docker Compose: " + message)
            return result.stdout


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
