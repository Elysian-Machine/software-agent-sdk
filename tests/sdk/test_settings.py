from openhands.sdk import LLM, AgentSettings, SettingProminence


def test_agent_settings_export_schema_groups_sections() -> None:
    schema = AgentSettings.export_schema()

    assert schema.model_name == "AgentSettings"
    assert [section.key for section in schema.sections] == [
        "llm",
        "condenser",
        "critic",
    ]

    llm_fields = {field.key: field for field in schema.sections[0].fields}
    assert set(llm_fields) == {f"llm.{name}" for name in LLM.model_fields}
    assert llm_fields["llm.model"].required is True
    assert llm_fields["llm.model"].value_type == "string"
    assert llm_fields["llm.api_key"].label == "API Key"
    assert llm_fields["llm.api_key"].value_type == "string"
    assert llm_fields["llm.api_key"].required is False
    assert llm_fields["llm.api_key"].secret is True
    assert llm_fields["llm.reasoning_effort"].choices[0].value == "low"
    assert llm_fields["llm.fallback_strategy"].value_type == "object"
    assert llm_fields["llm.litellm_extra_body"].value_type == "object"
    assert llm_fields["llm.litellm_extra_body"].default == {}

    condenser_fields = {field.key: field for field in schema.sections[1].fields}
    assert (
        condenser_fields["condenser.enabled"].prominence is SettingProminence.CRITICAL
    )
    assert condenser_fields["condenser.max_size"].depends_on == ["condenser.enabled"]
    assert condenser_fields["condenser.max_size"].prominence is SettingProminence.MINOR

    critic_fields = {field.key: field for field in schema.sections[2].fields}
    assert critic_fields["critic.mode"].value_type == "string"
    assert [choice.value for choice in critic_fields["critic.mode"].choices] == [
        "finish_and_message",
        "all_actions",
    ]
    assert critic_fields["critic.mode"].depends_on == ["critic.enabled"]
    assert critic_fields["critic.mode"].prominence is SettingProminence.MINOR
    assert critic_fields["critic.threshold"].depends_on == [
        "critic.enabled",
        "critic.enable_iterative_refinement",
    ]
    assert critic_fields["critic.threshold"].prominence is SettingProminence.MINOR
