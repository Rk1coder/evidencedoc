---
title: EvidenceDoc
emoji: 📄
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 6.11.0
python_version: "3.12"
app_file: app.py
license: apache-2.0
short_description: PDF question answering with checked quotes and page evidence.
models:
  - Qwen/Qwen3-VL-2B-Instruct
tags:
  - document-question-answering
  - vision-language-model
  - retrieval-augmented-generation
---

# EvidenceDoc

[![Tests](https://github.com/Rk1coder/evidencedoc/actions/workflows/test.yml/badge.svg)](https://github.com/Rk1coder/evidencedoc/actions/workflows/test.yml)

**Ask your documents. Inspect the evidence behind every answer.**

[Live demo](https://huggingface.co/spaces/rabitrabi/evidencedoc) · [Architecture](docs/ARCHITECTURE.md) · [Evaluation](docs/EVALUATION.md)

EvidenceDoc answers questions about technical reports and product catalogues using a local vision-language model. It retrieves relevant PDF pages, compares text-only and hybrid inference, and checks that every proposed quote exists in its cited source.

The interface, system messages, and generated answers are in English. Source quotes remain in the document's original language. Lexical retrieval supports English and Turkish; use the document's language when asking a question.

## Capabilities

- **Inspectable answers:** physical page numbers, source quotes, highlighted previews, and downloadable JSON.
- **Real local inference:** a pinned revision of `Qwen/Qwen3-VL-2B-Instruct`; no inference API key required.
- **Controlled comparison:** the same model and retrieved text, with or without page images.
- **Lightweight source search:** browse relevant pages without loading the model.
- **Explicit failure states:** unsupported documents, invalid model JSON, and unmatched quotes do not produce accepted answers.
- **Bounded processing:** upload/page limits, a resource-limited PDF extraction worker, serialized model inference, and expiring temporary files.

**A matched citation is not a correctness guarantee.** It confirms that the quoted text occurs on the cited page. It does not establish that the quote logically supports the answer. Review the source page.

## Run locally

Linux and Python 3.12 are the verified environment. The default requirements install CPU PyTorch.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:7860**. The fictional sample PDF is generated automatically on first startup.

The first answer downloads the model weights and loads them into memory. CPU latency and RAM requirements depend on the machine. Source search works without downloading the model. No paid service or GPU is provisioned by the application.

| Variable | Purpose |
|---|---|
| `HOST` | Bind address; defaults to `127.0.0.1` locally and `0.0.0.0` on Spaces |
| `PORT` | HTTP port; defaults to `7860` |
| `HF_HOME` | Hugging Face model cache directory |
| `HF_HUB_OFFLINE=1` | Use already-downloaded model files without network access |

### Docker

```bash
docker build -t evidencedoc .
docker run --rm -p 7860:7860 -v evidencedoc-models:/home/user/.cache/huggingface evidencedoc
```

The public Space builds from a fixed GitHub commit. See [deployment notes](docs/DEPLOYMENT.md) for the release contract.

## API

The Gradio endpoints expose the same flows as the UI:

```python
from gradio_client import Client, handle_file

client = Client("https://rabitrabi-evidencedoc.hf.space")
answer, evidence, pages, report_file, status = client.predict(
    handle_file("technical-report.pdf"),
    "What is the specified battery life?",
    "hybrid",  # or "text"
    api_name="/answer",
)
```

Use `/search` with the file and question to retrieve sources without model inference. Reports contain document hashes, physical page references, retrieval scores, mode, model revision, status, and elapsed time. Retrieval scores are not confidence estimates.

## Development and evaluation

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
ruff check .

# Regenerate the fictional sample and 20 development questions.
python scripts/make_examples.py
# Evaluate retrieval without loading a model.
python scripts/evaluate.py --search-only --output artifacts/retrieval.json
# Run both inference modes on three development cases.
python scripts/evaluate.py --ids t01,g01,u01 --output artifacts/comparison.json
```

The development fixture is original, fictional data released under CC0-1.0. It is not an independent benchmark. [Evaluation methodology](docs/EVALUATION.md) explains answer matching, retrieval recall, abstention, and the limits of the measurements.

## Supported scope

- One searchable PDF, up to **10 MiB and 10 pages**; questions of **3–500 characters**.
- At most three retrieved pages, 6,000 text characters per page, and 256 generated tokens.
- Page images are reduced to fit 512 × 512 pixels. Small text and dense charts can lose detail.
- Scanned documents require OCR, which is outside this release. Pages without extractable text are skipped and reported.
- Cropped, rotated, or offset-origin pages are rejected rather than displaying misplaced citation highlights.
- Retrieval is lexical, not a cross-language semantic search system. Synonyms or different-language questions may miss relevant evidence.
- Some repairable PDFs or owner-encrypted PDFs that do not require an opening password may be accepted by the underlying parser.
- If several citations refer to one page, all are listed; the gallery highlights the first one.

## Data handling

Local inference does not send document content to an external model provider. Hugging Face is contacted to download model files. Files uploaded to the public demo are processed on its hosting server; do not upload confidential material there.

Managed report originals are capped at 64 files. Gradio also creates upload/preview/download cache copies, which have an age limit rather than a file-count limit. Files older than one hour are removed at startup and during minute-by-minute cleanup in an application-specific, user-owned temporary directory.

PDF extraction runs in a disposable Linux process with a 768 MiB address-space limit, an eight-second CPU limit, and a twelve-second wall-clock timeout. These controls are not a complete security sandbox. Embedded document instructions are treated as data, but prompt-injection resistance is not guaranteed.

## Project structure

```text
app.py                 Gradio interface and API
 evidencedoc/          PDF processing, retrieval, inference, citation gate, reports
 scripts/              Original fixture generation and evaluation runner
 tests/                Regression and integration tests
 evaluation/           Development questions and measured runs
 docs/                 Architecture, evaluation, deployment, and contribution notes
```

## License and references

Code: [Apache-2.0](LICENSE). Fictional sample data: [CC0-1.0](examples/LICENSE).

- [Qwen3-VL-2B-Instruct model card](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)
- [UniDoc-Bench: document-centric multimodal RAG](https://aclanthology.org/2026.findings-emnlp.534/)
- [Benchmarking multilingual document understanding](https://arxiv.org/abs/2611.14758)
