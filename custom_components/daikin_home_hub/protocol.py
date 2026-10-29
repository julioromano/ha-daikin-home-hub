"""HA-independent HomeHub register models and device operations.

All component addresses are zero-based. EKRHH 4P744838-1E, pp. 39-50.
The caller owns the connection; this module consumes only a ModbusUnit.
"""

import asyncio
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from itertools import groupby
from typing import cast, final

from modbus_connection import ModbusError, ModbusUnit
from modbus_connection.exceptions import (
    ModbusExceptionError,
    ModbusProtocolError,
    ModbusTimeoutError,
)
from modbus_connection.model import Component, Raw, boolean, gauge, integer

from .models import MODELS
from .registers import Register, Space

type Value = int | float | bool | str | None
MARKERS = {32767: "unsupported", 32766: "unavailable", 32765: "waiting"}
_NAN = tuple(MARKERS)
_NO_OPTIONAL_FIELDS: frozenset[str] = frozenset()


@final
class AlthermaSettings(Component):
    """Signed, whole-degree Int16 settings; only power uses Pow16."""

    main_heating_setpoint = integer(0, nan=_NAN, writable=True)
    main_cooling_setpoint = integer(1, nan=_NAN, writable=True)
    operation_mode = integer(2, nan=_NAN, writable=True)
    space_conditioning = boolean(3, nan=_NAN, writable=True)
    room_heating_setpoint = integer(5, nan=_NAN, writable=True)
    room_cooling_setpoint = integer(6, nan=_NAN, writable=True)
    quiet_mode = boolean(8, nan=_NAN, writable=True)
    dhw_reheat_setpoint = integer(9, nan=_NAN, writable=True)
    dhw_reheat = boolean(11, nan=_NAN, writable=True)
    dhw_booster = boolean(12, nan=_NAN, writable=True)
    main_weather_mode = integer(52, nan=_NAN, writable=True)
    main_heating_offset = integer(53, nan=_NAN, writable=True)
    main_cooling_offset = integer(54, nan=_NAN, writable=True)
    smart_grid_mode = integer(55, nan=_NAN, writable=True)
    buffering_power_limit = gauge(56, 0.01, nan=_NAN, writable=True)
    general_power_limit = gauge(57, 0.01, nan=_NAN, writable=True)
    main_thermostat_input = boolean(58, nan=_NAN, writable=True)
    additional_thermostat_input = boolean(60, nan=_NAN, writable=True)
    additional_heating_setpoint = integer(62, nan=_NAN, writable=True)
    additional_cooling_setpoint = integer(63, nan=_NAN, writable=True)
    additional_weather_mode = integer(64, nan=_NAN, writable=True)
    additional_heating_offset = integer(65, nan=_NAN, writable=True)
    additional_cooling_offset = integer(66, nan=_NAN, writable=True)


@final
class AlthermaInputs(Component):
    """Read-only Int16, Temp16, Pow16 and the raw Text16 fault word."""

    register_space = "input"
    unit_abnormality = integer(20, nan=_NAN)
    unit_abnormality_code = integer(21, signed=False, nan=_NAN)
    unit_abnormality_subcode = integer(22, nan=_NAN)
    circulation_pump_running = boolean(29, nan=_NAN)
    compressor_running = boolean(30, nan=_NAN)
    booster_heater_running = boolean(31, nan=_NAN)
    disinfection_running = boolean(32, nan=_NAN)
    defrost = boolean(34, nan=_NAN)
    hot_start = boolean(35, nan=_NAN)
    three_way_valve = integer(36, nan=_NAN)
    actual_operation_mode = integer(37, nan=_NAN)
    leaving_water_phe_temperature = gauge(39, 0.01, nan=_NAN)
    leaving_water_buh_temperature = gauge(40, 0.01, nan=_NAN)
    return_water_temperature = gauge(41, 0.01, nan=_NAN)
    dhw_temperature = gauge(42, 0.01, nan=_NAN)
    outside_temperature = gauge(43, 0.01, nan=_NAN)
    liquid_refrigerant_temperature = gauge(44, 0.01, nan=_NAN)
    flow_rate = gauge(48, 0.01, nan=_NAN)
    room_temperature = gauge(49, 0.01, nan=_NAN)
    power_consumption = gauge(50, 0.01, nan=_NAN)
    dhw_normal_operation = boolean(51, nan=_NAN)
    space_normal_operation = boolean(52, nan=_NAN)
    main_heating_lower_limit = gauge(53, 0.01, nan=_NAN)
    main_heating_upper_limit = gauge(54, 0.01, nan=_NAN)
    main_cooling_lower_limit = gauge(55, 0.01, nan=_NAN)
    main_cooling_upper_limit = gauge(56, 0.01, nan=_NAN)
    additional_heating_lower_limit = gauge(57, 0.01, nan=_NAN)
    additional_heating_upper_limit = gauge(58, 0.01, nan=_NAN)
    additional_cooling_lower_limit = gauge(59, 0.01, nan=_NAN)
    additional_cooling_upper_limit = gauge(60, 0.01, nan=_NAN)
    dhw_upper_temperature = gauge(75, 0.01, nan=_NAN)
    dhw_lower_temperature = gauge(76, 0.01, nan=_NAN)
    room_heating_lower_limit = gauge(83, 0.01, nan=_NAN)
    room_heating_upper_limit = gauge(84, 0.01, nan=_NAN)
    room_cooling_lower_limit = gauge(85, 0.01, nan=_NAN)
    room_cooling_upper_limit = gauge(86, 0.01, nan=_NAN)


