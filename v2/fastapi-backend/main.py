import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from elasticsearch import Elasticsearch
from rerank import rerank

ES_URL = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = "qwen3-embedding:0.6b"
NB_CLUSTERS = 3

app = FastAPI()
es = Elasticsearch(ES_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str


def embed(text: str) -> list[float]:
    r = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["embeddings"][0]


@app.get("/")
def read_root():
    return {"message": "ElasticSearch Search API"}


@app.post("/search")
def search_data(req: SearchRequest):
    try:
        vector = embed(req.query)

        clusters = es.search(
            index="data_clusters",
            knn={"field": "embedding", "query_vector": vector,
                 "k": NB_CLUSTERS, "num_candidates": 10},
            size=NB_CLUSTERS,
        )
        hits = clusters["hits"]["hits"]
        indices = [h["_source"]["data_index"] for h in hits]
        labels = {h["_source"]["data_index"]: h["_source"].get("label") for h in hits}
        if not indices:
            return {"clusters": [], "results": []}

        docs = es.search(
            index=",".join(indices),
            query={"match": {"line": req.query}},
            knn={"field": "embedding", "query_vector": vector,
                 "k": 10, "num_candidates": 50},
            size=10,
        )
        results = [
            {"line": h["_source"]["line"], "score": h["_score"],
             "cluster": h["_index"], "label": labels.get(h["_index"])}
            for h in docs["hits"]["hits"]
        ]
        return {"clusters": indices, "results": rerank(req.query, results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
