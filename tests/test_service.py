import json

import pytest


class FixedGenerator:
    """Only replace expensive generation; the real PDF and evidence gate still run."""

    device = "test-double"

    def __init__(self, response):
        self.response = response

    def generate(self, question, pages, mode):
        assert question == "Atlas ağırlığı nedir?"
        assert pages[0]["page"] == 1
        assert mode in {"hybrid", "text"}
        if mode == "hybrid":
            assert pages[0]["image"].width > 100
        else:
            assert "image" not in pages[0]
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def ask(make_pdf, payload, mode="hybrid"):
    from evidencedoc.service import answer_document

    path = make_pdf(["Atlas ağırlığı 8 kg. Garanti 24 ay."])
    return answer_document(path, "Atlas ağırlığı nedir?", mode, FixedGenerator(payload))


@pytest.mark.parametrize("mode", ["hybrid", "text"])
def test_valid_quote_is_checked_against_real_pdf(make_pdf, mode):
    report = ask(
        make_pdf,
        json.dumps(
            {
                "answer": "Atlas 8 kg ağırlığındadır.",
                "abstain": False,
                "evidence": [{"source_id": 1, "quote": "Atlas ağırlığı 8 kg."}],
            }
        ),
        mode,
    )
    assert report["status"] == "answered"
    assert report["answer"] == "Atlas 8 kg ağırlığındadır."
    assert report["evidence"][0]["quote_checked"] is True
    assert report["evidence"][0]["boxes"]
    assert report["mode"] == mode


@pytest.mark.parametrize(
    "evidence",
    [
        [{"source_id": 1, "quote": "Atlas ağırlığı 999 kg."}],
        [{"source_id": 9, "quote": "Atlas ağırlığı 8 kg."}],
        [{"source_id": True, "quote": "Atlas ağırlığı 8 kg."}],
        [{"source_id": 1, "quote": ""}],
        [],
    ],
)
def test_invalid_evidence_blocks_generated_answer(make_pdf, evidence):
    report = ask(
        make_pdf, json.dumps({"answer": "Untrusted answer", "abstain": False, "evidence": evidence})
    )
    assert report["status"] == "evidence_rejected"
    assert "Untrusted answer" not in report["answer"]
    assert report["evidence"] == []


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        '{"answer":',
        "{}",
        "x" * 20001,
        '{"answer":"x","abstain":"false","evidence":[]}',
        '{"answer":"x","abstain":false,"evidence":{}}',
    ],
)
def test_bad_model_schema_is_visible_failure(make_pdf, payload):
    report = ask(make_pdf, payload)
    assert report["status"] == "invalid_model_output"
    assert report["evidence"] == []


def test_model_abstention_does_not_repeat_untrusted_answer(make_pdf):
    report = ask(
        make_pdf, json.dumps({"answer": "Invented price 999 TL", "abstain": True, "evidence": []})
    )
    assert report["status"] == "abstained"
    assert "999" not in report["answer"]


def test_model_outage_is_never_reported_as_success(make_pdf):
    with pytest.raises(RuntimeError, match="model"):
        ask(make_pdf, RuntimeError("simulated unavailable weights"))


def test_no_relevant_source_does_not_invoke_model(make_pdf):
    from evidencedoc.service import answer_document

    class MustNotRun:
        def generate(self, *args):
            pytest.fail("No-match retrieval must not load or call the model")

    report = answer_document(make_pdf(), "Kuantum işlemci nedir?", generator=MustNotRun())
    assert report["status"] == "no_sources"
    assert report["model_called"] is False


def test_search_is_explicitly_not_a_generated_answer(make_pdf):
    from evidencedoc.service import search_document

    report = search_document(make_pdf(), "Atlas ağırlığı nedir?")
    assert report["status"] == "sources_only"
    assert report["model_called"] is False
    assert report["retrieved_pages"][0]["page"] == 1


def test_invalid_input_is_rejected_before_generator(make_pdf):
    from evidencedoc.service import answer_document

    path = make_pdf()
    with pytest.raises(ValueError):
        answer_document(path, "Atlas ağırlığı?", "unknown")
    with pytest.raises(ValueError):
        answer_document("/no/file.pdf", "Atlas ağırlığı?")
    with pytest.raises(ValueError):
        answer_document(path, "x" * 501)


def test_harmless_trailing_model_quote_still_requires_valid_evidence(make_pdf):
    payload = json.dumps({"answer": "", "abstain": True, "evidence": []}) + '"'
    report = ask(make_pdf, payload)
    assert report["status"] == "abstained"


def test_model_source_id_maps_to_physical_pdf_page(make_pdf):
    from evidencedoc.service import answer_document

    path = make_pdf(["Atlas bakım notları.", "Boşta 18 W."], name="source-order.pdf")

    class SourceGenerator:
        def generate(self, question, pages, mode):
            assert pages[0]["page"] == 2
            return json.dumps(
                {
                    "answer": "18 W",
                    "abstain": False,
                    "evidence": [{"source_id": 1, "quote": "Boşta 18 W."}],
                }
            )

    report = answer_document(path, "Boşta güç kaç W?", "text", SourceGenerator())
    assert report["status"] == "answered"
    assert report["evidence"][0]["page"] == 2
