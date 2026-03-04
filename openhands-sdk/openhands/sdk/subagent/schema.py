"""Schema for Markdown-based agent definition files."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import frontmatter
from pydantic import BaseModel, Field

from openhands.sdk.context.agent_context import AgentContext


if TYPE_CHECKING:
    from openhands.sdk.agent.agent import Agent
    from openhands.sdk.llm.llm import LLM

AgentFactoryFunc = Callable[["LLM"], "Agent"]

KNOWN_FIELDS: Final[set[str]] = {
    "name",
    "description",
    "model",
    "color",
    "tools",
    "skills",
    "max_iteration_per_run",
    "working_dir",
}


def _extract_color(fm: dict[str, object]) -> str | None:
    """Extract color from frontmatter."""
    color_raw = fm.get("color")
    color: str | None = str(color_raw) if color_raw is not None else None
    return color


def _extract_tools(fm: dict[str, object]) -> list[str]:
    """Extract tools from frontmatter."""
    tools_raw = fm.get("tools", [])

    # Ensure tools is a list of strings
    tools: list[str]
    if isinstance(tools_raw, str):
        tools = [tools_raw]
    elif isinstance(tools_raw, list):
        tools = [str(t) for t in tools_raw]
    else:
        tools = []
    return tools


def _extract_skills(fm: dict[str, object]) -> list[str]:
    """Extract skill names from frontmatter."""
    skills_raw = fm.get("skills", [])
    skills: list[str]
    if isinstance(skills_raw, str):
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    elif isinstance(skills_raw, list):
        skills = [str(s) for s in skills_raw]
    else:
        skills = []
    return skills


def _extract_examples(description: str) -> list[str]:
    """Extract <example> tags from description for agent triggering."""
    pattern = r"<example>(.*?)</example>"
    matches = re.findall(pattern, description, re.DOTALL | re.IGNORECASE)
    return [m.strip() for m in matches if m.strip()]


def _extract_max_iteration_per_run(fm: dict[str, object]) -> int | None:
    """Extract max iterations per run from frontmatter file."""
    max_iter_raw = fm.get("max_iteration_per_run")
    if isinstance(max_iter_raw, str):
        return int(max_iter_raw)
    if isinstance(max_iter_raw, int):
        return max_iter_raw
    return None


def _extract_working_dir(fm: dict[str, object]) -> str | None:
    working_dir_raw = fm.get("working_dir")
    return str(working_dir_raw) if working_dir_raw is not None else None


class AgentDefinition(BaseModel):
    """Agent definition loaded from Markdown file.

    Agents are specialized configurations that can be triggered based on
    user input patterns. They define custom system prompts and tool access.
    """

    name: str = Field(description="Agent name (from frontmatter or filename)")
    description: str = Field(default="", description="Agent description")
    model: str = Field(
        default="inherit", description="Model to use ('inherit' uses parent model)"
    )
    color: str | None = Field(default=None, description="Display color for the agent")
    tools: list[str] = Field(
        default_factory=list, description="List of allowed tools for this agent"
    )
    skills: list[str] = Field(
        default_factory=list,
        description="List of skill names for this agent. "
        "Resolved from project/user directories.",
    )
    system_prompt: str = Field(default="", description="System prompt content")
    source: str | None = Field(
        default=None, description="Source file path for this agent"
    )
    when_to_use_examples: list[str] = Field(
        default_factory=list,
        description="Examples of when to use this agent (for triggering)",
    )
    max_iteration_per_run: int | None = Field(
        default=None,
        description="Maximum iterations per run. "
        "It must be strictly positive, or None for default.",
        gt=0,
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory for the agent. "
        "Absolute paths are used as-is. "
        "Relative paths are resolved against the parent's workspace. "
        "None means inherit the parent's working directory.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata from frontmatter"
    )

    @classmethod
    def load(cls, agent_path: Path) -> AgentDefinition:
        """Load an agent definition from a Markdown file.

        Agent Markdown files have YAML frontmatter with:
        - name: Agent name
        - description: Description with optional <example> tags for triggering
        - tools (optional): List of allowed tools
        - skills (optional): Comma-separated skill names or list of skill names
        - model (optional): Model profile to use (default: 'inherit')
        - color (optional): Display color
        - max_iterations_per_run: Max iteration per run
        - working_dir (optional): Working directory (absolute or relative to parent)

        The body of the Markdown is the system prompt.

        Args:
            agent_path: Path to the agent Markdown file.

        Returns:
            Loaded AgentDefinition instance.
        """
        with open(agent_path) as f:
            post = frontmatter.load(f)

        fm = post.metadata
        content = post.content.strip()

        # Extract frontmatter fields with proper type handling
        name: str = str(fm.get("name", agent_path.stem))
        description: str = str(fm.get("description", ""))
        model: str = str(fm.get("model", "inherit"))
        color: str | None = _extract_color(fm)
        tools: list[str] = _extract_tools(fm)
        skills: list[str] = _extract_skills(fm)
        max_iteration_per_run: int | None = _extract_max_iteration_per_run(fm)
        working_dir: str | None = _extract_working_dir(fm)

        # Extract whenToUse examples from description
        when_to_use_examples = _extract_examples(description)

        # Remove known fields from metadata to get extras
        metadata = {k: v for k, v in fm.items() if k not in KNOWN_FIELDS}

        return cls(
            name=name,
            description=description,
            model=model,
            color=color,
            tools=tools,
            skills=skills,
            max_iteration_per_run=max_iteration_per_run,
            working_dir=working_dir,
            system_prompt=content,
            source=str(agent_path),
            when_to_use_examples=when_to_use_examples,
            metadata=metadata,
        )

    @classmethod
    def from_factory_func(
        cls,
        name: str,
        factory_func: AgentFactoryFunc,
        description: str,
    ) -> AgentDefinition:
        """Build an AgentDefinition by introspecting a live Agent instance.

        Args:
            name: Name for the agent definition.
            factory_func: Factory function for this agent definition.
            description: Human-readable description of the agent.

        Returns:
            A fully populated AgentDefinition.
        """
        from openhands.sdk.llm.llm import LLM

        agent = factory_func(LLM(model="__introspect__", api_key="n/a"))

        tools = [t.name for t in agent.tools]
        if agent.agent_context and agent.agent_context.system_message_suffix:
            system_prompt = agent.agent_context.system_message_suffix
        else:
            system_prompt = ""

        skills: list[str] = []
        if agent.agent_context and agent.agent_context.skills:
            skills = [s.name for s in agent.agent_context.skills]

        model = agent.llm.model if agent.llm.model else "inherit"

        return cls(
            name=name,
            description=description,
            tools=tools,
            skills=skills,
            system_prompt=system_prompt,
            model=model,
        )

    def to_factory(self) -> AgentFactoryFunc:
        """Create an agent factory function from this definition.

        The returned callable accepts an ``LLM`` instance (the parent agent's
        LLM) and builds a fully-configured ``Agent`` instance.

        Both tools and skills are resolved eagerly (at ``.to_factory()`` call
        time) so that missing references fail fast rather than at agent spawn
        time.

        Raises:
            ValueError: If a tool is not registered or a skill is not found.
        """
        from openhands.sdk.agent.agent import Agent

        resolved_tools = self._resolve_tools()
        resolved_skills = self._resolve_skills()
        agent_def = self

        def _factory(llm: LLM) -> Agent:
            # Handle model override
            if agent_def.model and agent_def.model != "inherit":
                llm = llm.model_copy(update={"model": agent_def.model})

            # the system prompt of the subagent is added as a suffix of the
            # main system prompt
            has_context = agent_def.system_prompt or resolved_skills
            agent_context = (
                AgentContext(
                    system_message_suffix=agent_def.system_prompt or None,
                    skills=resolved_skills,
                )
                if has_context
                else None
            )

            return Agent(
                llm=llm,
                tools=resolved_tools,
                agent_context=agent_context,
            )

        return _factory

    def _resolve_skills(self) -> list:
        if not self.skills:
            return []

        from openhands.sdk.context.skills import load_available_skills

        available = load_available_skills(
            self.working_dir,
            include_user=True,
            include_project=True,
            include_public=False,
        )
        missing = [s for s in self.skills if s not in available]
        if missing:
            raise ValueError(
                f"Skills not found but given to agent '{self.name}': "
                f"{', '.join(missing)}"
            )

        return [available[skill_name] for skill_name in self.skills]

    def _resolve_tools(self) -> list:
        from openhands.sdk import Tool, list_registered_tools

        registered_tools: set[str] = set(list_registered_tools())
        missing = [t for t in self.tools if t not in registered_tools]
        if missing:
            raise ValueError(
                f"Tools not registered but given to agent '{self.name}': "
                f"{', '.join(missing)}"
            )

        return [Tool(name=tool_name) for tool_name in self.tools]
