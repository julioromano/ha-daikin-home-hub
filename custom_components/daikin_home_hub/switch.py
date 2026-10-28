"""Read/write 0/1 holding registers; HomeHub does not use coils here."""

from typing import Any, cast, final, override

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
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
        HomeHubSwitch(
            entry.runtime_data,
            SwitchEntityDescription(
                key=key,
                translation_key=key,
                entity_registry_enabled_default=not register.optional,
            ),
        )
        for key, register in entry.runtime_data.device.registers.items()
        if register.platform == "switch"
    )


@final
class HomeHubSwitch(HomeHubEntity[SwitchEntityDescription], SwitchEntity):
    @override
    def _update_state(self) -> None:
        super()._update_state()
        self._attr_is_on = cast(bool | None, self.field_value)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self.entity_description.key, True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self.entity_description.key, False)
