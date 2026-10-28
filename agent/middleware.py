from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, RemoveMessage, ToolMessage
from langgraph.errors import GraphBubbleUp
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from observability import get_logger

logger = get_logger(__name__)


def _error_message(request, error: Exception) -> ToolMessage:
    name = request.tool_call["name"]
    logger.error(f"Tool {name} failed: {error}")
    return ToolMessage(
        content=f"Error: tool {name} failed: {error}",
        tool_call_id=request.tool_call["id"],
        name=name,
        status="error",
    )


def _patch_dangling_tool_calls(messages: list) -> list | None:
    """Insert a cancelled ToolMessage after every tool call that has no response."""
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    patched = []
    changed = False
    for message in messages:
        patched.append(message)
        if not isinstance(message, AIMessage):
            continue
        for call in message.tool_calls:
            if call["id"] not in answered:
                logger.warning(f"Patching dangling tool call {call['name']} ({call['id']})")
                patched.append(
                    ToolMessage(
                        content="Error: this tool call was interrupted and did not complete.",
                        tool_call_id=call["id"],
                        name=call["name"],
                        status="error",
                    )
                )
                changed = True
    return patched if changed else None


class ToolErrorMiddleware(AgentMiddleware):
    """Keep the message history valid when tools fail.

    Tool exceptions are returned to the model as error ToolMessages instead of
    aborting the run, and sessions that already contain an unanswered tool call
    (e.g. from an earlier crash) are repaired before the agent runs.
    """

    def before_agent(self, state, runtime):
        patched = _patch_dangling_tool_calls(state["messages"])
        if patched is None:
            return None
        return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *patched]}

    async def abefore_agent(self, state, runtime):
        return self.before_agent(state, runtime)

    def wrap_tool_call(self, request, handler):
        try:
            return handler(request)
        except GraphBubbleUp:
            raise
        except Exception as e:
            return _error_message(request, e)

    async def awrap_tool_call(self, request, handler):
        try:
            return await handler(request)
        except GraphBubbleUp:
            raise
        except Exception as e:
            return _error_message(request, e)
