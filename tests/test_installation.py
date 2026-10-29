"""Installation options control entity groups without commissioning the unit."""

from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import CONNECTION_DATA, DOMAIN
from .reference import HOLDING, INPUT, PROFILES
from .test_home_assistant import entity_id

SETTINGS = {
    "dhw_present": False,
    "additional_zone": False,
    "control_method": "leaving_water",
    "cooling_available": True,
}
DHW = {
    "dhw_reheat_setpoint",
    "dhw_reheat",
    "dhw_booster",
    "dhw_temperature",
    "dhw_normal_operation",
    "dhw_upper_temperature",
    "dhw_lower_temperature",
    "booster_heater_running",
    "disinfection_running",
    "three_way_valve",
}
ROOM = {
    "room_heating_setpoint",
    "room_cooling_setpoint",
    "room_temperature",
    "room_heating_lower_limit",
    "room_heating_upper_limit",
    "room_cooling_lower_limit",
    "room_cooling_upper_limit",
}
ADDITIONAL = {
    "additional_thermostat_input",
    "additional_heating_setpoint",
    "additional_cooling_setpoint",
    "additional_weather_mode",
    "additional_heating_offset",
    "additional_cooling_offset",
    "additional_heating_lower_limit",
    "additional_heating_upper_limit",
    "additional_cooling_lower_limit",
    "additional_cooling_upper_limit",
}
COOLING = {
    "operation_mode",
    "main_cooling_setpoint",
    "main_cooling_offset",
    "main_cooling_lower_limit",
    "main_cooling_upper_limit",
    "additional_cooling_setpoint",
    "additional_cooling_offset",
    "additional_cooling_lower_limit",
    "additional_cooling_upper_limit",
    "room_cooling_setpoint",
    "room_cooling_lower_limit",
    "room_cooling_upper_limit",
}


async def test_altherma_setup_has_installation_step(
    hass, unit, mock_connection, enable_custom_integrations
):
    writes = []
    unit.on_write(writes.append)
    form = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=CONNECTION_DATA
    )
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "installation"
    with patch(
        "custom_components.daikin_home_hub.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"], {**SETTINGS, "dhw_present": True}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == CONNECTION_DATA
    assert result["options"] == {**SETTINGS, "dhw_present": True}
    assert writes == []


@pytest.mark.parametrize("model,excluded", PROFILES.items())
@pytest.mark.parametrize(
    "dhw,zone,control,cooling",
    [
        (False, False, "leaving_water", True),
        (True, False, "room_thermostat", True),
        (True, True, "external_thermostat", True),
        (True, True, "room_thermostat", False),
    ],
)
async def test_selected_installation_groups_define_entities_and_polling(
    hass,
    unit,
    mock_connection,
    enable_custom_integrations,
    model,
    excluded,
    dhw,
    zone,
    control,
    cooling,
):
    options = {
        "dhw_present": dhw,
        "additional_zone": zone,
        "control_method": control,
        "cooling_available": cooling,
    }
    entry = MockConfigEntry(
        domain=DOMAIN, data={**CONNECTION_DATA, "model": model}, options=options
    )
    entry.add_to_hass(hass)
    writes = []
    unit.on_write(writes.append)
    assert await hass.config_entries.async_setup(entry.entry_id)
    if model == "air_to_air":
        expected = {"smart_grid_mode", "demand_power_limit"}
    else:
        expected = {row[0] for row in [*HOLDING.values(), *INPUT.values()]}
        if not dhw:
            expected -= DHW
        if not zone:
            expected -= ADDITIONAL
        if control != "room_thermostat":
            expected -= ROOM
        if control != "external_thermostat":
            expected -= {"main_thermostat_input"}
        if not cooling:
            expected -= COOLING
        if excluded:
            expected -= {"main_thermostat_input", "additional_thermostat_input"}
    registry = er.async_get(hass)
    registered = er.async_entries_for_config_entry(registry, entry.entry_id)
    enabled = {
        item.unique_id.removeprefix(f"{entry.entry_id}_")
        for item in registered
        if item.disabled_by is None
    }
    assert enabled == expected
    assert set(entry.runtime_data.data.values) == expected
    assert writes == []
    # No field outside the installation is read, even if its register exists.
    for table, space in [(HOLDING, "holding"), (INPUT, "input")]:
        if model != "air_to_air":
            assert set(entry.runtime_data.data.raw.get(space, {})) == {
                offset - 1 for offset, row in table.items() if row[0] in expected
            }


