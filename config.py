import yaml
from enum import StrEnum
from pathlib import Path


class LLMProvider(StrEnum):
   OPENAI = "openai"
   ANTHROPIC = "anthropic"


class EmbeddingsProvider(StrEnum):
   OPENAI = "openai"
   HUGGINGFACE = "huggingface"


# config section -> enum its "provider" value must belong to
PROVIDER_ENUMS: dict[str, type[StrEnum]] = {
   "llm": LLMProvider,
   "embeddings": EmbeddingsProvider,
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
