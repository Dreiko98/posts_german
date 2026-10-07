import json
import secrets
import time
import uuid
from cryptography.fernet import Fernet
from deployment import Deployment, ROOT
from backup import backup
from restore import restore

local = ROOT / ".local"
local.mkdir(exist_ok=True)
key = uuid.uuid4().hex[:8]
config = local / f"backup-source-{key}.env"
config.write_text(
    "POSTGRES_PASSWORD="
    + secrets.token_hex(20)
    + "\nMASTER_KEY="
    + Fernet.generate_key().decode()
    + "\nWEB_PORT=18082\nAPP_ORIGIN=http://localhost:18082\n",
    encoding="utf-8",
)
source = Deployment(config, "studio-backup-test-" + key)
print("Arrancando proyecto aislado de backup…", flush=True)
source.run(["up", "-d"])
sample = """from app.db import SessionLocal
from app.models import Connection, File
from app.security import encrypt
from app.services import current_context
from pathlib import Path
with SessionLocal() as s:
 current_context(s)
 s.add(Connection(provider='openai',config={},encrypted=encrypt({'api_key':'backup-verification-only'})))
 Path('/data/restore-verification.bin').write_bytes(b'original-persistent-file')
 s.add(File(path='/data/restore-verification.bin',mime='application/octet-stream',size=24,alt='test-file'))
 s.commit()
print('Fixture creada.')
"""
sample_file = local / "backup-fixture.py"
sample_file.write_text(sample, encoding="utf-8")
source.run(["exec", "-T", "api", "python", "-c", sample])
print("Copiando base de datos y archivos…", flush=True)
archive = backup(local / f"backup-{key}", source)
print("Restaurando en volúmenes nuevos…", flush=True)
target = restore(
    archive, local / f"backup-restored-{key}.env", "studio-restore-test-" + key, 18083
)
check = """from app.db import SessionLocal
from app.models import Connection, File, Context
from app.security import decrypt
from sqlalchemy import select
from pathlib import Path
with SessionLocal() as s:
 c=s.scalar(select(Connection).where(Connection.provider=='openai'))
 assert decrypt(c.encrypted)['api_key']=='backup-verification-only'
 f=s.scalar(select(File))
 assert Path(f.path).read_bytes()==b'original-persistent-file'
 assert s.scalar(select(Context)) is not None
 Path('/data/post-restore-write.bin').write_bytes(b'write-permissions-ok')
print('Restore verified: database, original file, decryption and write permissions.')
"""
target.run(["exec", "-T", "api", "python", "-c", check])
print("Verificando persistencia tras reinicio…", flush=True)
target.run(["restart", "api", "worker", "web"])
for _ in range(50):
    try:
        target.run(["exec", "-T", "api", "python", "-c", check])
        break
    except Exception as error:
        print(str(error)[-300:], flush=True)
        time.sleep(0.5)
else:
    raise RuntimeError("Persistence after restart failed.")
(ROOT / "docs" / "backup-test-report.json").write_text(
    json.dumps(
        {
            "passed": True,
            "checks": [
                "Consistent database and file backup",
                "Archive checksums",
                "Restoration to a fresh Compose project",
                "Original file integrity",
                "External master key decrypts credentials",
                "Restored volume writable as UID 10001",
                "Restart persistence",
            ],
            "scope": "Disposable isolated Compose projects; no user deployment data overwritten.",
        },
        indent=2,
    ),
    encoding="utf-8",
)
source.run(["down"])
target.run(["down"])
print(
    "Backup y restauración conjunta verificados; proyectos de prueba detenidos, volúmenes conservados."
)
