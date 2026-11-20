import pytest


def test_turkish_suffix_and_case_retrieve_correct_page(make_pdf):
    from evidencedoc.documents import read_document
    from evidencedoc.retrieval import retrieve

    doc = read_document(make_pdf(["Garanti süresi 24 aydır.", "AĞIRLIK: 8 kg. Batarya: 9 saat."]))
    hits = retrieve(doc, "Ürünün ağırlığı nedir?")
    assert hits[0].page == 2
    assert hits[0].score > 0


def test_unrelated_question_has_no_hits(make_pdf):
    from evidencedoc.documents import read_document
    from evidencedoc.retrieval import retrieve

    assert retrieve(read_document(make_pdf()), "Kuantum işlemcinin fiyatı nedir?") == []


def test_hit_limit_and_question_validation(make_pdf):
    from evidencedoc.documents import read_document
    from evidencedoc.retrieval import retrieve

    doc = read_document(
        make_pdf(["Batarya 9 saat.", "Batarya 8 saat.", "Batarya 7 saat.", "Batarya 6 saat."])
    )
    assert len(retrieve(doc, "Batarya süresi?", 3)) == 3
    for question in ["", "ab", "x" * 501]:
        with pytest.raises(ValueError):
            retrieve(doc, question)
    with pytest.raises(ValueError):
        retrieve(doc, "Batarya süresi?", 20)


def test_concurrent_turkish_retrieval_matches_serial_result(make_pdf):
    import sys
    from concurrent.futures import ThreadPoolExecutor

    from evidencedoc.documents import read_document
    from evidencedoc.retrieval import retrieve

    doc = read_document(make_pdf(["Ağırlık 8 kg. Batarya süresi 9 saat.", "Garanti 24 ay."]))
    queries = ["Ürünlerin ağırlıkları ve bataryaları nedir?", "Garantilerin süresi kaç aydır?"] * 40
    expected = [retrieve(doc, q) for q in queries]
    previous = sys.getswitchinterval()
    try:
        sys.setswitchinterval(0.000001)
        with ThreadPoolExecutor(max_workers=8) as pool:
            actual = list(pool.map(lambda q: retrieve(doc, q), queries))
    finally:
        sys.setswitchinterval(previous)
    assert actual == expected
