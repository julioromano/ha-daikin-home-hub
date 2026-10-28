# Daikin Home Hub Modbus

<img src="custom_components/daikin_home_hub/brand/logo.png" alt="Daikin" width="206">

A Home Assistant custom integration for compatible **Daikin Altherma 3** and **air-to-air installations**, through a **Daikin HomeHub EKRHH in unencrypted Modbus TCP mode**. Requires **Home Assistant 2026.10.2 or newer**.

**Unofficial, independent project.** This repository and its code are not affiliated with, developed by, sponsored by, endorsed by, or supported by Daikin or any of its subsidiaries. Daikin, Altherma and Home Hub names, trademarks and logos belong to their respective owners and are used solely to identify compatible equipment.

Support is based on Daikin's published compatibility and register tables, unit tests and an independent TCP simulator. **Physical hardware validation is pending for every profile.** Selecting a profile does not identify the connected equipment or prove that an optional function is installed.

## Compatibility and authoritative documentation

The authoritative source is Daikin's [EKRHH installer reference guide, 4P744838-1E, January 2026](https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/accessories/ekrhh/EKRHH_Installer%20reference%20guide_4PEN744838-1E_English.pdf), linked from the [official HomeHub product page](https://www.daikin.eu/en_us/products/product.html/EKRHH.html). Pages 7-8 establish compatibility, 39-44 describe use case 3 (Altherma), and 48-50 describe use case 4 (air-to-air).

| Setup profile | Equipment / Micon ID | Entities / disabled by default |
| --- | --- | --- |
| Altherma 3 H HT | EPRA14/16/18DV37/W17; `20017705` | 59 / 28 |
| Altherma 3 H MT | EPRA08/10/12EV3/W1; `20007903` | 59 / 28 |
| Altherma 3 R ERGA floor/wall | EHVH/X/Z-E or EHBH/X-E; `20002203` | 57 / 26 |
| Altherma 3 R ERGA ECH₂O | EHSH(B)/X(B)-P-E; `20017704` | 59 / 28 |
| Altherma 3 R ERLA | ERLA11/14/16DV3/W1; `20007903` | 59 / 28 |
| Altherma 3 R MT | ERRA-EV3/W1; `22009C01` | 59 / 28 |
| Altherma 3 M D-series | EBLA/EDLA09/11/14/16D; `20002203` | 57 / 26 |
| Altherma 3 M E-series | EBLA/EDLA04/06/08E; `20017704` | 59 / 28 |
| Compatible air-to-air installation | BRP069C4* WLAN adapter support and an outdoor unit supporting Demand Control; maximum five units | 2 / 0 |

Altherma requires unified MMI2 firmware **7.8.0 or newer**, plus the compatible equipment in the manufacturer's table. Profiles group variants sharing the documented map and exclusions. Compare the full indoor/outdoor model combination with the [manual index](docs/manuals.md) and compatibility table. For the two `20002203` profiles, thermostat holding registers 59/61 are explicitly non-operational and are omitted from the integration.

The air-to-air map exposes **Smart Grid mode and a Demand Control power limit only**. Its two entities represent the installation managed by HomeHub; the map does not expose independent indoor-unit temperatures, setpoints or fan controls.

The [complete register reference](docs/register-map.md) inventories all 61 published entries across both maps. Only the published HomeHub Modbus use cases are supported. PV-only use cases 1/2, EEBUS, direct/native Altherma 4 Modbus, other gateways, RTU and TLS are outside this release.

## Installation

### Manual

From a checkout of this repository:

```sh
ssh USER@HA_HOST 'mkdir -p /config/custom_components'
scp -r custom_components/daikin_home_hub USER@HA_HOST:/config/custom_components/
```

Replace the SSH login and host; for HA Container use the host directory mounted as `/config`. The resulting file must be `/config/custom_components/daikin_home_hub/manifest.json`. Copy the entire directory, including translations and branding. Restart HA, then open **Settings → Devices & services → Add integration → Daikin Home Hub Modbus**.

### HACS custom repository

The distribution target is `julioromano/ha-daikin-home-hub` on GitHub. Repository publication is separate from this initial implementation. Once that repository and a release are published, add `https://github.com/julioromano/ha-daikin-home-hub` under **HACS → Custom repositories**, choose **Integration**, download, restart HA and add the integration. HACS default-directory inclusion is not claimed.

## Gateway preparation and setup

