# IA Search

Moteur de recherche IA : embeddings (Ollama), clusters (K-means),
recherche hybride kNN + BM25 (ElasticSearch), rerank par LLM.

## Prérequis
- Docker Desktop
- Ollama installé sur la machine, avec les modèles :
  - `ollama pull qwen3-embedding:0.6b`
  - `ollama pull qwen3.5:0.8b`
- uv (pour le script d'indexation)

## Lancement
1. `docker compose up -d elasticsearch backend front`
   (le backend joint Ollama via `host.docker.internal:11434`)
2. Indexer les données :
   `cd index_data && uv run main.py`
3. Ouvrir http://localhost:3000

## Architecture
- `index_data/` : script d'indexation (embeddings, K-means, ElasticSearch)
- `fastapi-backend/` : API de recherche (kNN sur les clusters, hybride dans le cluster, rerank)
- `react-front/` : interface React
- `docker-compose.yml` : ElasticSearch, Ollama, backend, front
