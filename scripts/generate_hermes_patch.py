"""Deprecated unsafe generator: verify the pinned patch instead of overwriting it."""
from pathlib import Path
from patch_core import apply
if __name__ == '__main__':
    baseline=Path(__file__).resolve().parents[1]/'patches/hermes/baseline'
    raise SystemExit(0 if apply(baseline,'hermes',True) else 1)
