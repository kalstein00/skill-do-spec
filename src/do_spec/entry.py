"""Absolute script entry for Dagu; does not rely on inherited PYTHONPATH."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from do_spec.cli import main
raise SystemExit(main())
