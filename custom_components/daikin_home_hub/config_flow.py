"""UI setup and reconfiguration; probing never changes device settings."""

import ipaddress
import logging
import math
import re
from datetime import timedelta
from typing import Any, final, override

import probatio
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,  # pyright: ignore[reportUnknownVariableType]
    NumberSelector,  # pyright: ignore[reportUnknownVariableType]
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,  # pyright: ignore[reportUnknownVariableType]
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,  # pyright: ignore[reportUnknownVariableType]
)
from modbus_connection import ModbusError, ModbusTcpParams

from .const import (
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DEFAULT_UNIT_ID,
    DOMAIN,
    MIN_SCAN_INTERVAL_SECONDS,
)
from .installation import (
    ADDITIONAL_ZONE_FIELDS,
    CONF_ADDITIONAL_ZONE,
    CONF_CONTROL_METHOD,
    CONF_COOLING_AVAILABLE,
    CONF_DHW_PRESENT,
    COOLING_FIELDS,
    DHW_FIELDS,
    INSTALLATION_KEYS,
    ROOM_THERMOSTAT_FIELDS,
    ControlMethod,
    Installation,
)
from .models import MODELS
from .protocol import MARKERS, HomeHub

_LOGGER = logging.getLogger(__name__)


def normalize_host(value: str) -> str:
    """Normalize DNS names and IPv4/IPv6 literals, without resolving aliases."""
    host = value.strip().lower().removesuffix(".")
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        if len(host) > 253 or not all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in host.split(".")
        ):
            raise probatio.Invalid("Enter a hostname or IP address") from None
        return host


def _integer(value: float) -> int:
    if isinstance(value, bool) or not math.isfinite(value) or int(value) != value:
        raise probatio.Invalid("Expected an integer")
    return int(value)


DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
            NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
        ),
        probatio.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): NumberSelector(
            NumberSelectorConfig(min=1, max=247, mode=NumberSelectorMode.BOX)
        ),
        probatio.Required(CONF_MODEL): SelectSelector(
            SelectSelectorConfig(
                options=list(MODELS),
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="model",
            )
        ),
    }
)

OPTIONS_SCHEMA = probatio.Schema(
    {
        probatio.Required(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_SECONDS
        ): NumberSelector(
            NumberSelectorConfig(
                min=MIN_SCAN_INTERVAL_SECONDS,
                step=1,
                unit_of_measurement="s",
                mode=NumberSelectorMode.BOX,
            )
        ),
    }
)


def installation_schema(defaults: dict[str, Any]) -> probatio.Schema:
    """Use frontend-serializable selectors, with no device configuration writes."""
    return probatio.Schema(
        {
            probatio.Required(
                CONF_DHW_PRESENT, default=defaults[CONF_DHW_PRESENT]
            ): BooleanSelector(),
            probatio.Required(
                CONF_ADDITIONAL_ZONE, default=defaults[CONF_ADDITIONAL_ZONE]
            ): BooleanSelector(),
            probatio.Required(
                CONF_CONTROL_METHOD, default=defaults[CONF_CONTROL_METHOD]
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(ControlMethod),
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="control_method",
                )
            ),
            probatio.Required(
                CONF_COOLING_AVAILABLE, default=defaults[CONF_COOLING_AVAILABLE]
            ): BooleanSelector(),
        }
    )


