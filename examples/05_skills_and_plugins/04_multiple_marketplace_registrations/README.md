# Multiple Marketplace Registrations

This example demonstrates how to register multiple plugin marketplaces with different auto-load behaviors using `MarketplaceRegistration` and `MarketplaceRegistry`.

## Key Concepts

### MarketplaceRegistration

Declares a marketplace with its source and auto-load setting:

```python
MarketplaceRegistration(
    name="company",                    # Identifier for this registration
    source="github:mycompany/plugins", # Source: GitHub, git URL, or local path
    ref="v2.0.0",                      # Optional: branch, tag, or commit
    repo_path="internal/marketplace",  # Optional: subdirectory for monorepos
    auto_load="all",                   # "all" or None
)
```

### auto_load Behavior

| Setting | Behavior |
|---------|----------|
| `auto_load="all"` | Load all plugins from this marketplace at conversation start |
| `auto_load=None` (default) | Register for resolution but don't auto-load plugins |

### Plugin Resolution

```python
# Explicit marketplace qualifier
source = registry.resolve_plugin("formatter@company")

# Search all registered marketplaces (errors if ambiguous)
source = registry.resolve_plugin("formatter")
```

## Use Cases

1. **Enterprise teams** - Internal marketplace + curated public plugins
2. **Multi-team organizations** - Team-specific + shared company marketplaces
3. **Experimental plugins** - Register but don't auto-load until tested

## Running the Example

```bash
cd examples/05_skills_and_plugins/04_multiple_marketplace_registrations
python main.py
```

## Output

The example demonstrates:
1. Registering multiple marketplaces with different auto-load settings
2. Resolving plugins with explicit and implicit marketplace references
3. Loading plugins from resolved sources
4. Error handling for not found, ambiguous, and unregistered cases
5. Prefetching marketplaces for validation
6. Integration pattern with AgentContext

## Directory Structure

```
04_multiple_marketplace_registrations/
├── marketplaces/                    # Created by the example
│   ├── company-tools/
│   │   └── .plugin/marketplace.json
│   │   └── plugins/formatter/...
│   └── experimental/
│       └── .plugin/marketplace.json
│       └── plugins/beta-tool/...
├── main.py                          # Example code
└── README.md                        # This file
```

## Related

- [02_loading_plugins](../02_loading_plugins/) - Loading individual plugins
- [43_mixed_marketplace_skills](../../01_standalone_sdk/43_mixed_marketplace_skills/) - Single marketplace with mixed sources
- [Plugin documentation](https://docs.all-hands.dev/sdk/guides/plugins)
