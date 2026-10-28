"""Measurements, limits and exact fault codes from the published interface."""

from typing import cast, final, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HomeHubConfigEntry
from .entity import HomeHubEntity
from .registers import Register


def _description(register: Register) -> SensorEntityDescription:
    device_class = {
        "°C": SensorDeviceClass.TEMPERATURE,
        "kW": SensorDeviceClass.POWER,
        "L/min": SensorDeviceClass.VOLUME_FLOW_RATE,
    }.get(register.unit or "")
    if register.options:
        device_class = SensorDeviceClass.ENUM
    return SensorEntityDescription(
        key=register.key,
        translation_key=register.key,
        device_class=device_class,
        native_unit_of_measurement=register.unit,
        state_class=SensorStateClass.MEASUREMENT
        if register.unit and not register.diagnostic
        else None,
        options=list(register.options.values()) if register.options else None,
        entity_category=EntityCategory.DIAGNOSTIC if register.diagnostic else None,
        entity_registry_enabled_default=not register.optional,
        suggested_display_precision=2 if register.unit else None,
    )


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: HomeHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        HomeHubSensor(entry.runtime_data, _description(register))
        for register in entry.runtime_data.device.registers.values()
        if register.platform == "sensor"
    )


@final
class HomeHubSensor(HomeHubEntity[SensorEntityDescription], SensorEntity):
    @override
    def _update_state(self) -> None:
        super()._update_state()
        register = self.coordinator.device.registers[self.entity_description.key]
        self._attr_native_value = (
            register.options.get(cast(int, self.field_value))
            if register.options
            else self.field_value
        )
        if register.options or register.key.startswith("unit_abnormality"):
            self._attr_extra_state_attributes = {
                "raw_code": self.coordinator.data.raw.get(register.space, {}).get(
                    register.address
                )
            }