def installation_defaults(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Suggest saved settings, or the legacy registry selection for user review."""
    saved = Installation.from_options(entry.options)
    if saved is not None:
        return saved.as_options()
    entries = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    prefix = f"{entry.entry_id}_"
    enabled = {
        item.unique_id.removeprefix(prefix)
        for item in entries
        if item.platform == DOMAIN
        and item.unique_id.startswith(prefix)
        and item.disabled_by is None
    }
    method = ControlMethod.LEAVING_WATER
    if enabled & ROOM_THERMOSTAT_FIELDS:
        method = ControlMethod.ROOM_THERMOSTAT
    elif "main_thermostat_input" in enabled:
        method = ControlMethod.EXTERNAL_THERMOSTAT
    return Installation(
        dhw_present=bool(enabled & DHW_FIELDS),
        additional_zone=bool(enabled & ADDITIONAL_ZONE_FIELDS),
        control_method=method,
        cooling_available=bool(enabled & COOLING_FIELDS) if entries else True,
    ).as_options()


@final
class HomeHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure the device rather than a separate YAML Modbus hub."""

    VERSION = 1
    _connection_data: dict[str, Any] | None = None
    _reconfigure_entry: ConfigEntry | None = None

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> HomeHubOptionsFlow:
        """Expose polling preferences separately from the device connection."""
        return HomeHubOptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_step_connection("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_step_connection("reconfigure", user_input)

    async def _async_step_connection(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry() if step_id == "reconfigure" else None
        if user_input is not None:
            try:
                data: dict[str, Any] = DATA_SCHEMA(user_input)
                # The form schema is serialized for the frontend. Keep custom
                # validation here because Python callables cannot be rendered.
                data[CONF_HOST] = normalize_host(data[CONF_HOST])
                data[CONF_PORT] = _integer(data[CONF_PORT])
                data[CONF_UNIT_ID] = _integer(data[CONF_UNIT_ID])
            except probatio.Invalid:
                errors["base"] = "invalid_input"
            else:
                self._async_abort_entries_match(
                    {
                        CONF_HOST: data[CONF_HOST],
                        CONF_PORT: data[CONF_PORT],
                        CONF_UNIT_ID: data[CONF_UNIT_ID],
                    }
                )
                error = await self._async_validate(data)
                if error:
                    errors["base"] = error
                else:
                    if not MODELS[data[CONF_MODEL]].air_to_air and (
                        entry is None
                        or (
                            MODELS[entry.data[CONF_MODEL]].air_to_air
                            and Installation.from_options(entry.options) is None
                        )
                    ):
                        self._connection_data = data
                        self._reconfigure_entry = entry
                        return await self.async_step_installation()
                    return self._finish_connection(data, entry)
        schema = (
            self.add_suggested_values_to_schema(DATA_SCHEMA, entry.data)
            if entry
            else DATA_SCHEMA
        )
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    def _finish_connection(
        self,
        data: dict[str, Any],
        entry: ConfigEntry | None,
        options: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if entry is not None:
            # Preserve custom titles, identities and unrelated options.
            title = (
                MODELS[data[CONF_MODEL]].name
                if entry.title == MODELS[entry.data[CONF_MODEL]].name
                else entry.title
            )
            return self.async_update_reload_and_abort(
                entry,
                title=title,
                data_updates=data,
                options={**entry.options, **(options or {})},
            )
        return self.async_create_entry(
            title=MODELS[data[CONF_MODEL]].name, data=data, options=options or {}
        )

    async def async_step_installation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._connection_data is not None
        defaults = (
            installation_defaults(self.hass, self._reconfigure_entry)
            if self._reconfigure_entry
            else Installation().as_options()
        )
        schema = installation_schema(defaults)
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                options: dict[str, Any] = schema(user_input)
            except probatio.Invalid:
                errors["base"] = "invalid_installation"
            else:
                return self._finish_connection(
                    self._connection_data, self._reconfigure_entry, options
                )
        return self.async_show_form(
            step_id="installation", data_schema=schema, errors=errors
        )

    async def _async_validate(self, data: dict[str, Any]) -> str | None:
        try:
            async with async_get_temporary_unit(
                self.hass,
                ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT]),
                data[CONF_UNIT_ID],
            ) as unit:
                state = await HomeHub(unit, data[CONF_MODEL]).async_validate()
        except ModbusError, HomeAssistantError:
            return "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error validating Daikin HomeHub")
            return "unknown"
        valid = (0, 1, 2, 3) if MODELS[data[CONF_MODEL]].air_to_air else (0, 1, 2)
        return None if state in valid or state in MARKERS else "invalid_response"


@final
class HomeHubOptionsFlow(OptionsFlowWithReload):
    """Installation and polling preferences; HA commissioning remains untouched."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        air_to_air = MODELS[self.config_entry.data[CONF_MODEL]].air_to_air
        defaults = installation_defaults(self.hass, self.config_entry)
        schema = (
            OPTIONS_SCHEMA
            if air_to_air
            else OPTIONS_SCHEMA.extend(installation_schema(defaults).schema)
        )
        if user_input is not None:
            try:
                # Classify polling errors independently of installation selectors.
                options: dict[str, Any] = OPTIONS_SCHEMA(
                    {
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
                        )
                    }
                )
                options[CONF_SCAN_INTERVAL] = _integer(options[CONF_SCAN_INTERVAL])
                # Reject intervals the coordinator cannot represent before saving.
                _ = timedelta(seconds=options[CONF_SCAN_INTERVAL])
            except probatio.Invalid, OverflowError:
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
            else:
                try:
                    installation: dict[str, Any] = (
                        {}
                        if air_to_air
                        else installation_schema(defaults)(
                            {
                                key: value
                                for key, value in user_input.items()
                                if key in INSTALLATION_KEYS
                            }
                        )
                    )
                except probatio.Invalid:
                    errors["base"] = "invalid_installation"
                else:
                    return self.async_create_entry(
                        title="",
                        data={**self.config_entry.options, **options, **installation},
                    )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, {**defaults, **self.config_entry.options}
            ),
            errors=errors,
        )
