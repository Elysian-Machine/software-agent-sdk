"""Tests for subagent registration on remote server.

When a client sends a StartConversationRequest to the agent-server,
subagent definitions registered on the client must be forwarded to
the server so that delegation tools can use them in their description.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from openhands.agent_server.conversation_service import ConversationService
from openhands.agent_server.models import StartConversationRequest
from openhands.sdk import LLM, Agent, Tool
from openhands.sdk.subagent.registry import (
    _reset_registry_for_tests,
    get_factory_info,
    get_registered_agent_definitions,
    register_agent,
    register_agent_if_absent,
)
from openhands.sdk.subagent.schema import AgentDefinition
from openhands.sdk.workspace import LocalWorkspace


@pytest.fixture(autouse=True)
def _clean_subagent_registry():
    _reset_registry_for_tests()
    yield
    _reset_registry_for_tests()


@pytest.fixture
def conversation_service():
    with tempfile.TemporaryDirectory() as temp_dir:
        service = ConversationService(
            conversations_dir=Path(temp_dir) / "conversations",
        )
        service._event_services = {}
        yield service


def _make_request(**overrides) -> StartConversationRequest:
    agent = overrides.pop(
        "agent",
        Agent(
            llm=LLM(
                model="openai/gpt-4o",
                api_key=SecretStr("test-key"),
                base_url="https://api.openai.com/v1",
            ),
            tools=[],
        ),
    )
    workspace = overrides.pop("workspace", LocalWorkspace(working_dir="/workspace"))
    return StartConversationRequest(
        agent=agent,
        workspace=workspace,
        **overrides,
    )


@pytest.mark.asyncio
async def test_start_conversation_registers_subagent_definitions(conversation_service):
    """Subagent definitions in the request are registered so the agent can see them."""
    from openhands.sdk.tool import register_tool
    from openhands.sdk.tool.builtins import FinishTool, ThinkTool

    register_tool(
        "finish",
        FinishTool,
    )
    register_tool(
        "think",
        ThinkTool,
    )

    agent_defs = [
        AgentDefinition(
            name="bash",
            description="Command execution specialist",
            tools=["finish"],
            system_prompt="You are a bash specialist.",
        ),
        AgentDefinition(
            name="explore",
            description="Codebase exploration agent",
            tools=["think"],
            system_prompt="You are an exploration specialist.",
        ),
    ]

    request = _make_request(
        subagent_definitions=[d.model_dump() for d in agent_defs],
    )

    mock_event_service = AsyncMock()
    conversation_service._start_event_service = AsyncMock(
        return_value=mock_event_service
    )
    mock_event_service.get_state = AsyncMock(return_value=None)

    with pytest.raises(Exception):
        # Fails later in _compose_conversation_info (None state), but
        # subagent registration happens before that point.
        await conversation_service.start_conversation(request)

    info = get_factory_info()
    assert "bash" in info
    assert "explore" in info


def test_get_registered_agent_definitions_returns_stored_definitions():
    """Registered definitions are retrievable for forwarding to remote servers."""
    for name, desc, tool in [
        ("bash", "Command execution", "terminal"),
        ("explore", "Codebase exploration", "file_editor"),
    ]:
        register_agent_if_absent(
            lambda llm: None,  # type: ignore[return-value]
            AgentDefinition(name=name, description=desc, tools=[tool]),
        )

    defs = get_registered_agent_definitions()
    assert {d.name for d in defs} == {"bash", "explore"}
    assert {d.description for d in defs} == {
        "Command execution",
        "Codebase exploration",
    }
    assert {"".join(d.tools) for d in defs} == {"terminal", "file_editor"}


def test_register_agent_introspects_factory():
    """register_agent() introspects the factory to build a full definition."""
    from openhands.sdk.context.agent_context import AgentContext
    from openhands.sdk.tool import register_tool
    from openhands.sdk.tool.builtins import FinishTool

    register_tool(
        "finish",
        FinishTool,
    )

    def create_expert(llm):
        return Agent(
            llm=llm,
            tools=[Tool(name="finish")],
            agent_context=AgentContext(
                system_message_suffix="You are an expert.",
            ),
        )

    register_agent(
        name="expert",
        factory_func=create_expert,
        description="An expert agent",
    )

    defs = get_registered_agent_definitions()
    expert_def = next(d for d in defs if d.name == "expert")
    assert expert_def.tools == ["finish"]
    assert expert_def.system_prompt == "You are an expert."
