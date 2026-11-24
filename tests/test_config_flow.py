"""UI validation, error reporting, duplicate detection and reconfiguration."""

from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
from modbus_connection.exceptions import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.daikin_home_hub.config_flow import DATA_SCHEMA, normalize_host
from custom_components.daikin_home_hub.const import DOMAIN

from .conftest import CONNECTION_DATA
from .reference import PROFILES

DEFAULT_INSTALLATION_OPTIONS = {
    "dhw_present": False,
    "additional_zone": False,
    "control_method": "leaving_water",
    "cooling_available": True,
}
pytestmark = pytest.mark.usefixtures("enable_custom_integrations", "mock_connection")


@pytest.mark.parametrize("step_id", ["user", "reconfigure"])
async def test_gui_form_and_validation_errors_are_serializable(
    hass, hass_client, entry, step_id
):
    """The GUI must receive JSON for both the initial form and a retry."""
    assert await async_setup_component(hass, "config", {})
    client = await hass_client()
    request = {"handler": DOMAIN}
    if step_id == "reconfigure":
        request["entry_id"] = entry.entry_id
    response = await client.post("/api/config/config_entries/flow", json=request)
    assert response.status == 200
    form = await response.json()
    assert form["type"] == "form"
    assert form["step_id"] == step_id
    fields = {field["name"]: field for field in form["data_schema"]}
    assert set(fields) == {"host", "port", "unit_id", "model"}
    assert "text" in fields["host"]["selector"]
    assert fields["port"]["default"] == 502
    assert fields["unit_id"]["default"] == 1
    assert "default" not in fields["model"]
    assert fields["model"]["selector"]["select"]["options"] == list(PROFILES)
    if step_id == "reconfigure":
        for key, value in CONNECTION_DATA.items():
            assert fields[key]["description"]["suggested_value"] == value

    response = await client.post(
        f"/api/config/config_entries/flow/{form['flow_id']}",
        json={**CONNECTION_DATA, "host": "http://gateway.local"},
    )
    assert response.status == 200
    form = await response.json()
    assert form["errors"] == {"base": "invalid_input"}
    assert len(form["data_schema"]) == 4


@pytest.mark.parametrize(
    "host,normalized_host",
    [
        (" GATEWAY.local. ", "gateway.local"),
        ("192.168.1.5", "192.168.1.5"),
        ("[2001:0DB8::1]", "2001:db8::1"),
    ],
)
async def test_form_and_read_only_validation(
    hass, unit, connection, host, normalized_host
):
    writes = []
    unit.on_write(writes.append)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    with patch(
        "custom_components.daikin_home_hub.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                **CONNECTION_DATA,
                "host": host,
                "port": 502.0,
                "unit_id": 1.0,
            },
        )
        assert result["step_id"] == "installation"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"HomeHub at {normalized_host}"
    assert result["data"] == {**CONNECTION_DATA, "host": normalized_host}
    assert result["options"] == DEFAULT_INSTALLATION_OPTIONS
    assert type(result["data"]["port"]) is int
    assert type(result["data"]["unit_id"]) is int
    assert writes == []
    assert [
        (event.register_type, event.address, event.count) for event in unit.read_events
    ] == [("input", 20, 1)]
    assert not connection.connected


@pytest.mark.parametrize(
    "state,error",
    [
        (30, "invalid_response"),
        (40, "invalid_response"),
        (50, "invalid_response"),
        (99, "invalid_response"),
    ],
)
async def test_connection_status_errors(hass, unit, state, error):
    unit.input[20] = state
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=CONNECTION_DATA
    )
    assert result["errors"] == {"base": error}


@pytest.mark.parametrize(
    "exception",
    [ModbusTimeoutError(), HomeAssistantError("conflict"), OSError("unexpected")],
)
async def test_validation_exceptions(hass, unit, exception):
    unit.fail_requests(exception)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=CONNECTION_DATA
    )
    assert result["errors"] == {
        "base": "unknown" if type(exception) is OSError else "cannot_connect"
    }


async def test_duplicates_are_rejected_before_probe(hass, entry, unit):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={**CONNECTION_DATA, "host": "GATEWAY.local."},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert unit.read_events == []


async def test_entries_on_the_same_host_can_share_a_title(hass, unit):
    with patch(
        "custom_components.daikin_home_hub.async_setup_entry", return_value=True
    ):
        for port in (502, 1502):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "user"},
                data={**CONNECTION_DATA, "model": "air_to_air", "port": port},
            )
            assert result["type"] is FlowResultType.CREATE_ENTRY
            assert result["title"] == "HomeHub at gateway.local"
            await hass.async_block_till_done()


@pytest.mark.parametrize(
    "updates",
    [
        {"host": "http://gateway.local"},
        {"port": 0},
        {"port": 502.5},
        {"port": float("nan")},
        {"unit_id": 248},
        {"model": "q350"},
    ],
)
async def test_invalid_input(hass, updates):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={**CONNECTION_DATA, **updates}
    )
    assert result["errors"] == {"base": "invalid_input"}


