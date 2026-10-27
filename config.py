import hashlib
import re
import yaml
from enum import StrEnum
from pathlib import Path


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class EmbeddingsProvider(StrEnum):
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"


class VectorStoreProvider(StrEnum):
    CHROMADB = "chromadb"
    QDRANT = "qdrant"


# config section -> enum its "provider" value must belong to
PROVIDER_ENUMS: dict[str, type[StrEnum]] = {
    "llm": LLMProvider,
    "embeddings": EmbeddingsProvider,
    "vector_store": VectorStoreProvider,
}


def load_config() -> dict:
    """Load settings from config.yaml at the project root."""
    cfg = yaml.safe_load((Path(__file__).parent / "config.yaml").read_text())

    for section, enum in PROVIDER_ENUMS.items():
        value = cfg[section]["provider"]
        try:
            cfg[section]["provider"] = enum(value)
        except ValueError:
            allowed = ", ".join(e.value for e in enum)
            raise ValueError(
                f"Invalid {section}.provider '{value}' in config.yaml. Allowed: {allowed}"
            ) from None

    return cfg


config = load_config()


def qdrant_collection_name() -> str:
    """Per-project Qdrant collection: <base>_<folder>_<path hash>, keyed on the current directory."""
    project = Path.cwd().resolve()
    folder = re.sub(r"[^A-Za-z0-9_-]", "_", project.name)
    digest = hashlib.sha1(str(project).encode()).hexdigest()[:8]
    return f"{config['qdrant']['collection_name']}_{folder}_{digest}"


def memory_db_path() -> Path:
    """Per-project memory DB, resolved against the current directory; creates its folder on first use."""
    db_path = Path.cwd().resolve() / config["memory"]["db_path"]
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True)
        # keep the memory folder out of the target project's git
        (db_path.parent / ".gitignore").write_text("*\n")
    return db_path
