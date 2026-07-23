from functools import lru_cache

from sentence_transformers import SentenceTransformer

@lru_cache
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer("BAAI/bge-small-en-v1.5")

def create_embeddings(texts: list[str]) -> list[list[float]]:
    embeddings = get_embedding_model().encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return [embedding.tolist() for embedding in embeddings]