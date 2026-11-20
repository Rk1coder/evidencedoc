"""EvidenceDoc: evidence-grounded PDF question answering."""

import html
import logging
import os
from pathlib import Path

from evidencedoc.reports import ReportStore, private_data_root

DATA_ROOT = private_data_root()
os.environ["GRADIO_TEMP_DIR"] = str(DATA_ROOT / "gradio")

import gradio as gr  # noqa: E402

from evidencedoc.documents import read_document, render_page  # noqa: E402
from evidencedoc.service import answer_document, search_document  # noqa: E402

STORE = ReportStore(DATA_ROOT / "reports", cache_root=DATA_ROOT / "gradio")
ROOT = Path(__file__).resolve().parent
CSS = """
.gradio-container {max-width:1280px!important; font-family:system-ui,sans-serif!important;}
#masthead {border-bottom:1px solid #d9e0e8; padding:16px 0 24px; margin-bottom:12px;}
#masthead h1 {font-size:30px; font-weight:600; letter-spacing:-.025em; margin:0;}
#masthead p {font-size:16px; line-height:1.55; color:#526173; max-width:65ch; margin:8px 0 0;}
#answer-panel {border:1px solid #d9e0e8; border-radius:10px; padding:22px; min-height:180px;}
#answer-panel p {line-height:1.65; overflow-wrap:anywhere;}
#evidence-panel blockquote {border-left:3px solid #3973aa; background:#f2f6fa; padding:12px 16px; margin:8px 0 18px;}
#evidence-panel p {overflow-wrap:anywhere;}
#evidence-panel blockquote {color:#142334;}
.dark #masthead p, .dark #notes {color:#a4b5c7;}
button {min-height:44px!important; letter-spacing:.015em;}
button:focus-visible, a:focus-visible {outline:3px solid #3973aa!important; outline-offset:3px;}
#primary-action {background:#18334e!important; color:white!important; border-color:#18334e!important;}
#notes {font-size:13px;line-height:1.55;color:#526173;letter-spacing:.01em;}
"""


def clear_result():
    return "Ask a question about your document.", "", [], None, "Ready"


def _present(report, file_path):
    document = read_document(file_path)
    evidence = ""
    for item in report["evidence"]:
        evidence += f"**Page {item['page']} · Quote matched in source text**\n\n"
        evidence += f"<blockquote>{html.escape(item['quote'])}</blockquote>\n\n"
    gallery = []
    for page in report["retrieved_pages"]:
        quotes = [item["quote"] for item in report["evidence"] if item["page"] == page["page"]]
        gallery.append(
            (
                render_page(document, page["page"], quotes[0] if quotes else ""),
                f"Page {page['page']}",
            )
        )
    labels = {
        "answered": "Citation matched",
        "sources_only": "Sources found · no model inference",
        "no_sources": "No relevant sources found",
        "abstained": "Insufficient evidence",
        "evidence_rejected": "Citation rejected",
        "invalid_model_output": "Invalid model output",
    }
    status = labels[report["status"]] + f" · {report['elapsed_seconds']:.1f} s"
    if report.get("device"):
        status += " · " + report["device"]
    if report["document"]["skipped_pages"]:
        status += " · Pages without text were skipped: " + ", ".join(
            map(str, report["document"]["skipped_pages"])
        )
    if any(page["text_truncated"] for page in report["retrieved_pages"]):
        status += " · Long page text was truncated to 6,000 characters"
    return html.escape(report["answer"]), evidence, gallery, STORE.write(report), status


def _run(file_path, question, mode):
    try:
        report = (
            search_document(file_path, question)
            if mode == "search"
            else answer_document(file_path, question, mode)
        )
        return _present(report, file_path)
    except (ValueError, RuntimeError, OSError) as exc:
        return html.escape(str(exc)), "", [], None, "Error · Request could not be completed"
    except Exception:
        logging.exception("Unexpected document processing error")
        return (
            "The request could not be completed. Check the server logs.",
            "",
            [],
            None,
            "Error · Request could not be completed",
        )


def analyze(file_path, question, mode="hybrid"):
    return _run(file_path, question, mode)


def browse_sources(file_path, question):
    return _run(file_path, question, "search")


