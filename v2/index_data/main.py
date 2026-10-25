import os
import requests
import numpy as np
from sklearn.cluster import KMeans
from elasticsearch import Elasticsearch, helpers

PCLOUD_URL = (
    "https://apilux3.pcloud.com/getpublinkdownload"
    "?fileid=93128819642&code=XZnqkRJZ98VUd3rEuMXAFIsEpAtnNHoKYK8k"
    "&linkpassword=&forcedownload=1"
)
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ES_URL = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
EMBED_MODEL = "qwen3-embedding:0.6b"
CHAT_MODEL = "qwen3.5:0.8b"
NB_CLUSTERS = 5
DEFAULT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "data", "objet_consultations_sample.txt",
)


def get_data_from_cloud() -> list[str]:
    path = os.getenv("DATA_FILE", DEFAULT_FILE)
    if os.path.exists(path):
        print(f"Lecture du fichier local : {path}")
        with open(path, encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    # repli : le jeu de données du TD (lien pCloud)
    print("Fichier local absent, utilisation du jeu de données du TD")
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
            json={"model": EMBED_MODEL, "input": batch, "keep_alive": "30m"},
            timeout=300,
        )
        r.raise_for_status()
        embeddings.extend(r.json()["embeddings"])
        print(f"Embeddings: {len(embeddings)}/{len(lines)}")
    return embeddings


def cluster_data(embeddings):
    X = np.array(embeddings)
    km = KMeans(n_clusters=NB_CLUSTERS, random_state=0, n_init=10).fit(X)
    clusters = {}
    for idx, label in enumerate(km.labels_):
        clusters.setdefault(int(label) + 1, []).append(idx)
    return clusters, km.cluster_centers_


FR_STOP = ["alors","avec","dans","dont","elle","elles","entre","être","leur","leurs","mais","même","nous","pour","sans","sont","sous","tous","tout","toute","toutes","vers","vous","cette","ainsi","aussi","comme","plus","chez","lors","suite","avoir","fait","faire","selon","dans","des","les","une","aux","par","sur","est","pas","que","qui","the","and","marché","marchés","public","publics","publique","publiques","consultation","mission","missions","prestation","prestations","assistance","numéro","lot","lots"]


def cluster_labels(texts_by_cid):
    """Nom de chaque cluster : ses 3 mots les plus caractéristiques (TF-IDF)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    cids = list(texts_by_cid)
    docs = [" ".join(texts_by_cid[c]) for c in cids]
    vec = TfidfVectorizer(stop_words=FR_STOP, lowercase=True,
                          token_pattern=r"(?u)\b[^\W\d_]{4,}\b",
                          max_df=0.6, sublinear_tf=True)
    X = vec.fit_transform(docs)
    terms = vec.get_feature_names_out()
    labels = {}
    for i, c in enumerate(cids):
        row = X[i].toarray()[0]
        top = [terms[j] for j in row.argsort()[::-1][:3] if row[j] > 0]
        labels[c] = (" · ".join(top)).capitalize() if top else f"Groupe {c}"
    return labels


def main():
    lines = get_data_from_cloud()
    print(f"{len(lines)} lignes récupérées")
    embeddings = get_data_embeddings(lines)
    clusters, centers = cluster_data(embeddings)

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

    # index des clusters (centroïdes + nom)
    labels = cluster_labels({c: [lines[i] for i in ix] for c, ix in clusters.items()})
    if es.indices.exists(index="data_clusters"):
        es.indices.delete(index="data_clusters")
    es.indices.create(index="data_clusters", mappings={
        "properties": {"embedding": vec,
                       "data_index": {"type": "keyword"},
                       "label": {"type": "keyword"}}
    })
    helpers.bulk(es, (
        {"_index": "data_clusters",
         "_source": {"embedding": centers[cid - 1].tolist(),
                     "data_index": f"data_{cid}",
                     "label": labels[cid]}}
        for cid, idxs in clusters.items()
    ))
    es.indices.refresh(index="_all")
    print("Indexation terminée")


if __name__ == "__main__":
    main()
