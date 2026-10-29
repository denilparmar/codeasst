from langchain.agents.middleware import HumanInTheLoopMiddleware

from config import config
from observability import get_logger

logger = get_logger(__name__)

_SHELL_TOOLS = ("run_command", "run_in_directory")
# chaining, redirection or substitution can turn a safe prefix into anything
_SHELL_METACHARS = (";", "&", "|", ">", "<", "`", "$(", "\n")


def _is_safe_command(command: str) -> bool:
    command = command.strip()
    if any(char in command for char in _SHELL_METACHARS):
        return False
    return any(
        command == prefix or command.startswith(prefix + " ")
        for prefix in config["hitl"]["safe_command_prefixes"]
    )


def _shell_needs_approval(request) -> bool:
    return not _is_safe_command(request.tool_call["args"].get("command", ""))


def get_hitl_middleware() -> HumanInTheLoopMiddleware | None:
    """Return middleware that pauses for approval before risky tool calls."""
    hitl_config = config.get("hitl", {})
    if not hitl_config.get("enabled"):
        return None

    interrupt_on = {
        name: {"allowed_decisions": ["approve", "edit", "reject"]}
        for name in hitl_config.get("approve_tools", [])
    }
    for name in _SHELL_TOOLS:
        interrupt_on[name] = {
            "allowed_decisions": ["approve", "edit", "reject"],
            "when": _shell_needs_approval,
        }
    logger.info(f"HITL approval enabled for: {sorted(interrupt_on)}")
    return HumanInTheLoopMiddleware(
        interrupt_on=interrupt_on,
        description_prefix="CodeAsst wants to run a tool",
    )
