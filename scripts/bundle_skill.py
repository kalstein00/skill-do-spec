"""Refresh the portable skill from canonical sources; build a clean archive."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
skill = ROOT / "skills" / "do-spec"
target = skill / "scripts" / "runtime" / "do_spec"
target.mkdir(parents=True, exist_ok=True)
sources = {p.name: p for p in (ROOT / "src" / "do_spec").glob("*.py")}
for old in target.glob("*.py"):
    if old.name not in sources:
        old.unlink()
for name, source in sources.items():
    (target / name).write_bytes(source.read_bytes())
(ROOT / "dist").mkdir(exist_ok=True)
with zipfile.ZipFile(ROOT / "dist" / "do-spec-skill.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(skill.rglob("*")):
        if file.is_file() and file.suffix in {".py", ".md"} and "__pycache__" not in file.parts:
            archive.write(file, "do-spec/" + file.relative_to(skill).as_posix())
print("dist/do-spec-skill.zip")
