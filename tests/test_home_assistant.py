"""HA lifecycle, entity services and independent capability expectations."""

import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.icon import async_get_icons
from modbus_connection.exceptions import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.daikin_home_hub.models import MODELS

from .conftest import CONNECTION_DATA, DOMAIN
from .reference import PROFILES


def entity_id(hass, entry, key, platform="sensor"):
    return er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )


@pytest.mark.parametrize("model,excluded", PROFILES.items())
async def test_all_profiles_entities_and_defaults(
    hass, unit, model, excluded, mock_connection, enable_custom_integrations
):
    entry = MockConfigEntry(domain=DOMAIN, data={**CONNECTION_DATA, "model": model})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert len(entities) == (2 if model == "air_to_air" else 57 if excluded else 59)
    assert sum(e.disabled_by is not None for e in entities) == (
        0 if model == "air_to_air" else 26 if excluded else 28
    )
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    assert devices[0].manufacturer == "Daikin"
    assert devices[0].name == "Heat Pump"
    assert devices[0].model == MODELS[model].name
    assert devices[0].identifiers == {(DOMAIN, entry.entry_id)}
    assert all(e.entity_id.split(".", 1)[1].startswith("heat_pump_") for e in entities)
    assert entry.runtime_data.update_interval == timedelta(seconds=5)


async def test_values_service_writes_and_immediate_readback(hass, configured, unit):
    def state(key, platform="sensor"):
        return hass.states.get(entity_id(hass, configured, key, platform))

    assert state("outside_temperature").state == "-5.25"
    assert state("unit_abnormality_code").state == "U8"
    assert state("unit_abnormality").state == "fault"
    assert state("compressor_running", "binary_sensor").state == "on"
    number = state("main_heating_setpoint", "number")
    assert number.attributes["min"] == 25
    assert number.attributes["max"] == 55
    writes = []
    unit.on_write(writes.append)
    for platform, service, key, value in [
        ("number", "set_value", "main_heating_setpoint", {"value": 40}),
        ("select", "select_option", "smart_grid_mode", {"option": "recommended_on"}),
        ("switch", "turn_off", "space_conditioning", {}),
        ("switch", "turn_on", "quiet_mode", {}),
    ]:
        await hass.services.async_call(
            platform,
            service,
            {"entity_id": entity_id(hass, configured, key, platform), **value},
            blocking=True,
        )
    assert [w.address for w in writes] == [0, 55, 3, 8]
    assert state("main_heating_setpoint", "number").state == "40"
    assert state("smart_grid_mode", "select").state == "recommended_on"


async def test_activity_sensors_report_running_and_preserve_unavailability(
    hass, configured, unit
):
    registry = er.async_get(hass)
    for item in er.async_entries_for_config_entry(registry, configured.entry_id):
        if item.domain == "binary_sensor" and item.disabled_by:
            registry.async_update_entity(item.entity_id, disabled_by=None)
    await hass.config_entries.async_reload(configured.entry_id)
    activities = hass.states.async_all("binary_sensor")
    assert len(activities) == 8
    assert all(state.attributes["device_class"] == "running" for state in activities)

    compressor = entity_id(hass, configured, "compressor_running", "binary_sensor")
    for raw, expected in [(0, "off"), (1, "on"), (32766, "unavailable")]:
        unit.input[30] = raw
        await configured.runtime_data.async_refresh()
        assert hass.states.get(compressor).state == expected


async def test_entity_icons_are_available_to_home_assistant(hass, configured):
    icons = (await async_get_icons(hass, "entity", [DOMAIN]))[DOMAIN]
    pump = icons["binary_sensor"]["circulation_pump_running"]
    assert pump["default"] == "mdi:pump"
    assert pump["state"]["off"] == "mdi:pump-off"
    assert icons["switch"]["quiet_mode"]["state"]["on"] == "mdi:volume-low"
    assert icons["select"]["operation_mode"]["state"]["cooling"] == "mdi:snowflake"


async def test_diagnostics_are_sanitized_and_distinguish_markers(
    hass, configured, unit
):
    from custom_components.daikin_home_hub.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    unit.input[43] = 32765
    await configured.runtime_data.async_refresh()
    data = await async_get_config_entry_diagnostics(hass, configured)
    assert data["configuration"]["host"] == "**REDACTED**"
    assert data["unavailable"]["outside_temperature"] == "waiting"
    assert data["raw_registers"]["input"][43] == 32765
    assert "gateway.local" not in json.dumps(data)
    assert configured.entry_id not in json.dumps(data)


async def test_optional_enable_polls_dependencies(hass, configured, unit):
    registry = er.async_get(hass)
    key = entity_id(hass, configured, "room_heating_setpoint", "number")
    registry.async_update_entity(key, disabled_by=None)
    await hass.config_entries.async_reload(configured.entry_id)
    assert set(configured.runtime_data.data.polled_optional_fields) == {
        "room_heating_setpoint",
        "room_heating_lower_limit",
        "room_heating_upper_limit",
    }
    assert hass.states.get(key).attributes["min"] == 14
    assert hass.states.get(key).attributes["max"] == 28


