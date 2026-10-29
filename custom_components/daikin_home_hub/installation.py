"""Installation-dependent entity groups; never writes commissioning settings."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from .models import ModelProfile
from .registers import ALTHERMA_REGISTERS

CONF_DHW_PRESENT = "dhw_present"
CONF_ADDITIONAL_ZONE = "additional_zone"
CONF_CONTROL_METHOD = "control_method"
CONF_COOLING_AVAILABLE = "cooling_available"
INSTALLATION_KEYS = frozenset(
    {
        CONF_DHW_PRESENT,
        CONF_ADDITIONAL_ZONE,
        CONF_CONTROL_METHOD,
        CONF_COOLING_AVAILABLE,
    }
)


class ControlMethod(StrEnum):
    LEAVING_WATER = "leaving_water"
    ROOM_THERMOSTAT = "room_thermostat"
    EXTERNAL_THERMOSTAT = "external_thermostat"


DHW_FIELDS = frozenset(
    {key for key in ALTHERMA_REGISTERS if key.startswith("dhw_")}
    | {"booster_heater_running", "disinfection_running", "three_way_valve"}
)
ADDITIONAL_ZONE_FIELDS = frozenset(
    key for key in ALTHERMA_REGISTERS if key.startswith("additional_")
)
ROOM_THERMOSTAT_FIELDS = frozenset(
    key for key in ALTHERMA_REGISTERS if key.startswith("room_")
)
COOLING_FIELDS = frozenset(
    {key for key in ALTHERMA_REGISTERS if "cooling" in key} | {"operation_mode"}
)


@dataclass(frozen=True)
class Installation:
    """User-declared installation, independent of HA and transport."""

    dhw_present: bool = False
    additional_zone: bool = False
    control_method: ControlMethod = ControlMethod.LEAVING_WATER
    # Profiles include both heating-only and reversible equipment variants.
    # Keep existing cooling exposure unless the user selects heating-only.
    cooling_available: bool = True

    @classmethod
    def from_options(cls, options: Mapping[str, Any]) -> Installation | None:
        """Absent installation options preserve the legacy per-entity policy."""
        if CONF_CONTROL_METHOD not in options:
            return None
        return cls(
            dhw_present=options.get(CONF_DHW_PRESENT, False),
            additional_zone=options.get(CONF_ADDITIONAL_ZONE, False),
            control_method=ControlMethod(options[CONF_CONTROL_METHOD]),
            cooling_available=options.get(CONF_COOLING_AVAILABLE, True),
        )

    def as_options(self) -> dict[str, Any]:
        return asdict(self)

    def active_fields(self, profile: ModelProfile) -> frozenset[str]:
        fields = {key for key in profile.registers if profile.supports(key)}
        if profile.air_to_air:
            return frozenset(fields)
        if not self.dhw_present:
            fields -= DHW_FIELDS
        if not self.additional_zone:
            fields -= ADDITIONAL_ZONE_FIELDS
        if self.control_method != ControlMethod.ROOM_THERMOSTAT:
            fields -= ROOM_THERMOSTAT_FIELDS
        if self.control_method != ControlMethod.EXTERNAL_THERMOSTAT:
            fields.discard("main_thermostat_input")
        if not self.cooling_available:
            fields -= COOLING_FIELDS
        return frozenset(fields)
