"""Evidence collection only until a real Cline invocation is certified."""
from pathlib import Path
import platform
from .core import digest
from .process import run


def inspect(executable, directory):
    path = Path(executable).resolve()
    directory = Path(directory)
    records = {}
    for name, argv in [("version", [str(path), "--version"]), ("help", [str(path), "--help"])]:
        result = run(argv, directory, directory / name, timeout=10)
        records[name] = {"outcome": result["outcome"], "exit_code": result["exit_code"],
                         "output_hash": digest(Path(str(directory / name) + ".stdout.log").read_bytes())}
    return {"runtime": "cline", "status": "UNVERIFIED", "os": platform.platform(), "executable": str(path),
            "executable_hash": digest(path.read_bytes()), "observations": records,
            "missing": ["authorized noninteractive completion smoke", "fresh session semantics", "approval preservation", "process-tree cancellation", "rules/skills discovery"]}
