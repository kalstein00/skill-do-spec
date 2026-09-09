"""Refresh the portable skill from canonical sources; build a clean archive."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
skill = ROOT / "skills" / "do-spec"
parser = argparse.ArgumentParser()
parser.add_argument('--with-dagu', action='store_true', help='Prepare Windows/Linux amd64 binaries inside the skill')
args = parser.parse_args()
if args.with_dagu:
    sys.path.insert(0, str(ROOT / 'src'))
    from do_spec.bootstrap import ARCHIVES
    from do_spec.engine import PIN
    home = skill / 'tools' / 'dagu' / PIN
    home.mkdir(parents=True, exist_ok=True)
    manifest = {'version': PIN, 'archives': {}, 'binaries': {}, 'source_url': f'https://github.com/dagucloud/dagu/tree/v{PIN}'}
    for system, (flavor, expected) in ARCHIVES.items():
        archive = ROOT / '.tools' / ('dagu.tar.gz' if system == 'Windows' else 'dagu-linux.tar.gz')
        url = f'https://github.com/dagucloud/dagu/releases/download/v{PIN}/dagu_{PIN}_{flavor}_amd64.tar.gz'
        if not archive.exists():
            archive.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=60) as response:
                archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Archive hash mismatch: ' + flavor)
        name = 'dagu.exe' if system == 'Windows' else 'dagu'
        folder = home / (flavor + '-amd64')
        folder.mkdir(exist_ok=True)
        with tarfile.open(archive) as package:
            for wanted in (name, 'LICENSE'):
                matches = [m for m in package.getmembers() if m.isfile() and Path(m.name).name == wanted]
                if len(matches) != 1:
                    raise RuntimeError('Missing or ambiguous archive member: ' + wanted)
                (folder / wanted).write_bytes(package.extractfile(matches[0]).read())
        manifest['archives'][flavor] = {'url': url, 'sha256': expected}
        manifest['binaries'][(folder / name).relative_to(home).as_posix()] = hashlib.sha256((folder / name).read_bytes()).hexdigest()
    (home / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
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
        bundled_tool = file.is_relative_to(skill / 'tools' / 'dagu') and file.name in {'dagu', 'dagu.exe', 'LICENSE', 'manifest.json'}
        if file.is_file() and (file.suffix in {".py", ".md"} or bundled_tool) and "__pycache__" not in file.parts:
            name = 'do-spec/' + file.relative_to(skill).as_posix()
            if file.name == 'dagu':
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = 0o100755 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, file.read_bytes())
            else:
                archive.write(file, name)
print("dist/do-spec-skill.zip")
