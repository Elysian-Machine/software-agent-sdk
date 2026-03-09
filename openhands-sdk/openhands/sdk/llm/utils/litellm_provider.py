from __future__ import annotations

import warnings
from dataclasses import dataclass
from functools import cached_property
from typing import Any, cast


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import litellm
    from litellm.types.utils import LlmProviders
    from litellm.utils import ProviderConfigManager


@dataclass(frozen=True)
class LLMProvider:
    """LiteLLM provider metadata derived from a raw model string.

    This keeps the original user-facing model string, while also exposing the
    provider-specific model identifier LiteLLM resolved internally.
    """

    raw_model: str
    requested_api_base: str | None
    litellm_model: str
    name: str | None
    dynamic_api_key: str | None
    resolved_api_base: str | None

    @classmethod
    def from_model(cls, *, model: str, api_base: str | None) -> LLMProvider:
        """Parse a model string using LiteLLM's provider inference logic."""
        try:
            get_llm_provider = cast(Any, litellm).get_llm_provider
            parsed_model, provider_name, dynamic_key, resolved_api_base = (
                get_llm_provider(
                    model=model,
                    custom_llm_provider=None,
                    api_base=api_base,
                    api_key=None,
                )
            )
        except Exception:
            parsed_model = model
            provider_name = None
            dynamic_key = None
            resolved_api_base = api_base

        return cls(
            raw_model=model,
            requested_api_base=api_base,
            litellm_model=parsed_model,
            name=provider_name,
            dynamic_api_key=dynamic_key,
            resolved_api_base=resolved_api_base,
        )

    @cached_property
    def provider_enum(self) -> LlmProviders | None:
        if self.name is None:
            return None

        try:
            return LlmProviders(self.name)
        except ValueError:
            return None

    @cached_property
    def model_info(self) -> Any | None:
        if self.provider_enum is None:
            return None

        try:
            return ProviderConfigManager.get_provider_model_info(
                self.litellm_model, self.provider_enum
            )
        except Exception:
            return None

    @property
    def is_bedrock(self) -> bool:
        return self.name == "bedrock"

    @property
    def raw_prefix(self) -> str | None:
        if "/" not in self.raw_model:
            return None

        prefix, remainder = self.raw_model.split("/", 1)
        if not prefix or not remainder:
            return None
        return prefix

    @property
    def raw_model_without_prefix(self) -> str:
        if self.raw_prefix is None:
            return self.raw_model
        return self.raw_model.split("/", 1)[1]

    @property
    def model_names(self) -> tuple[str, ...]:
        """Return the useful model-name variants for downstream matching."""
        names = [self.raw_model]
        if self.litellm_model != self.raw_model:
            names.append(self.litellm_model)
        if self.name is not None:
            names.append(f"{self.name}/{self.litellm_model}")
        return tuple(dict.fromkeys(names))

    @property
    def provider_name_for_cost(self) -> str | None:
        return self.name or self.raw_prefix

    @property
    def model_name_for_cost(self) -> str:
        if self.name is not None:
            return self.litellm_model
        if self.raw_prefix is not None:
            return self.raw_model_without_prefix
        return self.litellm_model

    def infer_api_base(self) -> str | None:
        """Infer a provider API base without reimplementing provider logic."""
        try:
            get_api_base = cast(Any, litellm).get_api_base
            api_base = get_api_base(self.raw_model, {})
            if api_base:
                return cast(str, api_base)
        except Exception:
            pass

        if self.model_info is not None and hasattr(self.model_info, "get_api_base"):
            try:
                api_base = self.model_info.get_api_base()
            except NotImplementedError:
                api_base = None
            except Exception:
                api_base = None
            if api_base:
                return cast(str, api_base)

        return self.resolved_api_base


def infer_litellm_provider(*, model: str, api_base: str | None) -> str | None:
    """Infer the LiteLLM provider for a given model.

    This delegates to LiteLLM's provider inference logic (which includes model
    list lookups like Bedrock's regional model identifiers).
    """

    return LLMProvider.from_model(model=model, api_base=api_base).name