def build_app():
    from scripts.make_examples import create_examples

    sample = ROOT / "examples/technical-catalog.pdf"
    if not sample.exists():
        create_examples(sample)
    # This one immutable public fixture is not an expiring user upload.
    gr.set_static_paths(paths=[sample])
    with gr.Blocks(title="EvidenceDoc", delete_cache=(60, 3600)) as demo:
        gr.HTML("""<header id="masthead"><h1>EvidenceDoc</h1>
        <p>Ask your documents. Inspect the evidence behind every answer.</p></header>""")
        with gr.Row():
            with gr.Column(scale=4, min_width=280):
                gr.Markdown("### 1. Document and question")
                upload = gr.File(
                    label="Technical report or product catalogue · PDF, up to 10 MB / 10 pages",
                    file_types=[".pdf"],
                    type="filepath",
                )
                question = gr.Textbox(
                    label="What would you like to know?",
                    lines=3,
                    max_length=500,
                    placeholder="For example: How much does Atlas A1 weigh?",
                )
                mode = gr.Radio(
                    [
                        ("Hybrid · text and page images", "hybrid"),
                        ("Baseline · text only", "text"),
                    ],
                    value="hybrid",
                    label="Answer method",
                )
                answer_button = gr.Button(
                    "Answer with evidence", variant="primary", elem_id="primary-action"
                )
                search_button = gr.Button("Find sources · no model inference")
                status = gr.Textbox(label="Processing status", value="Ready", interactive=False)
                gr.Markdown(
                    "The first answer downloads and loads the model. CPU inference can take longer. Source search does not load the model.",
                    elem_id="notes",
                )
                sample = ROOT / "examples/technical-catalog.pdf"
                if sample.exists():
                    gr.Examples(
                        [
                            [str(sample), "How much does Atlas A1 weigh?"],
                            [
                                str(sample),
                                "What is the average power consumption in intensive processing mode?",
                            ],
                            [str(sample), "What is the selling price of Atlas A1?"],
                        ],
                        inputs=[upload, question],
                        label="Try the fictional sample document",
                        example_labels=[
                            "Product specifications",
                            "Read the power chart",
                            "An unanswerable question",
                        ],
                    )
            with gr.Column(scale=6, min_width=280):
                gr.Markdown("### 2. Answer and evidence")
                answer = gr.Markdown(
                    "Upload a document or select an example to get started.", elem_id="answer-panel"
                )
                evidence = gr.Markdown(elem_id="evidence-panel")
                gr.Markdown(
                    "Citation matching confirms that the quote exists in the PDF. Review the source page to assess whether it supports the answer."
                )
                gallery = gr.Gallery(
                    label="Source pages · matched quotes highlighted in yellow",
                    columns=1,
                    height=530,
                    object_fit="contain",
                    buttons=["download", "fullscreen"],
                )
                report_file = gr.File(label="Download JSON report", interactive=False)
        outputs = [answer, evidence, gallery, report_file, status]
        generate_event = answer_button.click(
            analyze, [upload, question, mode], outputs, api_name="answer"
        )
        search_event = search_button.click(
            browse_sources, [upload, question], outputs, api_name="search"
        )
        for component in (upload, question, mode):
            component.change(
                clear_result,
                outputs=outputs,
                queue=False,
                cancels=[generate_event, search_event],
                api_name=False,
            )
        gr.Markdown(
            "Searchable PDFs are supported. Temporary uploads and reports expire after approximately one hour. "
            "[Source code](https://github.com/Rk1coder/evidencedoc) · [Model](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) · [Evaluation](https://github.com/Rk1coder/evidencedoc/blob/main/docs/EVALUATION.md)"
        )
    return demo


if __name__ == "__main__":
    STORE.start_cleanup()
    build_app().queue(default_concurrency_limit=1, max_size=8).launch(
        server_name=os.environ.get(
            "HOST", "0.0.0.0" if os.environ.get("SPACE_ID") else "127.0.0.1"
        ),
        server_port=int(os.environ.get("PORT", "7860")),
        max_file_size="10mb",
        theme=gr.themes.Base(
            primary_hue="slate",
            neutral_hue="slate",
            font=["system-ui", "sans-serif"],
        ),
        css=CSS,
        show_error=False,
        enable_monitoring=False,
    )
