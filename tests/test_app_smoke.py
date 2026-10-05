import sys, runpy, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import fake_streamlit
fake_streamlit.install()


def test_app_runs_without_catalog(tmp_path, monkeypatch=None):
    os.environ["PROTUOLIUKAS_DATA_DIR"] = str(tmp_path)
    os.environ["RADAR_TODAY"] = "2026-10-04"
    import radar.catalog as c
    c.DATA_DIR = tmp_path; c.CATALOG_PATH = tmp_path / "catalog.json"
    # nekviesti realaus tinklo: pirmo nuskaitymo imitacija
    c.update_catalog = lambda **k: (c.empty_catalog(), "test", "warn")
    runpy.run_path(str(ROOT / "streamlit_app.py"))


if __name__ == "__main__":
    import tempfile
    test_app_runs_without_catalog(Path(tempfile.mkdtemp())); print("APP OK")
