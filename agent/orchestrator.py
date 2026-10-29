from typing import Awaitable, Callable

from langgraph.types import Command

from observability import get_logger

logger = get_logger(__name__)

# Receives a HITLRequest and returns one decision per action request, in order.
Reviewer = Callable[[dict], Awaitable[list[dict]]]


async def handle_query(
    agent, question: str, thread_id: str, reviewer: Reviewer | None = None
) -> str:
    """Entry point for all user queries - invokes the agent."""
    logger.info(f"Handling query for session {thread_id}: {question}")
    agent_config = {"configurable": {"thread_id": thread_id}}
    try:
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}, agent_config
        )
        # the agent pauses with an interrupt whenever a tool call needs approval
        while response.get("__interrupt__"):
            hitl_request = response["__interrupt__"][0].value
            if reviewer is None:
                decisions = [
                    {
                        "type": "reject",
                        "message": "No reviewer available to approve this.",
                    }
                    for _ in hitl_request["action_requests"]
                ]
            else:
                decisions = await reviewer(hitl_request)
            logger.info(f"HITL decisions: {[d['type'] for d in decisions]}")
            response = await agent.ainvoke(
                Command(resume={"decisions": decisions}), agent_config
            )
        return response["messages"][-1].content
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return f"Error: {e}"
