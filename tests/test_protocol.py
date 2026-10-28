"""Behavior specified independently from the production register declarations."""

import asyncio
from unittest.mock import patch

import pytest
from modbus_connection.exceptions import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusProtocolError,
    ModbusTimeoutError,
    ServerDeviceBusyError,
)

from custom_components.daikin_home_hub.models import MODELS
from custom_components.daikin_home_hub.protocol import HomeHub

from .reference import AIR_TO_AIR, HOLDING, INPUT, PROFILES


@pytest.mark.parametrize("model,excluded", PROFILES.items())
async def test_complete_inventory_and_decoding(unit, model, excluded):
    device = HomeHub(unit, model)
    data = await device.async_update(device.optional_fields)
    expected = (
        list(AIR_TO_AIR.values())
        if model == "air_to_air"
        else [*HOLDING.values(), *INPUT.values()]
    )
    if excluded:
        expected = [
            row
            for row in expected
            if row[0] not in {"main_thermostat_input", "additional_thermostat_input"}
        ]
    assert set(data.values) == {row[0] for row in expected}
    for key, _, value in expected:
        assert data.values[key] == value, key
    assert data.unavailable == {}
    assert len(MODELS) == 9


@pytest.mark.parametrize(
    "marker,reason",
    [
        (32767, "unsupported"),
        (32766, "unavailable"),
        (32765, "waiting"),
    ],
)
async def test_markers_are_not_scaled_or_reused(unit, marker, reason):
    device = HomeHub(unit, "altherma_3_m_e")
    assert (await device.async_update()).values["outside_temperature"] == -5.25
    unit.input[43] = marker
    data = await device.async_update()
    assert data.values["outside_temperature"] is None
    assert data.unavailable["outside_temperature"] == reason
    assert data.raw["input"][43] == marker


async def test_disabled_optional_registers_and_gaps_are_not_read(unit):
    device = HomeHub(unit, "altherma_3_m_e")
    data = await device.async_update()
    expected_input = {
        n - 1 for n, (key, _, _) in INPUT.items() if key not in device.optional_fields
    }
    expected_holding = {
        n - 1 for n, (key, _, _) in HOLDING.items() if key not in device.optional_fields
    }
    assert set(data.raw["input"]) == expected_input
    assert set(data.raw["holding"]) == expected_holding
    assert data.polled_optional_fields == ()
    for read in unit.read_events:
        allowed = expected_input if read.register_type == "input" else expected_holding
        assert set(range(read.address, read.address + read.count)) <= allowed


async def test_dynamic_limits_are_fresh_and_commands_write_once(unit):
    device = HomeHub(unit, "altherma_3_m_e")
    assert (await device.async_update()).bounds["main_heating_setpoint"] == (25, 55)
    unit.input[54] = 4500
    with pytest.raises(ValueError, match="between"):
        await device.async_write("main_heating_setpoint", 50)
    writes = []
    unit.on_write(writes.append)
    await device.async_write("main_heating_setpoint", 40)
    assert [(w.function_code, w.address, w.values) for w in writes] == [(6, 0, [40])]


async def test_enabled_control_reads_its_disabled_limit_dependencies(unit):
    device = HomeHub(unit, "altherma_3_m_e")
    data = await device.async_update(frozenset({"room_heating_setpoint"}))
    assert data.bounds["room_heating_setpoint"] == (14, 28)
    assert set(data.polled_optional_fields) == {
        "room_heating_setpoint",
        "room_heating_lower_limit",
        "room_heating_upper_limit",
    }
    assert "room_cooling_setpoint" not in data.values


async def test_excluded_thermostat_cannot_be_polled_or_written(unit):
    device = HomeHub(unit, "altherma_3_m_d")
    data = await device.async_update(frozenset({"main_thermostat_input"}))
    assert "main_thermostat_input" not in data.values
    with pytest.raises(ValueError, match="Unknown"):
        await device.async_write("main_thermostat_input", True)


