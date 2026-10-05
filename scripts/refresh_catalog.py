"""Paleidžia viso katalogo nuskaitymą be Streamlit (naudoja GitHub Actions kasdien).
Naudojimas: python scripts/refresh_catalog.py [--resume]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from radar import catalog as cat  # noqa: E402

if __name__ == "__main__":
    new, msg, lvl = cat.update_catalog(progress=lambda s: print(f"\r{s['fetched']} puslapių, {s['products']} produktų, eilėje {s['queued']}", end=""),
                                        resume="--resume" in sys.argv)
    print("\n" + msg)
    sys.exit(0 if lvl in ("ok", "warn") else 1)
