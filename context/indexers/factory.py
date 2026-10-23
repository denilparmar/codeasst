from config import config, VectorStoreProvider
from observability.logger import get_logger

logger = get_logger(__name__)


def get_indexer():
    """Return the right index_codebase function based on the vector_store in the config"""
    vector_store = config["vector_store"]["provider"]
    logger.info(f"Using vector store: {vector_store}")
    match vector_store:
        case VectorStoreProvider.CHROMADB:
            from .semantic_chroma import index_codebase

            return index_codebase
        case VectorStoreProvider.QDRANT:
            from .semantic_qdrant import index_codebase

            return index_codebase


def get_index_inspector():
    """Return the right show_index function based on vector_store in config."""
    vector_store = config["vector_store"]["provider"]

    match vector_store:
        case VectorStoreProvider.CHROMADB:
            from .semantic_chroma import show_index

            return show_index
        case VectorStoreProvider.QDRANT:
            from .semantic_qdrant import show_index

            return show_index
