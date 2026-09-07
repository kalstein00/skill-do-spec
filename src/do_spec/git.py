import os
from pathlib import Path
import subprocess
from .core import Fault, digest, inside
from .process import clean_env


def git(repo, *args, input=None):
    p = subprocess.run(["git", "-C", str(repo), *args], input=input, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=30, env=clean_env())
    if p.returncode:
        raise Fault("GIT_ERROR", p.stderr.decode("utf-8", "replace"), 13)
    return p.stdout.decode("utf-8", "strict").strip()


def head(repo):
    return git(repo, "rev-parse", "HEAD")


def common(repo):
    return Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()


def changes(repo):
    tracked = git(repo, "diff", "--name-only", "-z", "HEAD").split("\0")
    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return sorted(set(x for x in tracked + untracked if x))


def fingerprint(repo):
    paths = git(repo, "ls-files", "-z").split("\0") + git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    result = {}
    for path in sorted(set(p for p in paths if p)):
        p = inside(repo, path)
        if p.is_symlink():
            raise Fault("UNSAFE_PATH", path)
        result[path] = digest(p.read_bytes()) if p.is_file() else None
    return digest(result)


def check_head(repo, expected, branch):
    if head(repo) != expected or git(repo, "branch", "--show-current") != branch:
        raise Fault("UNEXPECTED_GIT_CHANGE", "HEAD or branch changed; preserved for reconciliation", 13)


def validate_paths(repo, allowed, protected):
    paths = changes(repo)
    for name in paths:
        p = inside(repo, name)
        if p.is_symlink() or not any(name == x or name.startswith(x.rstrip("/") + "/") for x in allowed):
            raise Fault("CHANGE_OUTSIDE_SCOPE", name, 13)
        if any(name == x or name.startswith(x.rstrip("/") + "/") for x in protected) or Path(name).name in {".env", "credentials.json"}:
            raise Fault("PROTECTED_PATH", name, 13)
    return paths
