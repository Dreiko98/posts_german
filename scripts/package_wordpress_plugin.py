"""Build a portable plugin ZIP with one explicit top-level directory."""

from pathlib import Path
import argparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "german-studio-connector"


def build(flat=False):
    source = ROOT / "wordpress" / PLUGIN
    output = ROOT / "wordpress" / f"{PLUGIN}{'-flat' if flat else ''}.zip"
    prefix = "" if flat else f"{PLUGIN}/"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if not flat:
            directory = zipfile.ZipInfo(f"{PLUGIN}/")
            directory.create_system = 3
            directory.external_attr = (0o40755 << 16) | 0x10
            archive.writestr(directory, b"")
        for filename in (f"{PLUGIN}.php", "readme.txt"):
            entry = zipfile.ZipInfo(prefix + filename)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (source / filename).read_bytes())
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert f"{prefix}{PLUGIN}.php" in archive.namelist()
        assert not any(
            "\\" in name or f"{PLUGIN}/{PLUGIN}/" in name for name in archive.namelist()
        )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--flat", action="store_true")
    print(build(parser.parse_args().flat))
