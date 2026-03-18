"""Example: Multiple Marketplace Registrations

This example demonstrates how to register multiple plugin marketplaces
with different auto-load behaviors using MarketplaceRegistration and
MarketplaceRegistry.

Key concepts:
1. MarketplaceRegistration - Declares a marketplace with source and auto-load setting
2. MarketplaceRegistry - Manages registered marketplaces with lazy fetching and resolution
3. auto_load="all" - Load all plugins at conversation start
4. auto_load=None - Register for resolution but don't auto-load

Use cases:
- Enterprise teams with internal + public marketplaces
- Curated plugin sets from multiple sources
- Experimental plugins registered but not auto-loaded

Plugin resolution:
- "plugin-name@marketplace" - Explicit marketplace reference
- "plugin-name" - Search all registered marketplaces (errors if ambiguous)

Directory Structure:
    04_multiple_marketplace_registrations/
    ├── marketplaces/
    │   ├── company-tools/          # Internal company marketplace
    │   │   └── .plugin/
    │   │       └── marketplace.json
    │   │   └── plugins/
    │   │       └── formatter/
    │   │           └── .plugin/
    │   │               └── plugin.json
    │   │           └── skills/
    │   │               └── SKILL.md
    │   └── experimental/           # Experimental marketplace
    │       └── .plugin/
    │           └── marketplace.json
    │       └── plugins/
    │           └── beta-tool/
    │               └── .plugin/
    │                   └── plugin.json
    │               └── skills/
    │                   └── SKILL.md
    └── main.py
"""

import json
from pathlib import Path

from openhands.sdk.plugin import (
    MarketplaceRegistration,
    MarketplaceRegistry,
    Plugin,
    PluginNotFoundError,
    AmbiguousPluginError,
)


script_dir = Path(__file__).parent


def setup_example_marketplaces() -> tuple[Path, Path]:
    """Create example marketplace directories for this demo.

    In production, these would be:
    - GitHub repos: github:company/internal-tools
    - Git URLs: https://gitlab.internal/team/plugins.git
    - Local paths: /opt/company/marketplaces/approved
    """
    marketplaces_dir = script_dir / "marketplaces"

    # Create company-tools marketplace
    company_mp = marketplaces_dir / "company-tools"
    company_meta = company_mp / ".plugin"
    company_meta.mkdir(parents=True, exist_ok=True)

    company_manifest = {
        "name": "company-tools",
        "owner": {"name": "DevOps Team", "email": "devops@company.com"},
        "description": "Internal company plugins for development workflows",
        "plugins": [
            {
                "name": "formatter",
                "source": "./plugins/formatter",
                "description": "Company code formatter with internal style rules",
            },
        ],
        "skills": [],
    }
    (company_meta / "marketplace.json").write_text(json.dumps(company_manifest, indent=2))

    # Create formatter plugin
    formatter_dir = company_mp / "plugins" / "formatter"
    formatter_meta = formatter_dir / ".plugin"
    formatter_meta.mkdir(parents=True, exist_ok=True)
    (formatter_meta / "plugin.json").write_text(json.dumps({
        "name": "formatter",
        "version": "2.1.0",
        "description": "Company code formatter with internal style rules",
    }, indent=2))

    formatter_skills = formatter_dir / "skills"
    formatter_skills.mkdir(exist_ok=True)
    (formatter_skills / "SKILL.md").write_text("""---
name: formatter-skill
description: Code formatting with company standards
---

# Company Formatter Skill

Apply company code style rules to your project.
""")

    # Create experimental marketplace
    experimental_mp = marketplaces_dir / "experimental"
    experimental_meta = experimental_mp / ".plugin"
    experimental_meta.mkdir(parents=True, exist_ok=True)

    experimental_manifest = {
        "name": "experimental",
        "owner": {"name": "R&D Team"},
        "description": "Experimental plugins - use at your own risk",
        "plugins": [
            {
                "name": "beta-tool",
                "source": "./plugins/beta-tool",
                "description": "Experimental AI-assisted refactoring",
            },
        ],
        "skills": [],
    }
    (experimental_meta / "marketplace.json").write_text(
        json.dumps(experimental_manifest, indent=2)
    )

    # Create beta-tool plugin
    beta_dir = experimental_mp / "plugins" / "beta-tool"
    beta_meta = beta_dir / ".plugin"
    beta_meta.mkdir(parents=True, exist_ok=True)
    (beta_meta / "plugin.json").write_text(json.dumps({
        "name": "beta-tool",
        "version": "0.1.0-beta",
        "description": "Experimental AI-assisted refactoring",
    }, indent=2))

    beta_skills = beta_dir / "skills"
    beta_skills.mkdir(exist_ok=True)
    (beta_skills / "SKILL.md").write_text("""---
name: beta-tool-skill
description: AI-assisted refactoring (experimental)
---

# Beta Tool Skill

Experimental AI-assisted code refactoring. Use with caution.
""")

    return company_mp, experimental_mp


