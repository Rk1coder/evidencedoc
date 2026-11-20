def test_english_plural_query_retrieves_the_battery_page(make_pdf):
    from evidencedoc.documents import read_document
    from evidencedoc.retrieval import retrieve

    doc = read_document(
        make_pdf(
            ["Calibration is required every twelve months.", "The batteries provide nine hours."]
        )
    )
    hits = retrieve(doc, "Battery duration?")
    assert hits and hits[0].page == 2


def test_english_uppercase_identifier_matches_lowercase_query(make_pdf):
    from evidencedoc.documents import read_document
    from evidencedoc.retrieval import retrieve

    doc = read_document(make_pdf(["The IP54 protection rating is certified."]))
    assert retrieve(doc, "ip54?")[0].page == 1


def test_english_unrelated_question_does_not_match_stopwords(make_pdf):
    from evidencedoc.documents import read_document
    from evidencedoc.retrieval import retrieve

    doc = read_document(make_pdf(["The battery is rated for nine hours."]))
    assert retrieve(doc, "What is the quantum processor price?") == []