@final
class AirToAirSettings(Component):
    """Installation-level energy controls, not individual indoor-unit controls."""

    smart_grid_mode = integer(1000, nan=_NAN, writable=True)
    demand_power_limit = gauge(1001, 0.01, nan=_NAN, writable=True)


@dataclass(frozen=True)
class ReadFailure:
    error_type: str
    exception_code: int | None = None


@dataclass(frozen=True)
class Snapshot:
    """A fresh poll; raw values retain marker and invalid-value evidence."""

    values: dict[str, Value]
    raw: Raw
    unavailable: dict[str, str] = field(default_factory=dict)
    failed_fields: dict[str, ReadFailure] = field(default_factory=dict)
    bounds: dict[str, tuple[float, float]] = field(default_factory=dict)
    polled_optional_fields: tuple[str, ...] = ()


def _bounds(
    register: Register, values: Mapping[str, Value]
) -> tuple[float, float] | None:
    lower, upper = register.minimum, register.maximum
    if register.limits:
        lo, hi = (values.get(key) for key in register.limits)
        if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
            return None
        lower = max(lo, lower) if lower is not None else lo
        upper = min(hi, upper) if upper is not None else hi
        # Int16 setpoints can represent whole degrees only.
        lower, upper = math.ceil(lower), math.floor(upper)
    if lower is None or upper is None or lower > upper:
        return None
    return lower, upper


def _decode(register: Register, value: Value) -> Value:
    """Reject unknown enums and malformed ASCII without inventing a meaning."""
    if register.options is not None and value not in register.options:
        return None
    if register.key == "unit_abnormality_code" and isinstance(value, int):
        high, low = value >> 8, value & 0xFF
        return chr(high) + chr(low) if 32 <= high < 127 and 32 <= low < 127 else None
    if register.key == "unit_abnormality_subcode" and isinstance(value, int):
        return value if 0 <= value <= 99 else None
    return value