async def test_reconfigure_preserves_entry_and_validates_before_change(
    hass, entry, unit
):
    hass.config_entries.async_update_entry(entry, title="My custom HomeHub title")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    assert result["step_id"] == "reconfigure"
    unit.input[20] = 50
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**CONNECTION_DATA, "host": "new.local"}
    )
    assert result["errors"] == {"base": "invalid_response"}
    assert entry.data["host"] == "gateway.local"
    assert entry.title == "My custom HomeHub title"
    unit.input[20] = 0
    with patch(
        "custom_components.daikin_home_hub.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**CONNECTION_DATA, "host": "NEW.local."}
        )
        await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "new.local"
    assert entry.title == "HomeHub at new.local"


async def test_reconfigure_cannot_take_another_entry_endpoint(hass, entry):
    MockConfigEntry(
        domain=DOMAIN, data={**CONNECTION_DATA, "host": "other.local"}
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
        data={**CONNECTION_DATA, "host": "other.local"},
    )
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "host,expected",
    [
        ("  GATEWAY.local. ", "gateway.local"),
        ("192.168.1.5", "192.168.1.5"),
        ("[2001:0DB8::1]", "2001:db8::1"),
    ],
)
def test_normalize_hosts(host, expected):
    assert normalize_host(host) == expected


def test_schema_defaults():
    assert (
        DATA_SCHEMA({"host": "gateway.local", "model": "altherma_3_m_e"})
        == CONNECTION_DATA
    )


async def test_model_must_be_explicit(hass, unit):
    data = {key: value for key, value in CONNECTION_DATA.items() if key != "model"}
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=data
    )
    assert result["errors"] == {"base": "invalid_input"}
    assert unit.read_events == []


@pytest.mark.parametrize(
    "model,address,space",
    [
        ("altherma_3_m_e", 20, "input"),
        ("air_to_air", 1000, "holding"),
    ],
)
@pytest.mark.parametrize("marker", [32765, 32766, 32767])
async def test_probe_accepts_markers_without_writing(
    hass, unit, model, address, space, marker
):
    getattr(unit, space)[address] = marker
    writes = []
    unit.on_write(writes.append)
    with patch(
        "custom_components.daikin_home_hub.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data={**CONNECTION_DATA, "model": model}
        )
        if model != "air_to_air":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert writes == []
    assert [(r.register_type, r.address, r.count) for r in unit.read_events] == [
        (space, address, 1)
    ]


@pytest.mark.parametrize("options", [{}, {"scan_interval": 30}])
@pytest.mark.parametrize("model", ["altherma_3_m_e", "air_to_air"])
async def test_options_gui_and_validation_errors_are_serializable(
    hass, hass_client, entry, options, model
):
    hass.config_entries.async_update_entry(
        entry, options=options, data={**entry.data, "model": model}
    )
    assert await async_setup_component(hass, "config", {})
    client = await hass_client()
    response = await client.post(
        "/api/config/config_entries/options/flow", json={"handler": entry.entry_id}
    )
    assert response.status == 200
    form = await response.json()
    assert form["type"] == "form"
    assert form["step_id"] == "init"
    expected_fields = (
        {"scan_interval"}
        if model == "air_to_air"
        else {"scan_interval", *DEFAULT_INSTALLATION_OPTIONS}
    )
    assert {field["name"] for field in form["data_schema"]} == expected_fields
    field = form["data_schema"][0]
    assert field["name"] == "scan_interval"
    assert field["default"] == 5
    assert field["selector"]["number"] == {
        "min": 5,
        "step": 1,
        "unit_of_measurement": "s",
        "mode": "box",
    }
    if options:
        assert field["description"]["suggested_value"] == 30

    response = await client.post(
        f"/api/config/config_entries/options/flow/{form['flow_id']}",
        json={"scan_interval": 5.5},
    )
    assert response.status == 200
    form = await response.json()
    assert form["errors"] == {"scan_interval": "invalid_scan_interval"}
    assert len(form["data_schema"]) == len(expected_fields)
    assert entry.options == options


@pytest.mark.parametrize("interval", [5.0, 30.0])
async def test_options_save_and_prefill_current_interval(
    hass, hass_client, entry, interval
):
    assert await async_setup_component(hass, "config", {})
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    with patch("homeassistant.config_entries.ConfigEntries.async_reload") as reload:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"scan_interval": interval}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "scan_interval": int(interval),
        **DEFAULT_INSTALLATION_OPTIONS,
    }
    assert type(entry.options["scan_interval"]) is int
    assert entry.data == CONNECTION_DATA
    reload.assert_awaited_once_with(entry.entry_id)

    client = await hass_client()
    response = await client.post(
        "/api/config/config_entries/options/flow", json={"handler": entry.entry_id}
    )
    assert response.status == 200
    form = await response.json()
    assert form["data_schema"][0]["description"]["suggested_value"] == interval


@pytest.mark.parametrize(
    "interval",
    [
        4,
        0,
        -5,
        5.5,
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
        "bad",
        None,
        1e100,
    ],
)
async def test_invalid_refresh_intervals_do_not_change_options(
    hass, entry, unit, interval
):
    hass.config_entries.async_update_entry(entry, options={"scan_interval": 30})
    result = await hass.config_entries.options.async_init(
        entry.entry_id, data={"scan_interval": interval}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"scan_interval": "invalid_scan_interval"}
    assert entry.options == {"scan_interval": 30}
    assert unit.read_events == []
