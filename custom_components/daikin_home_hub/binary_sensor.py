"""Read-only register flags; only 0 and 1 are valid boolean states."""

from typing import cast, final, override

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
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
        HomeHubBinarySensor(
            entry.runtime_data,
            BinarySensorEntityDescription(
                key=key,
                translation_key=key,
                device_class=BinarySensorDeviceClass.RUNNING,
                entity_registry_enabled_default=not register.optional,
            ),
        )
        for key, register in entry.runtime_data.device.registers.items()
        if register.platform == "binary_sensor"
    )


@final
class HomeHubBinarySensor(
    HomeHubEntity[BinarySensorEntityDescription], BinarySensorEntity
):
    @override
    def _update_state(self) -> None:
        super()._update_state()
        self._attr_is_on = cast(bool | None, self.field_value)
