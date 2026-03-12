from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


SETTINGS_METADATA_KEY = "openhands_settings"
SETTINGS_SECTION_METADATA_KEY = "openhands_settings_section"


class SettingProminence(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class SettingsSectionMetadata(BaseModel):
    key: str
    label: str | None = None


class SettingsFieldMetadata(BaseModel):
    label: str | None = None
    prominence: SettingProminence = SettingProminence.MAJOR
    depends_on: tuple[str, ...] = ()
