---
title: EvidenceDoc
emoji: 📄
colorFrom: blue
colorTo: gray
sdk: static
app_file: index.html
license: apache-2.0
short_description: Inspect recorded document QA results and source evidence.
models:
  - Qwen/Qwen3-VL-2B-Instruct
tags:
  - document-question-answering
  - retrieval-augmented-generation
  - vision-language-model
---

# EvidenceDoc

**Ask your documents. Inspect the evidence behind every answer.**

[Source code and local application](https://github.com/Rk1coder/evidencedoc) · [Evaluation methodology](https://github.com/Rk1coder/evidencedoc/blob/main/docs/EVALUATION.md)

This Space is an interactive **recorded-results preview**. It replays real CPU model outputs, source-page evidence, and JSON reports. It does not run a model or accept new document uploads.

The full open-source application provides English document question answering, English/Turkish lexical retrieval, local Qwen3-VL inference, citation checks, annotated page previews, and JSON export. Run it locally or deploy it on an account with compute access to analyze your own PDFs.

The fictional sample and 20 development questions are CC0-1.0. The recorded runs are functionality probes, not an independent benchmark. Citation matching checks quote presence, not whether the quote semantically supports the answer.

Code: Apache-2.0. Model: [Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct), revision `89644892e4d85e24eaac8bacfd4f463576704203`.
