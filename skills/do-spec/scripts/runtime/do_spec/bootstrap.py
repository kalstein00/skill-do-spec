"""Pinned, per-user Dagu cache. Never installs globally or edits PATH."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from .core import Fault, lock, read
from .engine import PIN, validate_binary

ARCHIVES = {
    "Windows": ("windows", "3e435358de147ee74ceb49d21220dc49f13325fb2e5ef2ffd130559737c61672"),
    "Linux": ("linux", "ccf33ff9d86e2463faeb7e7b30ebca82a96e8c76b6ea2e282adb506db69feb3d"),
}


def cache_home():
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else os.environ.get("XDG_CACHE_HOME")
    return (Path(base) if base else Path.home() / ".cache") / "do-spec" / "tools" / PIN


def bundled_home():
    skill = Path(__file__).resolve().parents[3]
    if (skill / 'SKILL.md').is_file() and (skill / 'scripts' / 'run.py').is_file():
        return skill / 'tools' / 'dagu' / PIN
    return None


def bundled_binary():
    home = bundled_home()
    system = platform.system()
    if home is None or system not in ARCHIVES or platform.machine().lower() not in {'amd64', 'x86_64'}:
        return None
    flavor = ARCHIVES[system][0]
    path = home / (flavor + '-amd64') / ('dagu.exe' if system == 'Windows' else 'dagu')
    archive = home / (flavor + '-amd64.zip')
    if not path.exists() and not archive.exists():
        return None
    manifest = read(home / 'manifest.json')
    expected = manifest['binaries'][path.relative_to(home).as_posix()]
    if not path.exists():
        # Extract only the requested native binary, never archive-provided paths.
        with lock(home / 'install.lock'):
            if not path.exists():
                if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['bundled_archives'][archive.name]:
                    raise Fault('DAGU_BUNDLED_ARCHIVE_HASH_MISMATCH')
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
                    candidate = Path(tmp) / path.name
                    with zipfile.ZipFile(archive) as package:
                        matches = [i for i in package.infolist() if i.filename == path.name and not i.is_dir()]
                        if len(matches) != 1 or matches[0].file_size > 256 * 1024 * 1024:
                            raise Fault('DAGU_BUNDLED_ARCHIVE_INVALID')
                        with package.open(matches[0]) as source, candidate.open('wb') as dest:
                            shutil.copyfileobj(source, dest)
                    if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
                        raise Fault('DAGU_BUNDLED_HASH_MISMATCH')
                    candidate.chmod(0o755)
                    validate_binary(str(candidate))
                    os.replace(candidate, path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise Fault('DAGU_BUNDLED_HASH_MISMATCH')
    if system == 'Linux':
        path.chmod(path.stat().st_mode | 0o100)
    validate_binary(str(path))
    return str(path)


def resolve(explicit=None):
    selected = explicit or os.environ.get("DO_SPEC_DAGU")
    if selected:
        path = str(Path(selected).resolve())
        validate_binary(path)
        return path
    bundled = bundled_binary()
    if bundled:
        return bundled
    selected = shutil.which('dagu')
    if selected:
        validate_binary(selected)
        return str(Path(selected).resolve())
    system = platform.system()
    if system not in ARCHIVES or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise Fault("DAGU_PLATFORM_UNVERIFIED", "provide --dagu for a separately verified Dagu 2.11.2 binary")
    home = cache_home()
    home.mkdir(parents=True, exist_ok=True)
    name = "dagu.exe" if system == "Windows" else "dagu"
    path = home / name
    flavor, expected = ARCHIVES[system]
    with lock(home / "install.lock"):
        if not path.exists():
            url = f"https://github.com/dagucloud/dagu/releases/download/v{PIN}/dagu_{PIN}_{flavor}_amd64.tar.gz"
            with tempfile.TemporaryDirectory(dir=home) as tmp:
                archive = Path(tmp) / "dagu.tar.gz"
                try:
                    with urllib.request.urlopen(url, timeout=60) as response, archive.open("wb") as dest:
                        total = 0
                        while chunk := response.read(1024 * 1024):
                            total += len(chunk)
                            if total > 256 * 1024 * 1024:
                                raise Fault("DAGU_DOWNLOAD_TOO_LARGE")
                            dest.write(chunk)
                except OSError as error:
                    raise Fault("DAGU_DOWNLOAD_FAILED", "use --dagu for an offline installation") from error
                if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
                    raise Fault("DAGU_DOWNLOAD_HASH_MISMATCH")
                with tarfile.open(archive) as package:
                    # Never extract archive paths or links onto the filesystem.
                    matches = [m for m in package.getmembers() if m.isfile() and Path(m.name).name == name]
                    if len(matches) != 1:
                        raise Fault("DAGU_ARCHIVE_INVALID")
                    candidate = Path(tmp) / name
                    with package.extractfile(matches[0]) as source, candidate.open("wb") as dest:
                        shutil.copyfileobj(source, dest)
                    candidate.chmod(0o755)
                    validate_binary(str(candidate))
                    os.replace(candidate, path)
        validate_binary(str(path))
    return str(path)
