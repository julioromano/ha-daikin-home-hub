"""Documented enumerated commands with translated option names."""

from typing import cast, final, override

from homeassistant.components.select import SelectEntity, SelectEntityDescription
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
        HomeHubSelect(
            entry.runtime_data,
            SelectEntityDescription(
                key=key,
                translation_key=key,
                entity_registry_enabled_default=not register.optional,
                options=list(register.options.values()) if register.options else [],
            ),
        )
        for key, register in entry.runtime_data.device.registers.items()
        if register.platform == "select"
    )


@final
class HomeHubSelect(HomeHubEntity[SelectEntityDescription], SelectEntity):
    @override
    def _update_state(self) -> None:
        super()._update_state()
        options = self.coordinator.device.registers[self.entity_description.key].options
        assert options is not None
        self._attr_current_option = options.get(cast(int, self.field_value))

    @override
    async def async_select_option(self, option: str) -> None:
        options = self.coordinator.device.registers[self.entity_description.key].options
        assert options is not None
        value = next(key for key, label in options.items() if label == option)
        await self.coordinator.async_write(self.entity_description.key, value)
