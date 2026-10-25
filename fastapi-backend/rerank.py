import math
import os
import requests
from concurrent.futures import ThreadPoolExecutor

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
RERANK_MODEL = "qwen3.5:0.8b"

SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string", "enum": ["yes", "no"]}},
    "required": ["answer"],
}


def _score(query: str, doc: str) -> float:
    prompt = (
        "Judge whether the Document is relevant to the Query. "
        'Answer with JSON {"answer": "yes"} or {"answer": "no"}.\n\n'
        f"Query: {query}\n\nDocument: {doc}"
    )
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": RERANK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "format": SCHEMA,
            "stream": False,
            "think": False,
            "logprobs": True,
            "top_logprobs": 20,
            "options": {"temperature": 0},
        },
        timeout=120,
    )
    r.raise_for_status()
    logprobs = r.json().get("logprobs") or []

    # on cherche le token qui porte la réponse (yes / no)
    for tok in logprobs:
        if tok["token"].strip().lower() in ("yes", "no"):
            p_yes = p_no = 0.0
            for alt in tok.get("top_logprobs", []):
                t = alt["token"].strip().lower()
                if t == "yes":
                    p_yes += math.exp(alt["logprob"])
                elif t == "no":
                    p_no += math.exp(alt["logprob"])
            total = p_yes + p_no
            return p_yes / total if total > 0 else 0.0
    return 0.0


#def rerank(query: str, docs: list[dict]) -> list[dict]:
    #for d in docs:
        #d["rerank_score"] = _score(query, d["line"])
    #return sorted(docs, key=lambda d: d["rerank_score"], reverse=True)


def rerank(query: str, docs: list[dict]) -> list[dict]:
    with ThreadPoolExecutor(max_workers=4) as ex:
        scores = list(ex.map(lambda d: _score(query, d["line"]), docs))
    for d, s in zip(docs, scores):
        d["rerank_score"] = s
    return sorted(docs, key=lambda d: d["rerank_score"], reverse=True)