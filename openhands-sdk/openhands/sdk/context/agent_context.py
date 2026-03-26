from __future__ import annotations

import pathlib
import re
from collections.abc import Mapping
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from openhands.sdk.context.prompts import render_template
from openhands.sdk.context.skills import (
    Skill,
    SkillKnowledge,
    load_available_skills,
    to_prompt,
)
from openhands.sdk.context.skills.skill import DEFAULT_MARKETPLACE_PATH
from openhands.sdk.llm import Message, TextContent
from openhands.sdk.llm.utils.model_prompt_spec import get_model_prompt_spec
from openhands.sdk.logger import get_logger
from openhands.sdk.secret import SecretSource, SecretValue


logger = get_logger(__name__)


_RELEVANT_SKILL_TERM_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")
_RELEVANT_SKILL_STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "application",
    "applications",
    "assistant",
    "build",
    "built",
    "check",
    "create",
    "describe",
    "for",
    "from",
    "help",
    "how",
    "implement",
    "into",
    "make",
    "need",
    "open",
    "openhands",
    "please",
    "project",
    "projects",
    "repo",
    "repository",
    "review",
    "run",
    "set",
    "should",
    "source",
    "task",
    "tasks",
    "that",
    "the",
    "this",
    "use",
    "using",
    "with",
}
_RELEVANT_SKILL_MIN_SCORE = 3
_RELEVANT_SKILL_MAX_SUGGESTIONS = 3


def _extract_relevance_terms(text: str) -> set[str]:
    normalized = text.lower().replace("/", " ").replace("_", " ")
    terms: set[str] = set()
    for match in _RELEVANT_SKILL_TERM_PATTERN.finditer(normalized):
        token = match.group(0).strip("-_")
        if len(token) < 2 or token in _RELEVANT_SKILL_STOPWORDS:
            continue
        terms.add(token)
        if "-" in token:
            terms.update(
                part
                for part in token.split("-")
                if len(part) >= 2 and part not in _RELEVANT_SKILL_STOPWORDS
            )
    return terms


def _score_relevant_skill(skill: Skill, query: str, query_terms: set[str]) -> int:
    haystack = " ".join(filter(None, [skill.name, skill.description or ""]))
    skill_terms = _extract_relevance_terms(haystack)
    score = len(query_terms & skill_terms)

    skill_name = skill.name.lower()
    query_lower = query.lower()
    if skill_name in query_lower:
        score += 3

    skill_name_terms = _extract_relevance_terms(skill.name)
    score += 2 * len(query_terms & skill_name_terms)
    return score


def _format_relevant_skills_hint(skills: list[Skill]) -> str:
    return (
        "<RELEVANT_SKILLS>\n"
        "The following available skills look relevant to the user's request. "
        "Review the listed skill files before deciding whether to use them.\n\n"
        f"{to_prompt(skills, max_description_length=240)}\n"
        "</RELEVANT_SKILLS>"
    )


PROMPT_DIR = pathlib.Path(__file__).parent / "prompts" / "templates"