Commission the installation using Daikin's tools first. Keep HomeHub and unit firmware current. The integration does not change gateway network settings, firmware, use case or installer field settings.

For Altherma, enable HomeHub under **Installer settings → Daikin HomeHub → Add Daikin HomeHub**, select **Modbus** (use case 3), then configure TCP/IP with security **not encrypted**. Configure Smart Grid support as required by the intended controls. Review section 13.4 of the EKRHH guide, including the requirement that `[4-08]` Power Consumption Control is set to `0: No` in combination with HomeHub.

For air-to-air, commission use case 4 and its Modbus settings through **ONECTA**, following section 13.5. Every connected unit must satisfy the compatibility conditions above.

| Integration setting | Default / behavior |
| --- | --- |
| Hostname or IP | Required; use the HomeHub address |
| TCP port | `502`; unencrypted Modbus TCP |
| Unit ID | `1`; configurable from 1 to 247 |
| Equipment profile | Required explicit choice; labels include equipment/Micon details |
| Refresh interval | Configure after setup; default/minimum five whole seconds |

Setup reads Altherma input register 21 or air-to-air holding register 1001. Fault/warning states and the three documented no-value markers do not block setup. A successful probe confirms a response at the selected map address; it cannot authenticate HomeHub, verify a model or read serial/firmware information. An illegal address or unexpected probe code requires checking the selected use case and profile.

Duplicate normalized host/port/unit combinations are rejected across profiles. DNS aliases cannot be recognized as the same physical gateway; use consistent endpoint spelling when sharing a connection.

Use **Reconfigure** to change the endpoint or correct a profile. Common entity/device identifiers, custom names and options are preserved. After successful setup, obsolete fields are removed from the registry. For example, changing to a `20002203` profile removes thermostat input entities; changing between Altherma and air-to-air retains the common Smart Grid entity while changing its register address. Update automations referring to removed entities. Failed probe validation leaves saved configuration and registries intact.

## Entities and control behavior

Altherma provides heating/cooling water setpoints, requested operation mode, space operation, quiet mode, weather-dependent modes and offsets, Smart Grid controls, measurements, equipment state and fault reporting. Holding registers are exposed through their controls' actual readback states, without duplicate sensors.

DHW, additional-zone, room-thermostat and external-thermostat fields start **disabled**. Enable only relevant entities on the device's entity page. Disabled optional fields are not polled, except when they supply limits required by an enabled control. Enabling/disabling can reload the integration. A zero value does not prove a feature is installed. Heating-only and differently commissioned installations can return unavailable markers for otherwise eligible fields.

### Setpoints and operating conditions

- Water and room setpoint registers use **whole degrees**, even though measured temperatures and limit registers use hundredths of a degree. Weather-dependent offsets use whole degrees in `-10..10 °C`. Power limits use `0..20 kW`, in `0.01 kW` steps.
- Water-setpoint controls derive bounds from the corresponding current input registers. Room controls intersect those limits with the published heating `12..30 °C` or cooling `15..35 °C` ranges. Fractional device bounds are rounded inward to representable whole degrees. DHW reheat uses `30..60 °C`.
- Missing, waiting, rejected or reversed limit values make the dependent control unavailable. Limits and target availability are read again before writing. Existing device readback outside the writable range is retained rather than clamped by the integration.
- DHW reheat setpoint propagation requires tank operation enabled, **Reheat only**, and **Fixed** setpoint mode. The map does not expose all prerequisites, so verify commissioning on the unit. DHW upper/lower temperature registers are exposed using their published names; they are not used as DHW setpoint limits.
- Thermostat input registers require the manufacturer's control-method/type conditions: in external room thermostat control (`[C-07]=1`), `[C-05]` must be `0: SW Contact`. Other thermostat types can return zero. The map cannot detect these installer settings reliably.

Change modes explicitly. The integration does not switch weather-dependent mode, disable schedules, change Smart Grid mode, or alter another setting as a side effect of a setpoint request. The unit can clamp setpoints or prioritize schedules, safety operation and local control. A successful Modbus acknowledgment/readback does not guarantee that a requested temperature or power limit has taken effect at the equipment.

### Smart Grid and power limits

Smart Grid exposes `free_running`, `forced_off`, `recommended_on` and `forced_on`. These are energy-management requests with device-specific effects, not a general thermostat on/off control.

