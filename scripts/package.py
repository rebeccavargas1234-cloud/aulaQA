"""Empacota somente os arquivos da aplicação, sem segredos ou ambiente local."""
import hashlib
import os
from pathlib import Path
import zipfile


def build_package():
    root = Path(__file__).resolve().parents[1]
    output = root / "dist"
    output.mkdir(exist_ok=True)
    archive = output / "petshop.zip"
    files = [root / name for name in (
        "app.py", "requirements.txt", "requirements-dev.txt", "pytest.ini",
        "README.md", "render.yaml", "render-homolog.yaml",
    )]
    for directory in ("templates", "static", "tests", "scripts"):
        files.extend(path for path in (root / directory).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts
                     and path.suffix != ".pyc")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for path in sorted(files):
            package.write(path, path.relative_to(root).as_posix())
        package.writestr("COMMIT.txt", os.environ.get("GITHUB_SHA", "local") + "\n")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "petshop.zip.sha256").write_text(
        f"{digest}  petshop.zip\n", encoding="utf-8")
    print(f"Pacote gerado: {archive.name} ({len(files)} arquivos + COMMIT.txt)")
    return archive


if __name__ == "__main__":
    build_package()
