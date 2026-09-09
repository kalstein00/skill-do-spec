import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time


class Fault(Exception):
    def __init__(self, reason, detail="", code=3):
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail, self.code = reason, detail, code


def digest(value):
    data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".atomic-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        # Windows scanners/readers may temporarily deny replacing a closed file.
        # Retry only this atomic metadata operation, never the agent or ticket.
        for attempt in range(6):
            try:
                os.replace(tmp, path)
                break
            except PermissionError as error:
                if os.name != 'nt' or getattr(error, 'winerror', None) not in {5, 32, 33} or attempt == 5:
                    raise
                time.sleep(0.02 * 2**attempt)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def event(path, **fields):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"time": time.time(), **fields}, ensure_ascii=False) + "\n")
        f.flush()


def inside(root, relative):
    root = Path(root).resolve()
    lexical = root / relative
    p = (root / relative).resolve()
    if not p.is_relative_to(root) or str(p).startswith("\\\\"):
        raise Fault("UNSAFE_PATH", str(relative), 2)
    for item in [lexical, *lexical.parents]:
        if item == root:
            break
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise Fault("UNSAFE_PATH", "symlink/junction in " + str(relative), 2)
    return p


@contextlib.contextmanager
def lock(path):
    """OS exclusion, not PID/TTL leasing. Persistent owner metadata is separate."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a+b")
    if f.seek(0, 2) == 0:
        f.write(b"0")
        f.flush()
    f.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        f.close()
        raise Fault("LOCK_CONFLICT", str(path), 16) from e
    try:
        yield
    finally:
        f.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_UN)
        f.close()
