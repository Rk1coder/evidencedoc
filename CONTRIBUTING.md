# Contributing

Use Python 3.12 on Linux, or a Linux container. Install `requirements-dev.txt`, run `python -m pytest -q`, and run `ruff check .` before proposing changes.

Add a regression test for changes to extraction limits, retrieval, citation validation, or error handling. Tests should exercise real parsing and retrieval; replace expensive model generation only at the model boundary. Keep inference artifacts out of commits unless they are intentional evaluation results with provenance.

Do not describe quote presence as answer correctness. Keep development measurements separate from independent evaluation, and document any change to data, prompts, model revision, or retrieval settings.
