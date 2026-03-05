# Mixed Marketplace Skills Example

This example demonstrates how to create a **marketplace that combines local and remote skills**, showing how teams can maintain their own custom skills while also leveraging the public OpenHands skills repository.

## Overview

The example includes:
- A **local skill** (`greeting-helper`) hosted in the `skills/` directory
- Access to **remote skills** from the [OpenHands/extensions](https://github.com/OpenHands/extensions) repository

This pattern is useful for:
- Teams that want to maintain their own custom skills
- Projects that need to combine public skills with internal workflows
- Creating curated skill sets for specific use cases

## Directory Structure

```
43_mixed_marketplace_skills/
├── .plugin/
│   └── marketplace.json     # Marketplace definition (includes local + remote)
├── skills/
│   └── greeting-helper/
│       └── SKILL.md         # Local skill following AgentSkills format
├── main.py                  # Main example script
└── README.md                # This file
```

## Marketplace Definition

The `.plugin/marketplace.json` file defines the marketplace:

```json
{
    "name": "mixed-skills-marketplace",
    "description": "Example marketplace combining local and remote skills",
    "owner": {"name": "OpenHands SDK Examples"},
    "metadata": {
        "pluginRoot": "./skills"
    },
    "plugins": [
        {"name": "greeting-helper", "source": "./greeting-helper"}
    ],
    "dependencies": {
        "OpenHands/extensions": [
            {"name": "github", "source": "OpenHands/extensions/skills/github"}
        ]
    }
}
```

## How It Works

1. **Local Skills Loading**: Skills from `skills/` are loaded using `load_skills_from_dir()`
2. **Remote Skills Loading**: Skills from OpenHands/extensions are loaded using `load_public_skills()`
3. **Skill Merging**: Both are combined with local skills taking precedence
4. **Agent Context**: The combined skill set is provided to the agent

## Running the Example

### Dry Run (No LLM Required)
```bash
python main.py --dry-run
```
This will show the skill loading without making LLM calls.

### Full Run (Requires LLM API Key)
```bash
export LLM_API_KEY=your-api-key
python main.py
```

### Expected Output (Dry Run)
```
================================================================================
Part 1: Loading Local Skills from Directory
================================================================================

Loading local skills from: /path/to/skills

Loaded local skills:
  - greeting-helper: A local skill that helps generate creative greetings

================================================================================
Part 2: Loading Remote Skills from OpenHands/extensions
================================================================================

Loading public skills from https://github.com/OpenHands/extensions...

Loaded 33 public skills from OpenHands/extensions:
  - add-skill: Add an external skill from a GitHub repository...
  - agent-memory: Persist and retrieve repository-specific knowledge...
  ...

================================================================================
Part 3: Combining Local and Remote Skills
================================================================================

Total combined skills: 34
  - Local skills: 1
  - Public skills: 33
```

## Creating Your Own Mixed Marketplace

1. Create a `skills/` directory with your custom skills
2. Add a `.plugin/marketplace.json` to define the marketplace
3. Use `load_skills_from_dir()` for local skills
4. Use `load_public_skills()` for remote skills
5. Combine them in your `AgentContext`

## See Also

- [01_loading_agentskills](../../05_skills_and_plugins/01_loading_agentskills/) - Loading skills from disk
- [03_activate_skill.py](../03_activate_skill.py) - Basic skill activation
- [AgentSkills Specification](https://agentskills.io/specification) - Skill format standard