On Altherma, general and buffering limits are separate. During recommended-on buffering the lower applicable limit governs. Daikin documents a compressor-start reliability override: for 15 minutes after an OFF-to-ON transition, the sent limit can temporarily become `max(4.5 kW, requested limit)`. A low register value is therefore not an instantaneous hard consumption cap.

On air-to-air, HomeHub translates the demand power limit into capacity percentages constrained to **40-100%**, according to the outdoor unit. Forced-off disables Demand Control and can last at most two hours. Recommended-on/forced-on can change equipment operation and comfort targets; local interactions and subsequent free-running requests affect restoration. Review sections 10.3.1-10.3.2 before automating these controls. Register readback is the request, not a measured actual power cap.

### Faults and measurements

Unit abnormality reports no error, fault or warning. The code sensor decodes the exact two ASCII characters, such as `U8`; the subcode remains numeric. No-error subcode `32766` is unavailable by definition. Unknown enum values, malformed ASCII and no-value markers retain their original raw words in diagnostics. Fault meanings depend on the actual unit's manual.

Power is reported in kW and flow in L/min. Power is an instantaneous measurement; the map does not provide an energy counter. DHW/space normal-operation flags distinguish normal operation from idle/buffering and do not replace compressor state.

## Polling, failures and diagnostics

HA owns the shared TCP connection through `async_get_unit`; setup probes use temporary holds through `async_get_temporary_unit`. No YAML hub or separate socket is required. The protocol module has no HA imports. Requests are serialized, and writes are followed immediately by a refresh.

Only consecutive selected registers are grouped. Polls do not bridge undocumented gaps or disabled optional fields. A Modbus exception or isolated timeout invalidates that group's fields for the current cycle, leaving other successful groups usable. Transport/protocol failures, an unsuccessful timeout probe, or failure of every request makes the update unavailable. There is no synthetic gateway-connection register in this map. Subsequent polling recovers automatically without reloading or replaying commands.

The raw markers are handled before sign conversion/scaling: `32767` means unsupported, `32766` means unavailable in the current configuration, and `32765` means waiting for a value. Waiting can occur while HomeHub synchronizes with Altherma. These responses are retried normally; they never become temperatures, limits or true boolean states.

Download diagnostics from the integration menu. They include decoded values, raw registers, writable bounds, per-field unavailability reasons, optional fields polled and sanitized error types/codes. Hostnames are redacted; persistent entry/device identifiers and exception messages are omitted. When reporting a discrepancy, supply actual equipment and firmware details separately, plus the relevant raw values and unit-display comparison.

## Development and validation

```sh
uv sync --frozen
uv run ruff format --check
uv run ruff check
uv run basedpyright
uv run pytest -m 'not integration'
uv run pytest tests/integration --no-cov
```

CI publishes unit XML/HTML coverage even on failure and enforces a 95% combined statement/branch coverage gate. Independent TCP tests run separately. Hassfest validates HA metadata; the HACS workflow validates the published GitHub repository. See [contribution guidance](CONTRIBUTING.md) and [maintenance/release instructions](MAINTAINING.md).

Tests transcribe reference values independently of production declarations and exercise all profiles, all 61 registers and all marker encodings, write validation, dynamic limits, optional polling, HA services and lifecycle, connection sharing, partial failures and recovery. Simulated verification does not replace hardware testing.

### Hardware verification checklist

- [ ] Record indoor/outdoor model codes, Micon ID, MMI/unit/HomeHub firmware and selected use case/profile.
- [ ] Compare measurements, actual mode, faults and raw diagnostics with the unit/ONECTA.
- [ ] Verify setpoint integer encoding, dynamic min/max limits and unavailable controls on the actual commissioning configuration.
- [ ] Enable installed DHW, additional-zone or thermostat features only; confirm disabled features are not polled and documented exclusions are absent.
- [ ] Exercise individual controls and actual readback; verify schedule/local-control arbitration and the conditional DHW/thermostat behavior.
- [ ] Observe Smart Grid and power-limit behavior, including the compressor-start override or air-to-air capacity restrictions.
- [ ] Check offline/synchronizing markers, partial failures, reconnection, restart, reconfiguration and unload while another consumer shares the connection.
- [ ] Record results per profile and firmware before making any physical-validation claim.

## Credits and license

Backend usage follows the [official HA Modbus developer guide](https://developers.home-assistant.io/docs/modbus/introduction/). Branding images are the unmodified [Home Assistant Daikin brand assets](https://github.com/home-assistant/brands/tree/master/core_integrations/daikin).

Licensed under the [MIT License](LICENSE).