@pytest.mark.parametrize(
    "model,offset,key,word,value",
    [
        (model, offset, *row)
        for model, table in [("altherma_3_m_e", HOLDING), ("air_to_air", AIR_TO_AIR)]
        for offset, row in table.items()
    ],
)
async def test_every_writable_register_uses_one_fc06(
    unit, model, offset, key, word, value
):
    writes = []
    unit.on_write(writes.append)
    await HomeHub(unit, model).async_write(key, value)
    assert [(w.function_code, w.address, w.values) for w in writes] == [
        (6, offset - 1, [word])
    ]


@pytest.mark.parametrize(
    "space,offset,key,model",
    [
        (space, offset, row[0], model)
        for model, space, table in [
            ("altherma_3_m_e", "holding", HOLDING),
            ("altherma_3_m_e", "input", INPUT),
            ("air_to_air", "holding", AIR_TO_AIR),
        ]
        for offset, row in table.items()
    ],
)
@pytest.mark.parametrize(
    "marker,reason",
    [(32767, "unsupported"), (32766, "unavailable"), (32765, "waiting")],
)
async def test_every_register_recognizes_all_markers(
    unit, space, offset, key, model, marker, reason
):
    getattr(unit, space)[offset - 1] = marker
    device = HomeHub(unit, model)
    data = await device.async_update(device.optional_fields)
    assert data.values[key] is None
    assert data.unavailable[key] == reason
    assert data.raw[space][offset - 1] == marker


@pytest.mark.parametrize(
    "key,value",
    [
        ("main_heating_setpoint", True),
        ("main_heating_setpoint", None),
        ("main_heating_setpoint", "40"),
        ("main_heating_setpoint", float("nan")),
        ("main_heating_setpoint", float("inf")),
        ("main_heating_setpoint", 35.5),
        ("quiet_mode", 1),
        ("quiet_mode", None),
        ("smart_grid_mode", 4),
        ("smart_grid_mode", 1.5),
        ("main_heating_offset", -11),
        ("general_power_limit", 20.01),
        ("buffering_power_limit", 4.555),
        ("outside_temperature", 12),
        ("no_such_field", 1),
    ],
)
async def test_invalid_commands_never_write(unit, key, value):
    writes = []
    unit.on_write(writes.append)
    with pytest.raises(ValueError):
        await HomeHub(unit, "altherma_3_m_e").async_write(key, value)
    assert writes == []


@pytest.mark.parametrize(
    "lo,hi,expected",
    [
        (32766, 5500, None),
        (2500, 32765, None),
        (5500, 2500, None),
        (2501, 2599, None),
        (2501, 5501, (26, 55)),
    ],
)
async def test_unavailable_reversed_or_fractional_bounds(unit, lo, hi, expected):
    unit.input.update({53: lo, 54: hi})
    device = HomeHub(unit, "altherma_3_m_e")
    data = await device.async_update()
    assert data.bounds.get("main_heating_setpoint") == expected
    # Existing actual readback is retained, regardless of the writable range.
    assert data.values["main_heating_setpoint"] == 35
    if expected is None:
        assert data.unavailable["main_heating_setpoint"] == "limits_unavailable"
        with pytest.raises(ValueError, match="limits_unavailable"):
            await device.async_write("main_heating_setpoint", 35)


@pytest.mark.parametrize(
    "space,address,value,key",
    [
        ("input", 20, 10, "unit_abnormality"),
        ("holding", 2, 10, "operation_mode"),
        ("input", 29, 2, "circulation_pump_running"),
        ("input", 21, 0, "unit_abnormality_code"),
        ("input", 21, 0xFF55, "unit_abnormality_code"),
        ("input", 22, 100, "unit_abnormality_subcode"),
    ],
)
async def test_invalid_wire_values_keep_raw_evidence(unit, space, address, value, key):
    getattr(unit, space)[address] = value
    data = await HomeHub(unit, "altherma_3_m_e").async_update()
    assert data.values[key] is None
    assert data.unavailable[key] == "invalid_value"
    assert data.raw[space][address] == value


