from openhands.sdk.llm.utils.litellm_provider import LLMProvider
from openhands.sdk.llm.utils.model_features import get_features


def test_llm_provider_parses_nested_openrouter_model():
    provider = LLMProvider.from_model(
        model="openrouter/anthropic/claude-sonnet-4", api_base=None
    )

    assert provider.name == "openrouter"
    assert provider.litellm_model == "anthropic/claude-sonnet-4"
    assert provider.model_names == (
        "openrouter/anthropic/claude-sonnet-4",
        "anthropic/claude-sonnet-4",
    )


def test_llm_provider_parses_bedrock_model():
    provider = LLMProvider.from_model(
        model="bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
        api_base=None,
    )

    assert provider.name == "bedrock"
    assert provider.is_bedrock is True
    assert provider.litellm_model == "anthropic.claude-3-5-sonnet-20241022-v2:0"


def test_llm_provider_handles_unknown_model_without_provider():
    provider = LLMProvider.from_model(model="unknown-model", api_base=None)

    assert provider.name is None
    assert provider.provider_enum is None
    assert provider.litellm_model == "unknown-model"
    assert provider.model_info is None


def test_llm_provider_preserves_raw_prefix_for_unknown_provider_fallback():
    provider = LLMProvider.from_model(model="provider/gpt-4o-mini", api_base=None)

    assert provider.name is None
    assert provider.raw_prefix == "provider"
    assert provider.model_name_for_cost == "gpt-4o-mini"
    assert provider.provider_name_for_cost == "provider"


def test_llm_provider_infers_api_base_from_model_info():
    provider = LLMProvider.from_model(
        model="anthropic/claude-sonnet-4-5-20250929", api_base=None
    )

    assert provider.infer_api_base() == "https://api.anthropic.com"


def test_llm_provider_infers_api_base_from_litellm_defaults():
    provider = LLMProvider.from_model(
        model="mistral/mistral-large-latest", api_base=None
    )

    assert provider.infer_api_base() == "https://api.mistral.ai/v1"


def test_get_features_accepts_provider_object_for_provider_specific_rules():
    azure = LLMProvider.from_model(model="azure/gpt-4.1", api_base=None)
    groq = LLMProvider.from_model(model="groq/kimi-k2-instruct-0905", api_base=None)
    openrouter = LLMProvider.from_model(model="openrouter/minimax-m2", api_base=None)

    assert get_features(azure).supports_prompt_cache_retention is False
    assert get_features(groq).force_string_serializer is True
    assert get_features(openrouter).send_reasoning_content is True