@final
class HomeHub:
    """One installation behind a HomeHub, with no socket ownership or HA imports."""

    def __init__(
        self,
        unit: ModbusUnit,
        model: str,
        *,
        active_fields: frozenset[str] | None = None,
    ) -> None:
        self.profile = MODELS[model]
        self.registers = {
            key: value
            for key, value in self.profile.registers.items()
            if self.profile.supports(key)
        }
        self.optional_fields = frozenset(
            key for key, register in self.registers.items() if register.optional
        )
        self.active_fields = frozenset(self.registers)
        if active_fields is not None:
            self.active_fields &= active_fields
        self._unit = unit
        self._lock = asyncio.Lock()

    def _component(self, space: Space, keys: set[str]) -> Component:
        component = (
            AirToAirSettings(self._unit)
            if self.profile.air_to_air
            else AlthermaInputs(self._unit)
            if space == "input"
            else AlthermaSettings(self._unit)
        )
        component.restrict_fields(keys)
        return component

    async def async_validate(self) -> int:
        """A read-only map probe; it cannot identify model or firmware."""
        key = "smart_grid_mode" if self.profile.air_to_air else "unit_abnormality"
        register = self.registers[key]
        raw = await self._component(register.space, {key}).async_read_raw()
        return cast(int, raw[register.space][register.address])

    async def async_update(
        self, optional_fields: frozenset[str] = _NO_OPTIONAL_FIELDS
    ) -> Snapshot:
        async with self._lock:
            keys = set(self.registers) - self.optional_fields
            keys.update(optional_fields & self.optional_fields)
            return await self._read(
                self._dependencies(keys & self.active_fields) & self.active_fields
            )

    def _dependencies(self, keys: set[str]) -> set[str]:
        return keys | {
            limit for key in keys for limit in (self.registers[key].limits or ())
        }

    async def _read(self, keys: set[str]) -> Snapshot:
        raw: Raw = {}
        values: dict[str, Value] = {}
        unavailable: dict[str, str] = {}
        failures: dict[str, ReadFailure] = {}
        timed_out = False
        last_error: ModbusError | None = None
        for space in ("input", "holding"):
            registers = sorted(
                (
                    self.registers[key]
                    for key in keys
                    if self.registers[key].space == space
                ),
                key=lambda register: register.address,
            )
            # Exactly consecutive selected fields form each isolated request.
            for _, group in groupby(
                enumerate(registers), key=lambda item: item[1].address - item[0]
            ):
                fields = [register for _, register in group]
                component = self._component(
                    space, {register.key for register in fields}
                )
                try:
                    block = await component.async_read_raw()
                except (ModbusExceptionError, ModbusTimeoutError) as err:
                    last_error = err
                    timed_out |= isinstance(err, ModbusTimeoutError)
                    for register in fields:
                        values[register.key] = None
                        unavailable[register.key] = "read_failed"
                        failures[register.key] = ReadFailure(
                            type(err).__name__,
                            err.exception_code
                            if isinstance(err, ModbusExceptionError)
                            else None,
                        )
                    continue
                raw.setdefault(space, {}).update(block[space])
                for register in fields:
                    word = cast(int, block[space][register.address])
                    value = _decode(
                        register, cast(Value, getattr(component, register.key))
                    )
                    values[register.key] = value
                    if word in MARKERS:
                        unavailable[register.key] = MARKERS[word]
                    elif value is None:
                        unavailable[register.key] = "invalid_value"
        if not raw:
            assert last_error is not None
            raise last_error
        if timed_out:
            probe = await self.async_validate()
            if probe not in MARKERS and probe not in (
                (0, 1, 2, 3) if self.profile.air_to_air else (0, 1, 2)
            ):
                raise ModbusProtocolError("Invalid HomeHub probe response")
        bounds: dict[str, tuple[float, float]] = {}
        for key in keys:
            register = self.registers[key]
            if register.platform == "number":
                limits = _bounds(register, values)
                if limits is None:
                    _ = unavailable.setdefault(key, "limits_unavailable")
                else:
                    bounds[key] = limits
        return Snapshot(
            values,
            raw,
            unavailable,
            failures,
            bounds,
            tuple(sorted(keys & self.optional_fields)),
        )

    async def async_write(self, key: str, value: Value) -> None:
        """Fresh availability/limit validation, one write, no replay."""
        async with self._lock:
            register = self.registers.get(key)
            if register is None or register.space != "holding":
                raise ValueError(f"Unknown writable field: {key}")
            if key not in self.active_fields:
                raise ValueError("Setting is not enabled for this installation")
            if register.platform == "switch":
                if not isinstance(value, bool):
                    raise ValueError("Expected a boolean")
            elif (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError("Expected a finite number")
            if register.options is not None and value not in register.options:
                raise ValueError("Unknown option")
            data = await self._read(self._dependencies({key}))
            if key in data.unavailable:
                raise ValueError(f"Setting unavailable: {data.unavailable[key]}")
            if register.platform == "number":
                lower, upper = data.bounds[key]
                numeric = cast(int | float, value)
                if not lower <= numeric <= upper:
                    raise ValueError(f"Expected a value between {lower} and {upper}")
                steps = numeric / register.step
                if not math.isclose(steps, round(steps), rel_tol=0, abs_tol=1e-7):
                    raise ValueError(f"Expected increments of {register.step}")
            await self._component("holding", {key}).write(key, value)
