"""Daikin HomeHub Modbus TCP integration."""

from awesomeversion import AwesomeVersion
from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PORT, __version__
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams

from .const import CONF_UNIT_ID, DOMAIN, MIN_HA_VERSION, PLATFORMS
from .coordinator import HomeHubConfigEntry, HomeHubCoordinator
from .models import MODELS


async def async_setup_entry(hass: HomeAssistant, entry: HomeHubConfigEntry) -> bool:
    """HA owns the shared socket and releases this entry's hold on unload."""
    if AwesomeVersion(__version__) < AwesomeVersion(MIN_HA_VERSION):
        raise ConfigEntryError(f"Requires Home Assistant {MIN_HA_VERSION} or newer")
    if entry.data[CONF_MODEL] not in MODELS:
        raise ConfigEntryError(f"Unsupported {DOMAIN} model")
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    coordinator = HomeHubCoordinator(hass, entry, unit)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # Only prune our obsolete fields after a successful refresh. Reconfiguration
    # keeps common identities even when their register address changes by map.
    prefix = f"{entry.entry_id}_"
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            entity.platform == DOMAIN
            and entity.unique_id.startswith(prefix)
            and entity.unique_id.removeprefix(prefix)
            not in coordinator.device.registers
        ):
            registry.async_remove(entity.entity_id)
        elif (
            entity.platform == DOMAIN
            and entity.unique_id.startswith(prefix)
            and coordinator.installation is not None
        ):
            key = entity.unique_id.removeprefix(prefix)
            if (
                key not in coordinator.device.active_fields
                and entity.disabled_by is None
            ):
                _ = registry.async_update_entity(
                    entity.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
                )
            elif (
                key in coordinator.device.active_fields
                and entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
            ):
                _ = registry.async_update_entity(entity.entity_id, disabled_by=None)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Enabled optional entities restored by the registry now have contexts.
    await coordinator.async_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HomeHubConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
