from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents.middleware import SummarizationMiddleware
from pathlib import Path


from config import config
from llm.factory import get_llm
from observability import get_logger

logger = get_logger(__name__)


def get_checkpointer_db_path() -> str:
    db_path = config["memory"]["db_path"]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using SQLite checkpointer at {db_path}")
    return db_path


def get_checkpointer() -> AsyncSqliteSaver:
    db_path = get_checkpointer_db_path()
    return AsyncSqliteSaver.from_conn_string(db_path)


def get_summarization_middleware() -> SummarizationMiddleware:
    return SummarizationMiddleware(
        model=get_llm(),
        trigger=("tokens", config["memory"]["summarize_at_tokens"]),
        keep=("messages", config["memory"]["keep_last_messages"]),
    )


def get_session_history(thread_id: str) -> list[dict]:
    checkpointer = get_checkpointer()
    config_ = {"configurable": {"thread_id": thread_id}}
    checkpoint = checkpointer.get(config_)
    if not checkpoint:
        return []
    messages = checkpoint["channel_values"].get("messages", [])
    return [
        {"role": "user" if m.type == "human" else "assistant", "content": m.content}
        for m in messages
        # skip tool results and tool-call-only turns
        if m.type in ("human", "ai") and m.content
    ]
