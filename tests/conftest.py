"""Reusable register stores and HA-owned connection fixtures."""

from unittest.mock import AsyncMock, patch

import pytest
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.daikin_home_hub.const import DOMAIN

from .reference import AIR_TO_AIR, HOLDING, INPUT

CONNECTION_DATA = {
    "host": "gateway.local",
    "port": 502,
    "unit_id": 1,
    "model": "altherma_3_m_e",
}


@pytest.fixture
def connection():
    return MockModbusConnection()


@pytest.fixture
def unit(connection):
    result = connection.for_unit(1)
    result.input.update({n - 1: row[1] for n, row in INPUT.items()})
    result.holding.update({n - 1: row[1] for n, row in HOLDING.items()})
    result.holding.update({n - 1: row[1] for n, row in AIR_TO_AIR.items()})
    return result


@pytest.fixture
def mock_connection(connection):
    with (
        patch.object(
            connection,
            "close",
            new=AsyncMock(side_effect=connection.simulate_connection_lost),
        ),
        patch(
            "homeassistant.components.modbus.connection.ModbusConnection",
            return_value=connection,
        ) as factory,
    ):
        yield factory


@pytest.fixture
def entry(hass):
    result = MockConfigEntry(
        domain=DOMAIN, title="Daikin Altherma 3 M", data=CONNECTION_DATA
    )
    result.add_to_hass(hass)
    return result


@pytest.fixture
async def configured(hass, entry, mock_connection, unit, enable_custom_integrations):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
