import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.agents.middleware import SummarizationMiddleware


from config import config, memory_db_path
from llm.factory import get_llm
from observability import get_logger

logger = get_logger(__name__)


def get_checkpointer() -> SqliteSaver:
    db_path = memory_db_path()
    logger.info(f"Using SQLite checkpointer at {db_path}")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteSaver(conn)


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


def get_summarization_middleware() -> SummarizationMiddleware:
    return SummarizationMiddleware(
        model=get_llm(),
        trigger=("tokens", config["memory"]["summarize_at_tokens"]),
        keep=("messages", config["memory"]["keep_last_messages"]),
    )