def demo_registration(company_mp: Path, experimental_mp: Path) -> MarketplaceRegistry:
    """Demo 1: Register multiple marketplaces with different auto-load settings."""
    print("\n" + "=" * 60)
    print("DEMO 1: Registering Multiple Marketplaces")
    print("=" * 60)

    registry = MarketplaceRegistry([
        # Company tools: auto-load all plugins
        MarketplaceRegistration(
            name="company",
            source=str(company_mp),
            auto_load="all",  # Load at conversation start
        ),
        # Experimental: register but don't auto-load
        MarketplaceRegistration(
            name="experimental",
            source=str(experimental_mp),
            # auto_load=None (default) - available for resolution but not auto-loaded
        ),
    ])

    print("\nRegistered marketplaces:")
    for name, reg in registry.registrations.items():
        auto_load_status = "auto-load" if reg.auto_load == "all" else "on-demand"
        print(f"  - {name}: {reg.source} ({auto_load_status})")

    auto_load_regs = registry.get_auto_load_registrations()
    print(f"\nMarketplaces with auto_load='all': {[r.name for r in auto_load_regs]}")

    return registry


def demo_plugin_resolution(registry: MarketplaceRegistry) -> None:
    """Demo 2: Resolve plugins from registered marketplaces."""
    print("\n" + "=" * 60)
    print("DEMO 2: Resolving Plugins")
    print("=" * 60)

    # Resolve with explicit marketplace qualifier
    print("\n1. Explicit marketplace qualifier:")
    source = registry.resolve_plugin("formatter@company")
    print(f"   'formatter@company' -> {source.source}")

    source = registry.resolve_plugin("beta-tool@experimental")
    print(f"   'beta-tool@experimental' -> {source.source}")

    # Resolve without qualifier (unique name)
    print("\n2. Search all marketplaces (unique names):")
    source = registry.resolve_plugin("formatter")
    print(f"   'formatter' -> {source.source}")

    # List plugins from specific marketplace
    print("\n3. List plugins from 'company' marketplace:")
    plugins = registry.list_plugins("company")
    for name in plugins:
        print(f"   - {name}")

    # List all plugins across all marketplaces
    print("\n4. List plugins from all marketplaces:")
    all_plugins = registry.list_plugins()
    for name in all_plugins:
        print(f"   - {name}")


def demo_plugin_loading(registry: MarketplaceRegistry) -> None:
    """Demo 3: Load plugins using resolved sources."""
    print("\n" + "=" * 60)
    print("DEMO 3: Loading Plugins from Resolved Sources")
    print("=" * 60)

    # Resolve and load a plugin
    source = registry.resolve_plugin("formatter@company")
    plugin = Plugin.load(source.source)

    print(f"\nLoaded plugin: {plugin.manifest.name}")
    print(f"  Version: {plugin.manifest.version}")
    print(f"  Description: {plugin.manifest.description}")
    print(f"  Skills: {len(plugin.skills)}")
    for skill in plugin.skills:
        print(f"    - {skill.name}: {skill.description}")


