from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from llm.factory import get_llm
from agent.hitl import get_hitl_middleware
from agent.middleware import ToolErrorMiddleware
from agent.tools import search_codebase
from observability import get_logger
from memory.short_term import get_checkpointer, get_summarization_middleware
from tools.terminal_tools import run_command, run_in_directory

from codeasst_mcp.codeasst_mcp_client import get_codeasst_mcp_tools

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer with deep knowledge of the codebase.
Always use the search_codebase tool before answering any question.
Reference specific file names, function names and line numbers in your answers.
If you cannot find the answer in the codebase, say so explicitly."""


async def build_agent(checkpointer):
    """Create and return a LangChain agent with persistent memory."""
    llm = get_llm()
    mcp_tools = await get_codeasst_mcp_tools()
    tools = [
        search_codebase,
        run_command,
        run_in_directory,
        *mcp_tools,
    ]
    middleware = [ToolErrorMiddleware(), get_summarization_middleware()]
    if hitl := get_hitl_middleware():
        middleware.append(hitl)

    return create_agent(
        llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        middleware=middleware,
    )