@pytest.mark.parametrize(
    "error", [IllegalDataAddressError(), ServerDeviceBusyError(), ModbusTimeoutError()]
)
async def test_failed_group_isolated_and_recovers(unit, error):
    device = HomeHub(unit, "altherma_3_m_e")
    before = await device.async_update()
    unit.fail_read(39, error, register_type="input")
    data = await device.async_update()
    fields = {
        "leaving_water_phe_temperature",
        "leaving_water_buh_temperature",
        "return_water_temperature",
    }
    assert set(data.failed_fields) == fields
    assert data.values["outside_temperature"] == -5.25
    for key in fields:
        assert data.values[key] is None
        assert data.unavailable[key] == "read_failed"
        assert data.failed_fields[key].error_type == type(error).__name__
    assert 39 not in data.raw["input"]
    if isinstance(error, ModbusTimeoutError):
        assert unit.read_events[-1].address == 20
        assert unit.read_events[-1].count == 1
    unit.fail_read(39, None, register_type="input")
    assert await device.async_update() == before


@pytest.mark.parametrize(
    "error",
    [
        ModbusConnectionError(),
        ModbusProtocolError(),
        ModbusTimeoutError(),
        IllegalDataAddressError(),
    ],
)
async def test_whole_link_or_every_request_failed(unit, error):
    unit.fail_requests(error)
    with pytest.raises(type(error)):
        await HomeHub(unit, "altherma_3_m_e").async_update()


@pytest.mark.parametrize("probe", [None, 99, 32765])
async def test_timeout_recheck_must_answer_the_selected_map(unit, probe):
    read = unit.read_input_registers

    async def respond(address, count):
        if (address, count) == (20, 1):
            if probe is None:
                raise ModbusTimeoutError()
            return [probe]
        return await read(address, count)

    unit.fail_read(39, ModbusTimeoutError(), register_type="input")
    with patch.object(unit, "read_input_registers", side_effect=respond):
        if probe == 32765:
            assert (await HomeHub(unit, "altherma_3_m_e").async_update()).failed_fields
        else:
            with pytest.raises(
                ModbusTimeoutError if probe is None else ModbusProtocolError
            ):
                await HomeHub(unit, "altherma_3_m_e").async_update()


async def test_failed_write_is_not_replayed(unit):
    unit.fail_write(55, ModbusTimeoutError())
    with patch.object(unit, "write_register", wraps=unit.write_register) as write:
        with pytest.raises(ModbusTimeoutError):
            await HomeHub(unit, "altherma_3_m_e").async_write("smart_grid_mode", 2)
        write.assert_awaited_once_with(55, 2)


async def test_polls_and_commands_cannot_interleave(unit):
    device = HomeHub(unit, "altherma_3_m_e")
    started, release = asyncio.Event(), asyncio.Event()
    read = unit.read_input_registers

    async def pause(address, count):
        if address == 39:
            started.set()
            await release.wait()
        return await read(address, count)

    with patch.object(unit, "read_input_registers", side_effect=pause):
        poll = asyncio.create_task(device.async_update())
        await started.wait()
        command = asyncio.create_task(device.async_write("quiet_mode", True))
        await asyncio.sleep(0)
        assert not command.done()
        assert unit.holding[8] == 0
        release.set()
        await asyncio.gather(poll, command)
    assert unit.holding[8] == 1


@pytest.mark.parametrize("offset,row", INPUT.items())
async def test_each_input_address_changes_only_its_documented_value(unit, offset, row):
    key, word, value = row
    device = HomeHub(unit, "altherma_3_m_e")
    before = await device.async_update(device.optional_fields)
    if isinstance(value, bool):
        new_word, expected = 1 - word, not value
    elif key == "unit_abnormality_code":
        new_word, expected = 0x4131, "A1"
    elif key == "unit_abnormality":
        new_word, expected = 2, 2
    elif key == "three_way_valve":
        new_word, expected = 0, 0
    elif key == "actual_operation_mode":
        new_word, expected = 2, 2
    else:
        new_word = word + 1
        expected = value + (1 if key == "unit_abnormality_subcode" else 0.01)
    unit.input[offset - 1] = new_word
    after = await device.async_update(device.optional_fields)
    if isinstance(expected, float):
        assert after.values[key] == pytest.approx(expected)
    else:
        assert after.values[key] == expected
    assert {
        name for name in after.values if after.values[name] != before.values[name]
    } == {key}