async def test_configure_enables_group_and_preserves_customization(
    hass, configured, unit
):
    registry = er.async_get(hass)
    original = entity_id(hass, configured, "dhw_temperature")
    manually_disabled = entity_id(hass, configured, "dhw_reheat", "switch")
    registry.async_update_entity(original, name="My cylinder", icon="mdi:water-boiler")
    registry.async_update_entity(
        manually_disabled, disabled_by=er.RegistryEntryDisabler.USER
    )

    async def configure(dhw):
        form = await hass.config_entries.options.async_init(configured.entry_id)
        result = await hass.config_entries.options.async_configure(
            form["flow_id"], {**SETTINGS, "dhw_present": dhw, "scan_interval": 30}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()

    await configure(True)
    assert registry.async_get(original).disabled_by is None
    assert hass.states.get(original).state == "49.5"
    for dhw in (False, True):
        await configure(dhw)
        item = registry.async_get(original)
        assert item.name == "My cylinder"
        assert item.icon == "mdi:water-boiler"
        assert entity_id(hass, configured, "dhw_temperature") == original
        assert item.disabled_by == (
            None if dhw else er.RegistryEntryDisabler.INTEGRATION
        )
        assert (
            registry.async_get(manually_disabled).disabled_by
            is er.RegistryEntryDisabler.USER
        )
        assert ("dhw_temperature" in configured.runtime_data.data.values) is dhw
    assert configured.options["scan_interval"] == 30


async def test_inactive_installation_blocks_manual_enable_and_writes(
    hass, configured, unit
):
    hass.config_entries.async_update_entry(configured, options=SETTINGS)
    await hass.config_entries.async_reload(configured.entry_id)
    registry = er.async_get(hass)
    number = entity_id(hass, configured, "dhw_reheat_setpoint", "number")
    registry.async_update_entity(number, disabled_by=None)
    await hass.config_entries.async_reload(configured.entry_id)
    assert (
        registry.async_get(number).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    )
    writes = []
    unit.on_write(writes.append)
    with pytest.raises(ServiceValidationError, match="enabled"):
        await configured.runtime_data.async_write("dhw_reheat_setpoint", 45)
    assert writes == []


async def test_existing_entries_keep_individual_selection_until_configured(
    hass, configured
):
    registry = er.async_get(hass)
    dhw = entity_id(hass, configured, "dhw_temperature")
    registry.async_update_entity(dhw, disabled_by=None)
    await hass.config_entries.async_reload(configured.entry_id)
    assert configured.options == {}
    assert set(configured.runtime_data.data.polled_optional_fields) == {
        "dhw_temperature"
    }
    assert registry.async_get(dhw).disabled_by is None


async def test_installation_form_is_serializable_and_has_clear_choices(
    hass, hass_client, unit, mock_connection, enable_custom_integrations
):
    assert await async_setup_component(hass, "config", {})
    client = await hass_client()
    response = await client.post(
        "/api/config/config_entries/flow", json={"handler": DOMAIN}
    )
    initial = await response.json()
    response = await client.post(
        f"/api/config/config_entries/flow/{initial['flow_id']}", json=CONNECTION_DATA
    )
    assert response.status == 200
    form = await response.json()
    assert form["step_id"] == "installation"
    fields = {item["name"]: item for item in form["data_schema"]}
    assert set(fields) == set(SETTINGS)
    for key in ("dhw_present", "additional_zone", "cooling_available"):
        assert fields[key]["selector"] == {"boolean": {}}
        assert fields[key]["default"] == SETTINGS[key]
    assert fields["control_method"]["selector"]["select"]["options"] == [
        "leaving_water",
        "room_thermostat",
        "external_thermostat",
    ]


@pytest.mark.parametrize(
    "control,enabled_key",
    [
        ("room_thermostat", "room_temperature"),
        ("external_thermostat", "main_thermostat_input"),
    ],
)
async def test_existing_registry_provides_configure_suggestions(
    hass, configured, control, enabled_key
):
    registry = er.async_get(hass)
    for key, platform in [
        ("dhw_temperature", "sensor"),
        ("additional_heating_setpoint", "number"),
        (enabled_key, "sensor" if control == "room_thermostat" else "switch"),
    ]:
        registry.async_update_entity(
            entity_id(hass, configured, key, platform), disabled_by=None
        )
    form = await hass.config_entries.options.async_init(configured.entry_id)
    # Suggestions come from prior selections, not a hardware-discovery claim.
    schema = form["data_schema"]
    for key, value in {
        **SETTINGS,
        "dhw_present": True,
        "additional_zone": True,
        "control_method": control,
    }.items():
        marker = next(marker for marker in schema.schema if str(marker) == key)
        assert marker.description["suggested_value"] == value


@pytest.mark.parametrize(
    "bad",
    [
        {"control_method": "unknown"},
        {"control_method": None},
        {"control_method": True},
    ],
)
async def test_invalid_installation_options_leave_entry_unchanged(
    hass, configured, bad
):
    before = dict(configured.options)
    result = await hass.config_entries.options.async_init(
        configured.entry_id, data={**SETTINGS, "scan_interval": 5, **bad}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_installation"}
    assert configured.options == before


async def test_invalid_setup_installation_can_be_corrected(
    hass, unit, mock_connection, enable_custom_integrations
):
    from custom_components.daikin_home_hub.config_flow import HomeHubConfigFlow

    flow = HomeHubConfigFlow()
    flow.hass = hass
    form = await flow.async_step_user(CONNECTION_DATA)
    assert form["step_id"] == "installation"
    result = await flow.async_step_installation({**SETTINGS, "control_method": "bad"})
    assert result["errors"] == {"base": "invalid_installation"}
    result = await flow.async_step_installation(SETTINGS)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_air_to_water_reconfigure_requests_installation_options(
    hass, unit, mock_connection, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**CONNECTION_DATA, "model": "air_to_air"},
        options={"scan_interval": 30},
    )
    entry.add_to_hass(hass)
    form = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
        data=CONNECTION_DATA,
    )
    assert form["step_id"] == "installation"
    with patch("homeassistant.config_entries.ConfigEntries.async_reload"):
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"], {**SETTINGS, "dhw_present": True}
        )
        await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert entry.options == {**SETTINGS, "dhw_present": True, "scan_interval": 30}


async def test_diagnostics_include_selected_installation(hass, configured):
    from custom_components.daikin_home_hub.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    hass.config_entries.async_update_entry(
        configured, options={**SETTINGS, "dhw_present": True}
    )
    await hass.config_entries.async_reload(configured.entry_id)
    data = await async_get_config_entry_diagnostics(hass, configured)
    assert data["installation"] == {**SETTINGS, "dhw_present": True}
    assert "dhw_temperature" in data["active_fields"]
    assert "room_temperature" not in data["active_fields"]
