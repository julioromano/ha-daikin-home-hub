"""Verify MBAP framing, strict register spaces and HA shared-socket lifetime."""

import asyncio
import struct
from contextlib import asynccontextmanager

import pytest
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams
from pytest_homeassistant_custom_component.common import MockConfigEntry

from ..conftest import DOMAIN
from ..reference import AIR_TO_AIR, HOLDING, INPUT

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("socket_enabled")]


class Gateway:
    """Strict FC03/04/06 server, independent of production metadata/codecs."""

    def __init__(self):
        self.inputs = {n - 1: row[1] for n, row in INPUT.items()}
        self.holdings = {n - 1: row[1] for n, row in {**HOLDING, **AIR_TO_AIR}.items()}
        self.requests = []
        self.rejected = []
        self.reject = set()
        self.clients = set()
        self.connection_count = 0
        self.empty = asyncio.Event()
        self.empty.set()

    async def handle(self, reader, writer):
        self.connection_count += 1
        self.clients.add(writer)
        self.empty.clear()
        try:
            while True:
                transaction, protocol, length, unit = struct.unpack(
                    ">HHHB", await reader.readexactly(7)
                )
                assert protocol == 0
                pdu = await reader.readexactly(length - 1)
                fc, address, count = struct.unpack(">BHH", pdu)
                self.requests.append((unit, fc, address, count))
                store = self.holdings if fc in (3, 6) else self.inputs
                if fc not in (3, 4, 6):
                    self.rejected.append((fc, address))
                    response = bytes([fc | 0x80, 1])
                elif (fc, address) in self.reject or not all(
                    n in store
                    for n in range(address, address + (1 if fc == 6 else count))
                ):
                    self.rejected.append((fc, address))
                    response = bytes([fc | 0x80, 2])
                elif fc == 6:
                    self.holdings[address] = count
                    response = pdu
                else:
                    values = [store[n] for n in range(address, address + count)]
                    response = bytes([fc, count * 2]) + struct.pack(
                        f">{count}H", *values
                    )
                writer.write(
                    struct.pack(">HHHB", transaction, 0, len(response) + 1, unit)
                    + response
                )
                await writer.drain()
        except asyncio.IncompleteReadError, ConnectionError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            self.clients.remove(writer)
            if not self.clients:
                self.empty.set()

    async def disconnect(self):
        for writer in tuple(self.clients):
            writer.close()
        await asyncio.wait_for(self.empty.wait(), 2)


@asynccontextmanager
async def gateway_server():
    gateway = Gateway()
    server = await asyncio.start_server(gateway.handle, "127.0.0.1", 0)
    try:
        yield gateway, server.sockets[0].getsockname()[1]
    finally:
        server.close()
        await server.wait_closed()
        await gateway.disconnect()


@pytest.mark.parametrize("model", ["altherma_3_m_e", "altherma_3_m_d", "air_to_air"])
async def test_tcp_setup_writes_sharing_reconnect_and_unload(
    hass, enable_custom_integrations, model
):
    async with gateway_server() as (gateway, port):
        data = {"host": "127.0.0.1", "port": port, "unit_id": 7, "model": model}
        first = MockConfigEntry(domain=DOMAIN, data=data)
        second = MockConfigEntry(domain=DOMAIN, data={**data, "unit_id": 8})
        try:
            first.add_to_hass(hass)
            assert await hass.config_entries.async_setup(first.entry_id)
            second.add_to_hass(hass)
            assert await hass.config_entries.async_setup(second.entry_id)
            assert gateway.connection_count == 1
            address = 1000 if model == "air_to_air" else 55
            await first.runtime_data.async_write("smart_grid_mode", 3)
            assert (7, 6, address, 3) in gateway.requests
            assert first.runtime_data.data.values["smart_grid_mode"] == 3
            assert gateway.rejected == []
            if model != "air_to_air":
                assert first.runtime_data.data.values["outside_temperature"] == -5.25
                registry = er.async_get(hass)
                key = registry.async_get_entity_id(
                    "number", DOMAIN, f"{first.entry_id}_room_heating_setpoint"
                )
                registry.async_update_entity(key, disabled_by=None)
                await hass.config_entries.async_reload(first.entry_id)
                assert (7, 4, 83, 2) in gateway.requests
                assert (7, 3, 5, 1) in gateway.requests
                gateway.reject.add((4, 39))
                await first.runtime_data.async_refresh()
                assert first.runtime_data.last_update_success
                assert (
                    first.runtime_data.data.values["return_water_temperature"] is None
                )
                assert first.runtime_data.data.values["outside_temperature"] == -5.25
                gateway.reject.remove((4, 39))
                await first.runtime_data.async_refresh()
                assert (
                    first.runtime_data.data.values["return_water_temperature"] == 31.25
                )
            async with async_get_temporary_unit(
                hass, ModbusTcpParams(host="127.0.0.1", port=port), 7
            ) as unit:
                assert await unit.read_holding_registers(address, 1) == [3]
                assert gateway.connection_count == 1
                lost = asyncio.Event()
                unsubscribe = unit.on_connection_lost(lost.set)
                try:
                    await gateway.disconnect()
                    await asyncio.wait_for(lost.wait(), 2)
                finally:
                    unsubscribe()
            await second.runtime_data.async_refresh()
            assert second.runtime_data.last_update_success
            assert gateway.connection_count == 2
            assert await hass.config_entries.async_unload(first.entry_id)
            await second.runtime_data.async_refresh()
            assert second.runtime_data.last_update_success
            assert len(gateway.clients) == 1
            assert await hass.config_entries.async_unload(second.entry_id)
            await asyncio.wait_for(gateway.empty.wait(), 2)
        finally:
            for entry in (first, second):
                if entry.state.value == "loaded":
                    await hass.config_entries.async_unload(entry.entry_id)
