"""Poll the HA-independent model and translate errors at the HA boundary."""

import logging
from datetime import timedelta
from typing import final, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusUnit

from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN
from .installation import Installation
from .models import MODELS
from .protocol import HomeHub, Snapshot, Value

_LOGGER = logging.getLogger(__name__)
type HomeHubConfigEntry = ConfigEntry[HomeHubCoordinator]


@final
class HomeHubCoordinator(DataUpdateCoordinator[Snapshot]):
    def __init__(
        self, hass: HomeAssistant, entry: HomeHubConfigEntry, unit: ModbusUnit
    ) -> None:
        self.installation = Installation.from_options(entry.options)
        profile = MODELS[entry.data[CONF_MODEL]]
        self.device = HomeHub(
            unit,
            entry.data[CONF_MODEL],
            active_fields=self.installation.active_fields(profile)
            if self.installation
            else None,
        )
        super().__init__(
            hass,
            _LOGGER,
            name=self.device.profile.name,
            config_entry=entry,
            always_update=False,
            update_interval=timedelta(
                seconds=entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
                )
            ),
        )
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=self.device.profile.name,
            manufacturer="Daikin",
            model=self.device.profile.name,
        )

    def entity_enabled_default(self, key: str) -> bool:
        """Installation choices govern new entities; legacy entries retain defaults."""
        return (
            key in self.device.active_fields
            if self.installation
            else not self.device.registers[key].optional
        )

    @override
    async def _async_update_data(self) -> Snapshot:
        try:
            optional = frozenset(self.async_contexts()) & self.device.optional_fields
            return await self.device.async_update(optional)
        except ModbusError as err:
            raise UpdateFailed("Unable to read Daikin HomeHub") from err

    async def async_write(self, key: str, value: Value) -> None:
        try:
            await self.device.async_write(key, value)
        except ValueError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_setting",
                translation_placeholders={"reason": str(err)},
            ) from err
        except ModbusError as err:
            await self.async_refresh()
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="write_failed"
            ) from err
        # Bypass request-refresh's cooldown after an explicit user command.
        await self.async_refresh()
