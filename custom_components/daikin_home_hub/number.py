"""Numeric controls with fresh device-dependent bounds."""

from typing import cast, final, override

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HomeHubConfigEntry
from .entity import HomeHubEntity


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: HomeHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        HomeHubNumber(
            entry.runtime_data,
            NumberEntityDescription(
                key=key,
                translation_key=key,
                entity_registry_enabled_default=not register.optional,
                device_class=NumberDeviceClass.POWER
                if register.unit == "kW"
                else NumberDeviceClass.TEMPERATURE,
                native_unit_of_measurement=register.unit,
                native_step=register.step,
                mode=NumberMode.BOX,
            ),
        )
        for key, register in entry.runtime_data.device.registers.items()
        if register.platform == "number"
    )


@final
class HomeHubNumber(HomeHubEntity[NumberEntityDescription], NumberEntity):
    @override
    def _update_state(self) -> None:
        super()._update_state()
        self._attr_native_value = cast(float | None, self.field_value)
        # No guessed fallback range: an unavailable control has a neutral range.
        limits = self.coordinator.data.bounds.get(self.entity_description.key, (0, 0))
        self._attr_native_min_value, self._attr_native_max_value = limits

    @override
    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write(self.entity_description.key, value)
