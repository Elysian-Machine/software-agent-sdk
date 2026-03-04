"""Example: Mixed Marketplace with Local and Remote Skills

This example demonstrates how to create a marketplace that includes both:
1. Local skills hosted in your project directory
2. Remote skills from the OpenHands/extensions repository

This pattern is useful for teams that want to:
- Maintain their own custom skills locally
- Leverage the public OpenHands skills repository
- Create a curated skill set for their specific workflows

The marketplace is defined in .plugin/marketplace.json and includes:
- greeting-helper: A local skill in ./local_skills/greeting-helper/
- github: A remote skill from OpenHands/extensions

Directory Structure:
    43_mixed_marketplace_skills/
    ├── .plugin/
    │   └── marketplace.json     # Marketplace definition
    ├── local_skills/
    │   └── greeting-helper/
    │       └── SKILL.md         # Local skill content
    ├── main.py                  # This file
    └── README.md                # Documentation

Usage:
    # With LLM_API_KEY set
    python main.py

    # Or run without LLM to just see the skill loading
    python main.py --dry-run
"""

import os
import sys
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import LLM, Agent, AgentContext, Conversation
from openhands.sdk.context.skills import (
    Skill,
    load_public_skills,
    load_skills_from_dir,
)
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool


def main():
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    local_skills_dir = script_dir / "local_skills"

    # =========================================================================
    # Part 1: Loading Local Skills
    # =========================================================================
    print("=" * 80)
    print("Part 1: Loading Local Skills from Directory")
    print("=" * 80)

    print(f"\nLoading local skills from: {local_skills_dir}")

    # Load skills from the local directory
    # This loads any SKILL.md files following the AgentSkills standard
    repo_skills, knowledge_skills, local_skills = load_skills_from_dir(local_skills_dir)

    print("\nLoaded local skills:")
    for name, skill in local_skills.items():
        print(f"  - {name}: {skill.description or 'No description'}")
        if skill.trigger:
            # KeywordTrigger has 'keywords', TaskTrigger has 'triggers'
            trigger_values = getattr(skill.trigger, "keywords", None) or getattr(
                skill.trigger, "triggers", None
            )
            if trigger_values:
                print(f"    Triggers: {trigger_values}")

    # =========================================================================
    # Part 2: Loading Remote Skills from OpenHands/extensions
    # =========================================================================
    print("\n" + "=" * 80)
    print("Part 2: Loading Remote Skills from OpenHands/extensions")
    print("=" * 80)

    print("\nLoading public skills from https://github.com/OpenHands/extensions...")

    # Load public skills from the OpenHands extensions repository
    # This pulls from the default marketplace at OpenHands/extensions
    public_skills = load_public_skills()

    print(f"\nLoaded {len(public_skills)} public skills from OpenHands/extensions:")
    for skill in public_skills[:5]:  # Show first 5
        desc = skill.description[:50] + "..." if skill.description else "No description"
        print(f"  - {skill.name}: {desc}")
    if len(public_skills) > 5:
        print(f"  ... and {len(public_skills) - 5} more")

    # =========================================================================
    # Part 3: Combining Local and Remote Skills
    # =========================================================================
    print("\n" + "=" * 80)
    print("Part 3: Combining Local and Remote Skills")
    print("=" * 80)

    # Combine all skills for the agent context
    # Local skills take precedence over public skills with the same name
    combined_skills: list[Skill] = []

    # Add public skills first (lower precedence)
    public_skill_names = {s.name for s in public_skills}
    combined_skills.extend(public_skills)

    # Add local skills (higher precedence - will override if same name)
    for name, skill in local_skills.items():
        if name in public_skill_names:
            # Remove the public skill and add the local one
            combined_skills = [s for s in combined_skills if s.name != name]
            print(f"  Local skill '{name}' overrides public skill")
        combined_skills.append(skill)

    print(f"\nTotal combined skills: {len(combined_skills)}")
    print(f"  - Local skills: {len(local_skills)}")
    print(f"  - Public skills: {len(public_skills)}")

    # Show the combined skill set
    local_names = set(local_skills.keys())
    print("\nSkills by source:")
    print(f"  Local: {list(local_names)}")
    print(f"  Remote (first 5): {[s.name for s in public_skills[:5]]}")

    # =========================================================================
    # Part 4: Using Skills with an Agent (Optional)
    # =========================================================================
    print("\n" + "=" * 80)
    print("Part 4: Using Skills with an Agent")
    print("=" * 80)

    # Check for dry-run mode
    if "--dry-run" in sys.argv:
        print("\n[Dry run mode - skipping agent interaction]")
        print("To run with an agent, remove --dry-run and set LLM_API_KEY")
        return

    # Check for API key
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        print("\nSkipping agent demo (LLM_API_KEY not set)")
        print("To run the full demo, set the LLM_API_KEY environment variable:")
        print("  export LLM_API_KEY=your-api-key")
        return

    # Configure LLM
    model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
    print(f"\nUsing model: {model}")

    llm = LLM(
        usage_id="mixed-skills-demo",
        model=model,
        api_key=SecretStr(api_key),
        base_url=os.getenv("LLM_BASE_URL"),
    )

    # Create agent context with combined skills
    agent_context = AgentContext(
        skills=combined_skills,
        # Disable automatic public skills loading since we already loaded them
        load_public_skills=False,
    )

    # Create agent with tools
    tools = [
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ]
    agent = Agent(llm=llm, tools=tools, agent_context=agent_context)

    # Create conversation
    conversation = Conversation(agent=agent, workspace=os.getcwd())

    # Test the local skill (triggered by "greeting" keyword)
    print("\n--- Testing Local Skill (greeting-helper) ---")
    print("Sending: 'Hello! Can you help me greet someone?'")
    conversation.send_message("Hello! Can you help me greet someone?")
    conversation.run()

    # Test the remote skill (triggered by "github" keyword)
    print("\n--- Testing Remote Skill (github from OpenHands/extensions) ---")
    print("Sending: 'Tell me about GitHub best practices'")
    conversation.send_message("Tell me about GitHub best practices")
    conversation.run()

    print(f"\nTotal cost: ${llm.metrics.accumulated_cost:.4f}")
    print(f"EXAMPLE_COST: {llm.metrics.accumulated_cost:.4f}")


if __name__ == "__main__":
    main()