async def test_service_errors_and_unload(hass, configured, unit, connection):
    unit.holding[0] = 32766
    with pytest.raises(ServiceValidationError, match="unavailable"):
        await configured.runtime_data.async_write("main_heating_setpoint", 40)
    unit.fail_write(55, ModbusTimeoutError())
    with pytest.raises(HomeAssistantError, match="write"):
        await configured.runtime_data.async_write("smart_grid_mode", 2)
    assert await hass.config_entries.async_unload(configured.entry_id)
    assert configured.state is ConfigEntryState.NOT_LOADED
    assert not connection.connected


async def test_reconfigure_preserves_common_identity_and_removes_old_map(
    hass, entry, unit, mock_connection, enable_custom_integrations
):
    legacy_name = "Daikin Altherma 3 M E-series"
    devices = dr.async_get(hass)
    device = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=legacy_name,
    )
    devices.async_update_device(device.id, name_by_user="My heat pump")
    registry = er.async_get(hass)
    common = registry.async_get_or_create(
        "select",
        DOMAIN,
        f"{entry.entry_id}_smart_grid_mode",
        config_entry=entry,
        device_id=device.id,
        suggested_object_id="daikin_altherma_3_m_e_series_energy_smart_grid_mode",
    ).entity_id
    registry.async_update_entity(common, name="My grid control")
    hass.config_entries.async_update_entry(
        entry, title=legacy_name, options={"scan_interval": 30}
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.title == legacy_name
    assert entity_id(hass, entry, "smart_grid_mode", "select") == common

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
        data={**entry.data, "model": "air_to_air"},
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.title == "HomeHub at gateway.local"
    assert entity_id(hass, entry, "smart_grid_mode", "select") == common
    assert registry.async_get(common).device_id == device.id
    assert registry.async_get(common).name == "My grid control"
    updated_device = devices.async_get(device.id)
    assert updated_device.name == "Heat Pump"
    assert updated_device.name_by_user == "My heat pump"
    assert updated_device.model == "Daikin air-to-air installation"
    assert len(er.async_entries_for_config_entry(registry, entry.entry_id)) == 2
    assert entry.runtime_data.update_interval == timedelta(seconds=30)


async def test_startup_retries_on_timeout(
    hass, entry, unit, mock_connection, enable_custom_integrations
):
    unit.fail_requests(ModbusTimeoutError())
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize(
    "version,model", [("2026.9.0", "altherma_3_m_e"), ("2026.10.2", "unsupported")]
)
async def test_unsupported_versions_and_models(
    hass, entry, mock_connection, enable_custom_integrations, version, model
):
    hass.config_entries.async_update_entry(entry, data={**entry.data, "model": model})
    with patch("custom_components.daikin_home_hub.__version__", version):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_manual_entity_update_and_device_clamped_readback(hass, configured, unit):
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "homeassistant", {})
    unit.input[43] = 250
    sensor = entity_id(hass, configured, "outside_temperature")
    await hass.services.async_call(
        "homeassistant", "update_entity", {"entity_id": sensor}, blocking=True
    )
    assert hass.states.get(sensor).state == "2.5"
    # The gateway may clamp a request if commissioning changes before write.
    unit.on_write(
        lambda event: unit.holding.update({0: 35}) if event.address == 0 else None
    )
    await configured.runtime_data.async_write("main_heating_setpoint", 40)
    number = entity_id(hass, configured, "main_heating_setpoint", "number")
    assert hass.states.get(number).state == "35"


async def test_all_optional_entities_can_be_enabled(hass, configured):
    registry = er.async_get(hass)
    for item in er.async_entries_for_config_entry(registry, configured.entry_id):
        if item.disabled_by:
            registry.async_update_entity(item.entity_id, disabled_by=None)
    await hass.config_entries.async_reload(configured.entry_id)
    entities = er.async_entries_for_config_entry(registry, configured.entry_id)
    assert len(entities) == 59
    for item in entities:
        state = hass.states.get(item.entity_id)
        assert state is not None
        assert state.state not in ("unknown", "unavailable"), item.entity_id


async def test_failed_reconfiguration_preserves_loaded_registry(hass, configured, unit):
    registry = er.async_get(hass)
    before = {
        item.unique_id: item.entity_id
        for item in er.async_entries_for_config_entry(registry, configured.entry_id)
    }
    unit.holding[1000] = 99
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": configured.entry_id},
        data={**configured.data, "model": "air_to_air"},
    )
    assert result["errors"] == {"base": "invalid_response"}
    assert configured.data["model"] == "altherma_3_m_e"
    assert before == {
        item.unique_id: item.entity_id
        for item in er.async_entries_for_config_entry(registry, configured.entry_id)
    }
