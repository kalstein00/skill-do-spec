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
parser.add_argument('--with-dagu', action='store_true', help='Prepare Git-sized Windows/Linux amd64 ZIPs inside the skill')
args = parser.parse_args()
if args.with_dagu:
    sys.path.insert(0, str(ROOT / 'src'))
    from do_spec.bootstrap import ARCHIVES
    from do_spec.engine import PIN
    home = skill / 'tools' / 'dagu' / PIN
    home.mkdir(parents=True, exist_ok=True)
    manifest = {'version': PIN, 'archives': {}, 'binaries': {}, 'bundled_archives': {}, 'source_url': f'https://github.com/dagucloud/dagu/tree/v{PIN}'}
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
        payloads = {}
        with tarfile.open(archive) as package:
            for wanted in (name, 'LICENSE'):
                matches = [m for m in package.getmembers() if m.isfile() and Path(m.name).name == wanted]
                if len(matches) != 1:
                    raise RuntimeError('Missing or ambiguous archive member: ' + wanted)
                payloads[wanted] = package.extractfile(matches[0]).read()
        packed = home / (flavor + '-amd64.zip')
        with zipfile.ZipFile(packed, 'w', zipfile.ZIP_DEFLATED) as output:
            for filename, data in payloads.items():
                info = zipfile.ZipInfo(filename)
                info.create_system = 3
                info.external_attr = (0o100755 if filename == name else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                output.writestr(info, data)
        if packed.stat().st_size > 100 * 1024 * 1024:
            raise RuntimeError('Dagu ZIP exceeds regular GitHub file limit')
        (home / 'LICENSE').write_bytes(payloads['LICENSE'])
        manifest['archives'][flavor] = {'url': url, 'sha256': expected}
        manifest['binaries'][flavor + '-amd64/' + name] = hashlib.sha256(payloads[name]).hexdigest()
        manifest['bundled_archives'][packed.name] = hashlib.sha256(packed.read_bytes()).hexdigest()
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
        bundled_tool = file.parent == skill / 'tools' / 'dagu' / '2.11.2' and file.name in {'windows-amd64.zip', 'linux-amd64.zip', 'LICENSE', 'manifest.json'}
        if file.is_file() and (file.suffix in {".py", ".md"} or bundled_tool) and "__pycache__" not in file.parts:
            name = 'do-spec/' + file.relative_to(skill).as_posix()
            archive.write(file, name, compress_type=zipfile.ZIP_STORED if file.suffix == '.zip' else zipfile.ZIP_DEFLATED)
print("dist/do-spec-skill.zip")
