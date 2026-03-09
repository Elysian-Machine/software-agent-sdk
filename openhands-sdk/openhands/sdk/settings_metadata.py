from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


SETTINGS_METADATA_KEY = "openhands_settings"
SETTINGS_SECTION_METADATA_KEY = "openhands_settings_section"


class SettingsSectionMetadata(BaseModel):
    key: str
    label: str
    order: int


class SettingsFieldMetadata(BaseModel):
    label: str
    order: int
    widget: Literal["text", "password", "number", "boolean", "select"] | None = None
    placeholder: str | None = None
    advanced: bool = False
    depends_on: tuple[str, ...] = ()
    help_text: str | None = None
    slash_command: str | None = None
