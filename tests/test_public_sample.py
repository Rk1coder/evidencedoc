import os
import time
from pathlib import Path


def test_public_example_survives_both_cache_cleanup_paths(monkeypatch, tmp_path):
    from gradio.route_utils import delete_files_created_by_app

    import app
    from evidencedoc.reports import ReportStore

    cache = tmp_path / "cache"
    monkeypatch.setenv("GRADIO_TEMP_DIR", str(cache))
    monkeypatch.setattr(app, "ROOT", tmp_path / "project")
    store = ReportStore(tmp_path / "reports", cache_root=cache)
    monkeypatch.setattr(app, "STORE", store)
    demo = app.build_app()
    dataset = next(c for c in demo.blocks.values() if type(c).__name__ == "Dataset")
    select = next(f.fn for f in demo.fns.values() if f.api_name == "load_example")

    def sample():
        return Path(select((0, dataset.samples[0]))[0]["value"]["path"])

    source = sample()
    assert source.is_file()
    os.utime(source, (time.time() - 3601, time.time() - 3601))
    store.prune()
    assert sample().is_file()
    delete_files_created_by_app(demo, age=None)
    assert sample().is_file()
    assert app.search_document(sample(), "Atlas A1 weight?")["status"] == "sources_only"


def test_sample_bytes_match_recorded_measurements_without_system_font(tmp_path):
    import subprocess
    import sys

    code = """import hashlib, sys
from pathlib import Path
original_exists = Path.exists
Path.exists = lambda p: False if str(p).endswith('/DejaVuSans.ttf') else original_exists(p)
from scripts.make_examples import create_examples
sample = create_examples(Path(sys.argv[1]))
print(hashlib.sha256(sample.read_bytes()).hexdigest())
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path / "sample.pdf")],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert (
        result.stdout.strip() == "523414900189612738f9d5d91c2849e05b8cfb82b08c3cee2b93e6ae85e3696b"
    )
