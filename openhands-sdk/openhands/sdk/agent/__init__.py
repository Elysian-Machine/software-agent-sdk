from __future__ import annotations

from typing import TYPE_CHECKING

from openhands.sdk.agent.agent import Agent
from openhands.sdk.agent.base import AgentBase


if TYPE_CHECKING:
    from openhands.sdk.agent.acp_agent import ACPAgent


# Lazy import: eagerly importing ACPAgent registers it in the
# DiscriminatedUnionMixin, which makes `kind` required in Agent payloads
# that previously defaulted.
def __getattr__(name: str):
    if name == "ACPAgent":
        try:
            from openhands.sdk.agent.acp_agent import ACPAgent
        except ImportError:
            raise ImportError(
                "The 'agent-client-protocol' package is required for ACPAgent. "
                "Install it with: pip install 'openhands-sdk[acp]' or "
                "pip install agent-client-protocol"
            ) from None

        return ACPAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Agent",
    "AgentBase",
    "ACPAgent",
]
