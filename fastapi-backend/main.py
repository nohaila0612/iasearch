import os
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from elasticsearch import Elasticsearch
from rerank import rerank

ES_URL = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = "qwen3-embedding:0.6b"

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
    )
    r.raise_for_status()
    return r.json()["embeddings"][0]


@app.get("/")
def read_root():
    return {"message": "ElasticSearch Search API"}


@app.post("/search")
def search_data(req: SearchRequest):
    vector = embed(req.query)

    # 1. cluster le plus proche (recherche kNN)
    clusters = es.search(
        index="data_clusters",
        knn={"field": "embedding", "query_vector": vector,
             "k": 1, "num_candidates": 10},
        size=1,
    )
    hits = clusters["hits"]["hits"]
    if not hits:
        return {"cluster": None, "results": []}
    data_index = hits[0]["_source"]["data_index"]

    # 2. recherche hybride (BM25 + kNN) dans ce cluster
    docs = es.search(
        index=data_index,
        query={"match": {"line": req.query}},
        knn={"field": "embedding", "query_vector": vector,
             "k": 10, "num_candidates": 50},
        size=10,
    )
    results = [
        {"line": h["_source"]["line"], "score": h["_score"]}
        for h in docs["hits"]["hits"]
    ]
    results = rerank(req.query, results)
    return {"cluster": data_index, "results": results}