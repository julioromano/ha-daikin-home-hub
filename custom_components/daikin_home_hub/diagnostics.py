"""Raw data and failure reasons without endpoint or persistent identifiers."""

from dataclasses import asdict
from typing import Any

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import HomeHubConfigEntry


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant,
    entry: HomeHubConfigEntry,
) -> dict[str, Any]:
    data = entry.runtime_data.data
    return {
        "configuration": {**entry.data, CONF_HOST: "**REDACTED**"},
        "last_update_success": entry.runtime_data.last_update_success,
        "values": data.values,
        "raw_registers": data.raw,
        "unavailable": data.unavailable,
        "bounds": data.bounds,
        "failed_fields": {
            key: asdict(failure) for key, failure in data.failed_fields.items()
        },
        "polled_optional_fields": data.polled_optional_fields,
    }
