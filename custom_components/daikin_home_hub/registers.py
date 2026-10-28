"""Entity semantics for EKRHH 4P744838-1E (2026.01), pp. 41-44 and 49.

Offsets remain one-based decimal here so the inventory can be audited against
the manual. Protocol components use zero-based PDU addresses.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

type Space = Literal["input", "holding"]
type Platform = Literal["sensor", "binary_sensor", "number", "select", "switch"]

OPERATION_MODES = {0: "auto", 1: "heating", 2: "cooling"}
WEATHER_MODES = {
    0: "fixed",
    1: "weather_dependent",
    2: "fixed_scheduled",
    3: "weather_dependent_scheduled",
}
SMART_GRID_MODES = {
    0: "free_running",
    1: "forced_off",
    2: "recommended_on",
    3: "forced_on",
}


@dataclass(frozen=True)
class Register:
    """Public field metadata, independent of Home Assistant."""

    key: str
    offset: int
    space: Space
    platform: Platform
    name: str
    unit: str | None = None
    optional: bool = False
    diagnostic: bool = False
    minimum: float | None = None
    maximum: float | None = None
    step: float = 1
    limits: tuple[str, str] | None = None
    options: Mapping[int, str] | None = None
    page: int = 43

    @property
    def address(self) -> int:
        return self.offset - 1


def _number(
    key: str,
    offset: int,
    name: str,
    *,
    optional: bool = False,
    minimum: float | None = None,
    maximum: float | None = None,
    limits: tuple[str, str] | None = None,
    power: bool = False,
    page: int = 41,
) -> Register:
    return Register(
        key,
        offset,
        "holding",
        "number",
        name,
        "kW" if power else "°C",
        optional,
        minimum=minimum,
        maximum=maximum,
        step=0.01 if power else 1,
        limits=limits,
        page=page,
    )


def _select(
    key: str,
    offset: int,
    name: str,
    options: Mapping[int, str],
    *,
    optional: bool = False,
    page: int = 41,
) -> Register:
    return Register(
        key,
        offset,
        "holding",
        "select",
        name,
        optional=optional,
        options=MappingProxyType(dict(options)),
        page=page,
    )


def _switch(
    key: str, offset: int, name: str, *, optional: bool = False, page: int = 41
) -> Register:
    return Register(
        key, offset, "holding", "switch", name, optional=optional, page=page
    )


def _sensor(
    key: str,
    offset: int,
    name: str,
    *,
    unit: str | None = None,
    optional: bool = False,
    diagnostic: bool = False,
    options: Mapping[int, str] | None = None,
    page: int = 43,
) -> Register:
    return Register(
        key,
        offset,
        "input",
        "sensor",
        name,
        unit,
        optional,
        diagnostic,
        options=MappingProxyType(dict(options)) if options is not None else None,
        page=page,
    )


def _binary(key: str, offset: int, name: str, *, optional: bool = False) -> Register:
    return Register(key, offset, "input", "binary_sensor", name, optional=optional)


_ALTHERMA = [
    _number(
        "main_heating_setpoint",
        1,
        "Main heating water setpoint",
        limits=("main_heating_lower_limit", "main_heating_upper_limit"),
    ),
    _number(
        "main_cooling_setpoint",
        2,
        "Main cooling water setpoint",
        limits=("main_cooling_lower_limit", "main_cooling_upper_limit"),
    ),
    _select("operation_mode", 3, "Requested operation mode", OPERATION_MODES),
    _switch("space_conditioning", 4, "Space heating/cooling"),
    _number(
        "room_heating_setpoint",
        6,
        "Room heating setpoint",
        optional=True,
        minimum=12,
        maximum=30,
        limits=("room_heating_lower_limit", "room_heating_upper_limit"),
    ),
    _number(
        "room_cooling_setpoint",
        7,
        "Room cooling setpoint",
        optional=True,
        minimum=15,
        maximum=35,
        limits=("room_cooling_lower_limit", "room_cooling_upper_limit"),
    ),
    _switch("quiet_mode", 9, "Quiet mode"),
    _number(
        "dhw_reheat_setpoint",
        10,
        "DHW reheat setpoint",
        optional=True,
        minimum=30,
        maximum=60,
    ),
    _switch("dhw_reheat", 12, "DHW reheat", optional=True),
    _switch("dhw_booster", 13, "DHW powerful mode", optional=True),
    _select("main_weather_mode", 53, "Main weather dependent mode", WEATHER_MODES),
    _number(
        "main_heating_offset",
        54,
        "Main weather dependent heating offset",
        minimum=-10,
        maximum=10,
    ),
    _number(
        "main_cooling_offset",
        55,
        "Main weather dependent cooling offset",
        minimum=-10,
        maximum=10,
    ),
    _select("smart_grid_mode", 56, "Smart Grid mode", SMART_GRID_MODES),
    _number(
        "buffering_power_limit",
        57,
        "Buffering power limit",
        power=True,
        minimum=0,
        maximum=20,
    ),
    _number(
        "general_power_limit",
        58,
        "General power limit",
        power=True,
        minimum=0,
        maximum=20,
    ),
    _switch(
        "main_thermostat_input", 59, "Main thermostat input A", optional=True, page=42
    ),
    _switch(
        "additional_thermostat_input",
        61,
        "Additional thermostat input A",
        optional=True,
        page=42,
    ),
    _number(
        "additional_heating_setpoint",
        63,
        "Additional heating water setpoint",
        optional=True,
        page=42,
        limits=("additional_heating_lower_limit", "additional_heating_upper_limit"),
    ),
    _number(
        "additional_cooling_setpoint",
        64,
        "Additional cooling water setpoint",
        optional=True,
        page=42,
        limits=("additional_cooling_lower_limit", "additional_cooling_upper_limit"),
    ),
    _select(
        "additional_weather_mode",
        65,
        "Additional weather dependent mode",
        WEATHER_MODES,
        optional=True,
        page=42,
    ),
    _number(
        "additional_heating_offset",
        66,
        "Additional weather dependent heating offset",
        optional=True,
        minimum=-10,
        maximum=10,
        page=42,
    ),
    _number(
        "additional_cooling_offset",
        67,
        "Additional weather dependent cooling offset",
        optional=True,
        minimum=-10,
        maximum=10,
        page=42,
    ),
    _sensor(
        "unit_abnormality",
        21,
        "Unit abnormality",
        diagnostic=True,
        options={0: "no_error", 1: "fault", 2: "warning"},
        page=42,
    ),
    _sensor(
        "unit_abnormality_code", 22, "Unit abnormality code", diagnostic=True, page=42
    ),
    _sensor(
        "unit_abnormality_subcode", 23, "Unit abnormality subcode", diagnostic=True
    ),
    _binary("circulation_pump_running", 30, "Circulation pump running"),
    _binary("compressor_running", 31, "Compressor running"),
    _binary("booster_heater_running", 32, "Booster heater running", optional=True),
    _binary("disinfection_running", 33, "Disinfection operation", optional=True),
    _binary("defrost", 35, "Defrost"),
    _binary("hot_start", 36, "Hot start"),
    _sensor(
        "three_way_valve",
        37,
        "Three-way valve",
        optional=True,
        options={0: "space_heating", 1: "dhw"},
    ),
    _sensor(
        "actual_operation_mode",
        38,
        "Actual operation mode",
        options={1: "heating", 2: "cooling"},
    ),
    *(
        _sensor(key, offset, name, unit="°C", optional=optional)
        for key, offset, name, optional in (
            (
                "leaving_water_phe_temperature",
                40,
                "Leaving water PHE temperature",
                False,
            ),
            (
                "leaving_water_buh_temperature",
                41,
                "Leaving water BUH temperature",
                False,
            ),
            ("return_water_temperature", 42, "Return water temperature", False),
            ("dhw_temperature", 43, "DHW temperature", True),
            ("outside_temperature", 44, "Outside temperature", False),
            (
                "liquid_refrigerant_temperature",
                45,
                "Liquid refrigerant temperature",
                False,
            ),
            ("room_temperature", 50, "Remote controller room temperature", True),
        )
    ),
    _sensor("flow_rate", 49, "Flow rate", unit="L/min"),
    _sensor("power_consumption", 51, "Heat pump power consumption", unit="kW"),
    _binary("dhw_normal_operation", 52, "DHW normal operation", optional=True),
    _binary("space_normal_operation", 53, "Space heating/cooling normal operation"),
    *(
        _sensor(
            f"{zone}_{mode}_{bound}_limit",
            offset,
            f"{zone.title()} {mode} setpoint {bound} limit",
            unit="°C",
            optional=zone == "additional",
            diagnostic=True,
            page=44,
        )
        for zone, mode, bound, offset in (
            ("main", "heating", "lower", 54),
            ("main", "heating", "upper", 55),
            ("main", "cooling", "lower", 56),
            ("main", "cooling", "upper", 57),
            ("additional", "heating", "lower", 58),
            ("additional", "heating", "upper", 59),
            ("additional", "cooling", "lower", 60),
            ("additional", "cooling", "upper", 61),
        )
    ),
    _sensor(
        "dhw_upper_temperature",
        76,
        "DHW upper temperature",
        unit="°C",
        optional=True,
        page=44,
    ),
    _sensor(
        "dhw_lower_temperature",
        77,
        "DHW lower temperature",
        unit="°C",
        optional=True,
        page=44,
    ),
    *(
        _sensor(
            f"room_{mode}_{bound}_limit",
            offset,
            f"Room {mode} setpoint {bound} limit",
            unit="°C",
            optional=True,
            diagnostic=True,
            page=44,
        )
        for mode, bound, offset in (
            ("heating", "lower", 84),
            ("heating", "upper", 85),
            ("cooling", "lower", 86),
            ("cooling", "upper", 87),
        )
    ),
]
ALTHERMA_REGISTERS = MappingProxyType({field.key: field for field in _ALTHERMA})
AIR_TO_AIR_REGISTERS = MappingProxyType(
    {
        field.key: field
        for field in (
            _select(
                "smart_grid_mode", 1001, "Smart Grid mode", SMART_GRID_MODES, page=49
            ),
            _number(
                "demand_power_limit",
                1002,
                "Demand Control power limit",
                power=True,
                minimum=0,
                maximum=20,
                page=49,
            ),
        )
    }
)