class AgentContext(BaseModel):
    """Central structure for managing prompt extension.

    AgentContext unifies all the contextual inputs that shape how the system
    extends and interprets user prompts. It combines both static environment
    details and dynamic, user-activated extensions from skills.

    Specifically, it provides:
    - **Repository context / Repo Skills**: Information about the active codebase,
      branches, and repo-specific instructions contributed by repo skills.
    - **Runtime context**: Current execution environment (hosts, working
      directory, secrets, date, etc.).
    - **Conversation instructions**: Optional task- or channel-specific rules
      that constrain or guide the agent’s behavior across the session.
    - **Knowledge Skills**: Extensible components that can be triggered by user input
      to inject knowledge or domain-specific guidance.

    Together, these elements make AgentContext the primary container responsible
    for assembling, formatting, and injecting all prompt-relevant context into
    LLM interactions.
    """  # noqa: E501

    skills: list[Skill] = Field(
        default_factory=list,
        description="List of available skills that can extend the user's input.",
    )
    system_message_suffix: str | None = Field(
        default=None, description="Optional suffix to append to the system prompt."
    )
    user_message_suffix: str | None = Field(
        default=None, description="Optional suffix to append to the user's message."
    )
    load_user_skills: bool = Field(
        default=False,
        description=(
            "Whether to automatically load user skills from ~/.openhands/skills/ "
            "and ~/.openhands/microagents/ (for backward compatibility). "
        ),
    )
    load_public_skills: bool = Field(
        default=False,
        description=(
            "Whether to automatically load skills from the public OpenHands "
            "skills repository at https://github.com/OpenHands/extensions. "
            "This allows you to get the latest skills without SDK updates."
        ),
    )
    marketplace_path: str | None = Field(
        default=DEFAULT_MARKETPLACE_PATH,
        description=(
            "Relative marketplace JSON path within the public skills repository. "
            "Set to None to load all public skills without marketplace filtering."
        ),
    )
    secrets: Mapping[str, SecretValue] | None = Field(
        default=None,
        description=(
            "Dictionary mapping secret keys to values or secret sources. "
            "Secrets are used for authentication and sensitive data handling. "
            "Values can be either strings or SecretSource instances "
            "(str | SecretSource)."
        ),
    )
    current_datetime: datetime | str | None = Field(
        default_factory=datetime.now,
        description=(
            "Current date and time information to provide to the agent. "
            "Can be a datetime object (which will be formatted as ISO 8601) "
            "or a pre-formatted string. When provided, this information is "
            "included in the system prompt to give the agent awareness of "
            "the current time context. Defaults to the current datetime."
        ),
    )

    @field_validator("skills")
    @classmethod
    def _validate_skills(cls, v: list[Skill], _info):
        if not v:
            return v
        # Check for duplicate skill names
        seen_names = set()
        for skill in v:
            if skill.name in seen_names:
                raise ValueError(f"Duplicate skill name found: {skill.name}")
            seen_names.add(skill.name)
        return v

    @model_validator(mode="after")
    def _load_auto_skills(self):
        """Load user and/or public skills if enabled."""
        if not self.load_user_skills and not self.load_public_skills:
            return self

        auto_skills = load_available_skills(
            work_dir=None,
            include_user=self.load_user_skills,
            include_project=False,
            include_public=self.load_public_skills,
            marketplace_path=self.marketplace_path,
        )

        existing_names = {skill.name for skill in self.skills}
        for name, skill in auto_skills.items():
            if name not in existing_names:
                self.skills.append(skill)
            else:
                logger.warning(
                    f"Skipping auto-loaded skill '{name}' (already in explicit skills)"
                )

        return self

    def _find_relevant_available_skills(
        self,
        query: str,
        skip_skill_names: set[str],
    ) -> list[Skill]:
        query_terms = _extract_relevance_terms(query)
        if not query_terms:
            return []

        scored_skills: list[tuple[int, Skill]] = []
        for skill in self.skills:
            if skill.name in skip_skill_names:
                continue
            if not (skill.is_agentskills_format or skill.trigger is not None):
                continue
            score = _score_relevant_skill(skill, query, query_terms)
            if score < _RELEVANT_SKILL_MIN_SCORE:
                continue
            scored_skills.append((score, skill))

        scored_skills.sort(
            key=lambda item: (
                -item[0],
                0 if item[1].is_agentskills_format else 1,
                item[1].name,
            )
        )
        return [skill for _, skill in scored_skills[:_RELEVANT_SKILL_MAX_SUGGESTIONS]]

    def get_secret_infos(self) -> list[dict[str, str | None]]:
        """Get secret information (name and description) from the secrets field.

        Returns:
            List of dictionaries with 'name' and 'description' keys.
            Returns an empty list if no secrets are configured.
            Description will be None if not available.
        """
        if not self.secrets:
            return []
        secret_infos: list[dict[str, str | None]] = []
        for name, secret_value in self.secrets.items():
            description = None
            if isinstance(secret_value, SecretSource):
                description = secret_value.description
            secret_infos.append({"name": name, "description": description})
        return secret_infos

    def get_formatted_datetime(self) -> str | None:
        """Get formatted datetime string for inclusion in prompts.

        Returns:
            Formatted datetime string, or None if current_datetime is not set.
            If current_datetime is a datetime object, it's formatted as ISO 8601.
            If current_datetime is already a string, it's returned as-is.
        """
        if self.current_datetime is None:
            return None
        if isinstance(self.current_datetime, datetime):
            return self.current_datetime.isoformat()
        return self.current_datetime

    def get_system_message_suffix(
        self,
        llm_model: str | None = None,
        llm_model_canonical: str | None = None,
        additional_secret_infos: list[dict[str, str | None]] | None = None,
    ) -> str | None:
        """Get the system message with repo skill content and custom suffix.

        Custom suffix can typically includes:
        - Repository information (repo name, branch name, PR number, etc.)
        - Runtime information (e.g., available hosts, current date)
        - Conversation instructions (e.g., user preferences, task details)
        - Repository-specific instructions (collected from repo skills)
        - Available skills list (for AgentSkills-format and triggered skills)

        Args:
            llm_model: Optional LLM model name for vendor-specific skill filtering.
            llm_model_canonical: Optional canonical LLM model name.
            additional_secret_infos: Optional list of additional secret info dicts
                (with 'name' and 'description' keys) to merge with agent_context
                secrets. Typically passed from conversation's secret_registry.

        Skill categorization:
        - AgentSkills-format (SKILL.md): Always in <available_skills> (progressive
          disclosure). If has triggers, content is ALSO auto-injected on trigger
          in user prompts.
        - Legacy with trigger=None: Full content in <REPO_CONTEXT> (always active)
        - Legacy with triggers: Listed in <available_skills>, injected on trigger
        """
        # Categorize skills based on format and trigger:
        # - AgentSkills-format: always in available_skills (progressive disclosure)
        # - Legacy: trigger=None -> REPO_CONTEXT, else -> available_skills
        repo_skills: list[Skill] = []
        available_skills: list[Skill] = []

        for s in self.skills:
            if s.is_agentskills_format:
                # AgentSkills: always list (triggers also auto-inject via
                # get_user_message_suffix)
                available_skills.append(s)
            elif s.trigger is None:
                # Legacy OpenHands: no trigger = full content in REPO_CONTEXT
                repo_skills.append(s)
            else:
                # Legacy OpenHands: has trigger = list in available_skills
                available_skills.append(s)

        # Gate vendor-specific repo skills based on model family.
        if llm_model or llm_model_canonical:
            spec = get_model_prompt_spec(llm_model or "", llm_model_canonical)
            family = (spec.family or "").lower()
            if family:
                filtered: list[Skill] = []
                for s in repo_skills:
                    n = (s.name or "").lower()
                    if n == "claude" and not (
                        "anthropic" in family or "claude" in family
                    ):
                        continue
                    if n == "gemini" and not (
                        "gemini" in family or "google_gemini" in family
                    ):
                        continue
                    filtered.append(s)
                repo_skills = filtered

        logger.debug(f"Loaded {len(repo_skills)} repository skills: {repo_skills}")

        # Generate available skills prompt
        available_skills_prompt = ""
        if available_skills:
            available_skills_prompt = to_prompt(available_skills)
            logger.debug(
                f"Generated available skills prompt for {len(available_skills)} skills"
            )

        # Build the workspace context information
        # Merge agent_context secrets with additional secrets from registry
        secret_infos = self.get_secret_infos()
        if additional_secret_infos:
            # Merge: additional secrets override agent_context secrets by name
            secret_dict = {s["name"]: s for s in secret_infos}
            for additional in additional_secret_infos:
                secret_dict[additional["name"]] = additional
            secret_infos = list(secret_dict.values())
        formatted_datetime = self.get_formatted_datetime()
        has_content = (
            repo_skills
            or self.system_message_suffix
            or secret_infos
            or available_skills_prompt
            or formatted_datetime
        )
        if has_content:
            formatted_text = render_template(
                prompt_dir=str(PROMPT_DIR),
                template_name="system_message_suffix.j2",
                repo_skills=repo_skills,
                system_message_suffix=self.system_message_suffix or "",
                secret_infos=secret_infos,
                available_skills_prompt=available_skills_prompt,
                current_datetime=formatted_datetime,
            ).strip()
            return formatted_text
        elif self.system_message_suffix and self.system_message_suffix.strip():
            return self.system_message_suffix.strip()
        return None

    def get_user_message_suffix(
        self, user_message: Message, skip_skill_names: list[str]
    ) -> tuple[TextContent, list[str]] | None:
        """Augment the user’s message with knowledge recalled from skills.

        This works by:
        - Extracting the text content of the user message
        - Matching skill triggers against the query
        - Returning formatted knowledge and triggered skill names if relevant skills were triggered
        """  # noqa: E501

        user_message_suffix = None
        if self.user_message_suffix and self.user_message_suffix.strip():
            user_message_suffix = self.user_message_suffix.strip()

        query = "\n".join(
            c.text for c in user_message.content if isinstance(c, TextContent)
        ).strip()
        recalled_knowledge: list[SkillKnowledge] = []
        # skip empty queries, but still return user_message_suffix if it exists
        if not query:
            if user_message_suffix:
                return TextContent(text=user_message_suffix), []
            return None

        skipped_names = set(skip_skill_names)
        # Search for skill triggers in the query
        for skill in self.skills:
            if not isinstance(skill, Skill):
                continue
            trigger = skill.match_trigger(query)
            if trigger and skill.name not in skipped_names:
                logger.info(
                    "Skill '%s' triggered by keyword '%s'",
                    skill.name,
                    trigger,
                )
                recalled_knowledge.append(
                    SkillKnowledge(
                        name=skill.name,
                        trigger=trigger,
                        content=skill.content,
                        location=skill.source,
                    )
                )

        recalled_skill_names = {knowledge.name for knowledge in recalled_knowledge}
        relevant_skills = self._find_relevant_available_skills(
            query,
            skip_skill_names=skipped_names | recalled_skill_names,
        )

        formatted_sections: list[str] = []
        if recalled_knowledge:
            formatted_sections.append(
                render_template(
                    prompt_dir=str(PROMPT_DIR),
                    template_name="skill_knowledge_info.j2",
                    triggered_agents=recalled_knowledge,
                )
            )
        if relevant_skills:
            logger.info(
                "Suggesting relevant skills for query '%s': %s",
                query,
                [skill.name for skill in relevant_skills],
            )
            formatted_sections.append(_format_relevant_skills_hint(relevant_skills))

        if formatted_sections:
            formatted_skill_text = "\n\n".join(formatted_sections)
            if user_message_suffix:
                formatted_skill_text += "\n" + user_message_suffix
            return TextContent(text=formatted_skill_text), [
                knowledge.name for knowledge in recalled_knowledge
            ]

        if user_message_suffix:
            return TextContent(text=user_message_suffix), []
        return None
