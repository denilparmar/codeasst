from config import config, VectorStoreProvider
from observability.logger import get_logger

logger = get_logger(__name__)


def get_indexer():
    """Return the right index_codebase function based on the vector_store in the config"""
    vector_store = config["vector_store"]["provider"]
    mode = config["rag"]["mode"]

    logger.info(f"Using vector store: {vector_store} & mode: {mode}")
    if mode == "hybrid" and vector_store == VectorStoreProvider.QDRANT:
        from .hybrid_qdrant import index_codebase
    elif vector_store == VectorStoreProvider.QDRANT:
        from .semantic_qdrant import index_codebase
    else:
        from .semantic_chroma import index_codebase
    return index_codebase


def get_index_inspector():
    """Return the right show_index function based on rag mode and vector_store in config."""
    mode = config["rag"]["mode"]
    vector_store = config["vector_store"]["provider"]

    if mode == "hybrid" and vector_store == VectorStoreProvider.QDRANT:
        from .hybrid_qdrant import show_index
    elif vector_store == VectorStoreProvider.QDRANT:
        from .semantic_qdrant import show_index
    else:
        from .semantic_chroma import show_index

    return show_index
