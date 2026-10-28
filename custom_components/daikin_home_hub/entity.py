"""Shared identity and field-level availability for every platform."""

from typing import override

from homeassistant.core import callback
from homeassistant.helpers.device_registry import ChildDeviceInfo, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import BaseCoordinatorEntity

from .coordinator import HomeHubCoordinator
from .protocol import Value


class HomeHubEntity[DescriptionT: EntityDescription](
    BaseCoordinatorEntity[HomeHubCoordinator]
):
    _attr_has_entity_name: bool = True

    def __init__(
        self, coordinator: HomeHubCoordinator, description: DescriptionT
    ) -> None:
        super().__init__(coordinator, context=description.key)
        self.entity_description: DescriptionT = description  # pyright: ignore[reportIncompatibleVariableOverride]
        assert coordinator.config_entry is not None
        self._attr_unique_id: str | None = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )
        self._attr_device_info: DeviceInfo | ChildDeviceInfo | None = (
            coordinator.device_info
        )
        self._update_state()

    @property
    def field_value(self) -> Value:
        return self.coordinator.data.values.get(self.entity_description.key)

    @callback
    def _update_state(self) -> None:
        key = self.entity_description.key
        self._attr_available: bool = (
            self.coordinator.last_update_success
            and self.field_value is not None
            and key not in self.coordinator.data.unavailable
        )

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        self._update_state()
        self.async_write_ha_state()

    @override
    async def async_update(self) -> None:
        if self.enabled:
            await self.coordinator.async_request_refresh()
