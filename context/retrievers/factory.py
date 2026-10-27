from config import config, VectorStoreProvider
from observability.logger import get_logger

logger = get_logger(__name__)


def get_retriever():
    """Return the right retrieve function based on vector_store in config."""
    mode = config["rag"]["mode"]
    vector_store = config["vector_store"]["provider"]
    logger.info(f"Using vector store for retrieval: {vector_store} and mode: {mode}")

    if mode == "hybrid" and vector_store == VectorStoreProvider.QDRANT:
        from .hybrid_qdrant import retrieve
    elif vector_store == VectorStoreProvider.QDRANT:
        from .semantic_qdrant import retrieve
    else:
        from .semantic_chroma import retrieve

    return retrieve