def demo_error_handling(registry: MarketplaceRegistry, experimental_mp: Path) -> None:
    """Demo 4: Error handling for resolution failures."""
    print("\n" + "=" * 60)
    print("DEMO 4: Error Handling")
    print("=" * 60)

    # Plugin not found
    print("\n1. Plugin not found:")
    try:
        registry.resolve_plugin("nonexistent@company")
    except PluginNotFoundError as e:
        print(f"   PluginNotFoundError: {e}")

    # Marketplace not registered
    print("\n2. Marketplace not registered:")
    try:
        registry.resolve_plugin("some-plugin@unknown")
    except Exception as e:
        print(f"   {type(e).__name__}: {e}")

    # Ambiguous plugin (add duplicate to demonstrate)
    print("\n3. Ambiguous plugin name (simulated):")
    # Create a temporary registry with duplicate plugin names
    temp_registry = MarketplaceRegistry([
        MarketplaceRegistration(name="mp1", source=str(experimental_mp)),
        MarketplaceRegistration(name="mp2", source=str(experimental_mp)),
    ])
    try:
        temp_registry.resolve_plugin("beta-tool")
    except AmbiguousPluginError as e:
        print(f"   AmbiguousPluginError: {e}")


def demo_prefetch(registry: MarketplaceRegistry) -> None:
    """Demo 5: Eager prefetching for validation."""
    print("\n" + "=" * 60)
    print("DEMO 5: Prefetching Marketplaces")
    print("=" * 60)

    print(f"\nCache before prefetch: {len(registry._cache)} entries")

    # Prefetch all registered marketplaces
    registry.prefetch_all()

    print(f"Cache after prefetch: {len(registry._cache)} entries")
    print("Cached marketplaces:")
    for name in registry._cache:
        marketplace, path = registry._cache[name]
        print(f"  - {name}: {len(marketplace.plugins)} plugins")


def demo_conversation_integration() -> None:
    """Demo 6: How this integrates with AgentContext (conceptual)."""
    print("\n" + "=" * 60)
    print("DEMO 6: Integration with AgentContext")
    print("=" * 60)

    print("""
In a real application, you would configure AgentContext:

    from openhands.sdk import Agent
    from openhands.sdk.context import AgentContext
    from openhands.sdk.plugin import MarketplaceRegistration

    context = AgentContext(
        registered_marketplaces=[
            MarketplaceRegistration(
                name="public",
                source="github:OpenHands/extensions",
                auto_load="all",
            ),
            MarketplaceRegistration(
                name="company",
                source="github:mycompany/internal-plugins",
                ref="v2.0.0",
                auto_load="all",
            ),
            MarketplaceRegistration(
                name="experimental",
                source="github:mycompany/experimental",
                # Not auto-loaded, but available for explicit use
            ),
        ],
    )

    agent = Agent(llm=llm, agent_context=context)

The SDK will:
1. Fetch marketplaces with auto_load="all" at conversation start
2. Load all plugins from those marketplaces
3. Keep other marketplaces registered for on-demand resolution
""")


if __name__ == "__main__":
    # Setup example marketplace directories
    company_mp, experimental_mp = setup_example_marketplaces()
    print(f"Created example marketplaces in: {script_dir / 'marketplaces'}")

    # Run demos
    registry = demo_registration(company_mp, experimental_mp)
    demo_plugin_resolution(registry)
    demo_plugin_loading(registry)
    demo_error_handling(registry, experimental_mp)
    demo_prefetch(registry)
    demo_conversation_integration()

    print("\n" + "=" * 60)
    print("EXAMPLE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("EXAMPLE_COST: 0")
