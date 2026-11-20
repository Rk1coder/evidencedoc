import json
import os
import time


def test_invalid_upload_clears_preview_and_download():
    from app import analyze

    answer, evidence, gallery, download, status = analyze(None, "Atlas ağırlığı?", "hybrid")
    assert not gallery
    assert download is None
    assert not evidence
    assert status.startswith("Error")
    assert "PDF" in answer


def test_gradio_string_path_source_browsing_is_not_model_output(make_pdf):
    from app import browse_sources

    answer, evidence, gallery, report_file, status = browse_sources(
        str(make_pdf()), "Atlas ağırlığı?"
    )
    report = json.loads(open(report_file).read())
    assert report["status"] == "sources_only"
    assert report["model_called"] is False
    assert len(gallery) == len(report["retrieved_pages"])
    assert "Sources" in status
    assert "model" in answer


def test_report_store_expires_and_bounds_files(tmp_path):
    from evidencedoc.reports import ReportStore

    store = ReportStore(tmp_path, max_files=2, ttl_seconds=10)
    first = store.write({"answer": "old"})
    os.utime(first, (time.time() - 20, time.time() - 20))
    second = store.write({"answer": "new"})
    assert not os.path.exists(first)
    assert json.load(open(second))["answer"] == "new"
    store.write({"answer": "third"})
    last = store.write({"answer": "fourth"})
    assert len(list(tmp_path.glob("*.json"))) == 2
    assert json.load(open(last))["answer"] == "fourth"


def test_readable_model_error_clears_old_result(monkeypatch, make_pdf):
    import app

    def unavailable(*args, **kwargs):
        raise RuntimeError("Model unavailable")

    monkeypatch.setattr(app, "answer_document", unavailable)
    answer, evidence, gallery, download, status = app.analyze(
        str(make_pdf()), "Atlas ağırlığı?", "hybrid"
    )
    assert "Model" in answer
    assert evidence == "" and gallery == [] and download is None
    assert status.startswith("Error")


def test_app_constructs_registered_answer_and_search_endpoints():
    from app import build_app

    demo = build_app()
    api_names = {dependency.get("api_name") for dependency in demo.config["dependencies"]}
    assert {"answer", "search"} <= api_names


def test_expired_reports_are_removed_without_new_report(tmp_path):
    from evidencedoc.reports import ReportStore

    store = ReportStore(tmp_path, ttl_seconds=10)
    path = store.write({"answer": "expires"})
    os.utime(path, (time.time() - 20, time.time() - 20))
    store.prune()
    assert not os.path.exists(path)


def test_restart_cleans_expired_reports_and_cache_copies(tmp_path):
    from evidencedoc.reports import ReportStore

    root = tmp_path / "reports"
    cache = tmp_path / "gradio" / "hash"
    cache.mkdir(parents=True)
    first = ReportStore(root, ttl_seconds=10)
    report = first.write({"answer": "old"})
    cached = cache / "old.json"
    cached.write_text("old")
    for p in (report, cached):
        os.utime(p, (time.time() - 20, time.time() - 20))
    ReportStore(root, cache_root=cache.parent, ttl_seconds=10)
    assert not os.path.exists(report)
    assert not cached.exists()
