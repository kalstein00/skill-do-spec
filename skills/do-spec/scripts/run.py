# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Copy this entire skill directory; no wheel installation is required."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime"))
from do_spec.cli import main

raise SystemExit(main())
