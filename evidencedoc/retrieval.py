"""English/Turkish lexical BM25. Scores are ranking scores, never model confidence."""

import re
from collections import Counter
from dataclasses import dataclass
from math import log

import snowballstemmer

from evidencedoc.documents import Document, normalize

STOP = set(
    "ve veya bir bu şu o ile için göre hangi nedir ne kaç mi mı mu mü ürün ürünün olarak olan en az fazla daha hem da de the a an is are was were be been of to for in on at by from and or this that these those what which who how do does did will would should can could it its with as than then".split()
)


@dataclass(frozen=True)
class Hit:
    page: int
    score: float


def tokens(text: str) -> list[str]:
    stemmers = [snowballstemmer.stemmer("english"), snowballstemmer.stemmer("turkish")]
    variants = {normalize(text), text.casefold().replace("\u0307", "")}
    words = re.findall(r"[^\W_]+", " ".join(sorted(variants)), re.UNICODE)
    result = []
    for word in words:
        if word in STOP or (len(word) < 2 and not word.isdigit()):
            continue
        # Preserve identifiers and apply both stemmers without shared mutable state.
        result.extend(sorted({word, *(stemmer.stemWord(word) for stemmer in stemmers)}))
    return result


def validate_question(question: str) -> str:
    if not isinstance(question, str) or not 3 <= len(question.strip()) <= 500:
        raise ValueError("Your question must contain 3–500 characters.")
    return question.strip()


def retrieve(document: Document, question: str, limit: int = 3) -> list[Hit]:
    question = validate_question(question)
    if type(limit) is not int or not 1 <= limit <= 3:
        raise ValueError("At most three pages can be retrieved.")
    corpus = [tokens(p.text) for p in document.pages]
    queries = set(tokens(question))
    average = sum(map(len, corpus)) / max(1, len(corpus)) or 1
    hits = []
    for page, terms in zip(document.pages, corpus):
        counts, score = Counter(terms), 0.0
        for term in queries:
            frequency = counts[term]
            if not frequency:
                continue
            df = sum(term in words for words in corpus)
            idf = log(1 + (len(corpus) - df + 0.5) / (df + 0.5))
            score += (
                idf * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * len(terms) / average))
            )
        if score > 0:
            hits.append(Hit(page.number, round(score, 6)))
    return sorted(hits, key=lambda hit: (-hit.score, hit.page))[:limit]
