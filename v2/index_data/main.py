import requests
import numpy as np
from sklearn.cluster import KMeans
from elasticsearch import Elasticsearch, helpers

PCLOUD_URL = (
    "https://apilux3.pcloud.com/getpublinkdownload"
    "?fileid=93128819642&code=XZnqkRJZ98VUd3rEuMXAFIsEpAtnNHoKYK8k"
    "&linkpassword=&forcedownload=1"
)
OLLAMA_URL = "http://localhost:11434"
ES_URL = "http://localhost:9200"
EMBED_MODEL = "qwen3-embedding:0.6b"
NB_CLUSTERS = 5


def get_data_from_cloud() -> list[str]:
    info = requests.get(PCLOUD_URL).json()
    url = "https://" + info["hosts"][0] + info["path"]
    text = requests.get(url).text
    return [l.strip() for l in text.splitlines() if l.strip()]


def get_data_embeddings(lines: list[str]) -> list[list[float]]:
    embeddings = []
    batch_size = 32
    for i in range(0, len(lines), batch_size):
        batch = lines[i : i + batch_size]
        r = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": batch},
        )
        r.raise_for_status()
        embeddings.extend(r.json()["embeddings"])
        print(f"Embeddings: {len(embeddings)}/{len(lines)}")
    return embeddings


def cluster_data(embeddings, lines):
    X = np.array(embeddings)
    km = KMeans(n_clusters=NB_CLUSTERS, random_state=0, n_init=10).fit(X)
    clusters = {}
    for idx, label in enumerate(km.labels_):
        clusters.setdefault(int(label) + 1, []).append(idx)
    return clusters, km.cluster_centers_


def main():
    lines = get_data_from_cloud()
    print(f"{len(lines)} lignes récupérées")
    embeddings = get_data_embeddings(lines)
    clusters, centers = cluster_data(embeddings, lines)

    es = Elasticsearch(ES_URL)
    dims = len(embeddings[0])
    vec = {"type": "dense_vector", "dims": dims,
           "index": True, "similarity": "cosine"}

    # un index par cluster
    for cid, idxs in clusters.items():
        index = f"data_{cid}"
        if es.indices.exists(index=index):
            es.indices.delete(index=index)
        es.indices.create(index=index, mappings={
            "properties": {"embedding": vec, "line": {"type": "text"}}
        })
        helpers.bulk(es, (
            {"_index": index,
             "_source": {"embedding": embeddings[i], "line": lines[i]}}
            for i in idxs
        ))

    # index des clusters (centroïdes)
    if es.indices.exists(index="data_clusters"):
        es.indices.delete(index="data_clusters")
    es.indices.create(index="data_clusters", mappings={
        "properties": {"embedding": vec, "data_index": {"type": "keyword"}}
    })
    helpers.bulk(es, (
        {"_index": "data_clusters",
         "_source": {"embedding": centers[cid - 1].tolist(),
                     "data_index": f"data_{cid}"}}
        for cid in clusters
    ))
    es.indices.refresh(index="_all")
    print("Indexation terminée")


if __name__ == "__main__":
    main()