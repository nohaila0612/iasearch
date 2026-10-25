from elasticsearch import Elasticsearch
from main import cluster_labels, ES_URL

es = Elasticsearch(ES_URL)
hits = es.search(index="data_clusters", size=50, _source=["data_index"])["hits"]["hits"]
texts, ids = {}, {}
for h in hits:
    idx = h["_source"]["data_index"]
    cid = int(idx.split("_")[1])
    ids[cid] = h["_id"]
    res = es.search(index=idx, size=5000, _source=["line"], query={"match_all": {}})
    texts[cid] = [x["_source"]["line"] for x in res["hits"]["hits"]]

labels = cluster_labels(texts)
for cid, _id in ids.items():
    es.update(index="data_clusters", id=_id, doc={"label": labels[cid]})
    print(f"data_{cid} ({len(texts[cid])} lignes) -> {labels[cid]}")
es.indices.refresh(index="data_clusters")
