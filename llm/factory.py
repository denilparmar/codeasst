from config import EmbeddingsProvider, LLMProvider, config
from observability import get_logger

logger = get_logger(__name__)


def get_llm():
    """Return the right langchain llm provider based on the config"""
    provider = config["llm"]["provider"]
    model = config["llm"]["model"]
    logger.info(f"Using llm provider: {provider} and model:{model}")

    match provider:
        case LLMProvider.ANTHROPIC:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=model)

        case LLMProvider.OPENAI:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model=model)


def get_embedder():
    """Return the right embedder based on the config"""
    provider = config["embeddings"]["provider"]
    model = config["embeddings"]["model"]
    logger.info(f"Using embeddings provider: {provider} and model:{model}")

    match provider:
        case EmbeddingsProvider.HUGGINGFACE:
            from langchain_huggingface import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(model_name=model)

        case EmbeddingsProvider.OPENAI:
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(model=model)
