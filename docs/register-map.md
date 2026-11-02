# HomeHub Modbus register reference

Register source reviewed **2026-10-28** against Daikin's [EKRHH installer reference, 4P744838-1E, January 2026](https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/accessories/ekrhh/EKRHH_Installer%20reference%20guide_4PEN744838-1E_English.pdf). Installation-options behavior updated **2026-10-29**. The [manual index](manuals.md) records official sources and applicability. This inventory covers **23 Altherma holding registers, 36 Altherma input registers, and two air-to-air holding registers**.

## Address, encoding and entity conventions

Published offsets below are **one-based decimal**. PDU addresses are zero-based: offset minus one. Holding and input are separate spaces, even where numbers overlap. Holding registers use FC03 reads and single-word FC06 writes; input registers use FC04. This interface uses no coils or discrete inputs.

`Int16` is signed two's complement and unscaled; temperature **setpoints and offsets are whole degrees**. `Temp16` and `Pow16` are signed words divided by 100. Flow is Int16 divided by 100 to give L/min. `Text16` is the high-byte ASCII character followed by the low-byte character. Fault subcodes are 0-99; unknown enums and malformed text have no decoded value, while the raw word remains available.

All fields recognize raw **32767 = unsupported**, **32766 = unavailable in the current configuration**, and **32765 = waiting for value**, before scaling or boolean conversion. They become unavailable rather than measurements or true flags. The subcode's no-error value is 32766. Read failures are separately diagnosed as `read_failed`; bounded controls with missing/invalid limits report `limits_unavailable`. Fresh snapshots never retain stale values from a failed group.

`Core` fields are available with the standard installation options. Other groups follow the declared installation: DHW, additional zone and main-zone control method. Cooling-related fields additionally require cooling available. Model-excluded fields are omitted entirely. All fields belong to one HA installation device. Writable states are exposed by their controls, without duplicate holding-register sensors.

## Altherma use case 3

All eight Altherma profiles use this map. HR 59/61 are omitted for ERGA floor/wall and M D-series with Micon **20002203**. The other six profiles register 59 entities; those two profiles register 57. Default installation choices enable 31 entities and leave 28 or 26 disabled. The number enabled changes with installation options and individual user choices.

### Holding registers

| Offset | PDU | Name / HA key | Entity | Encoding / unit | Installation group | Constraints / states | Page |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | Main heating water setpoint<br>`main_heating_setpoint` | number | Int16; °C | Core | Fresh bounds: `main_heating_lower_limit`, `main_heating_upper_limit` | 41 |
| 2 | 1 | Main cooling water setpoint<br>`main_cooling_setpoint` | number | Int16; °C | Core + cooling | Fresh bounds: `main_cooling_lower_limit`, `main_cooling_upper_limit` | 41 |
| 3 | 2 | Requested operation mode<br>`operation_mode` | select | Int16 | Core + cooling | 0: auto; 1: heating; 2: cooling; Heating-only units return 32766 | 41 |
| 4 | 3 | Space heating/cooling<br>`space_conditioning` | switch | Int16, 0/1 | Core | - | 41 |
| 6 | 5 | Room heating setpoint<br>`room_heating_setpoint` | number | Int16; °C | Room thermostat (main) | Fresh bounds: `room_heating_lower_limit`, `room_heating_upper_limit`; 12..30 °C; step 1 | 41 |
| 7 | 6 | Room cooling setpoint<br>`room_cooling_setpoint` | number | Int16; °C | Room thermostat (main) + cooling | Fresh bounds: `room_cooling_lower_limit`, `room_cooling_upper_limit`; 15..35 °C; step 1 | 41 |
| 9 | 8 | Quiet mode<br>`quiet_mode` | switch | Int16, 0/1 | Core | - | 41 |
| 10 | 9 | DHW reheat setpoint<br>`dhw_reheat_setpoint` | number | Int16; °C | DHW | 30..60 °C; step 1; Tank enabled; Reheat only; Fixed mode | 41 |
| 12 | 11 | DHW reheat<br>`dhw_reheat` | switch | Int16, 0/1 | DHW | - | 41 |
| 13 | 12 | DHW powerful mode<br>`dhw_booster` | switch | Int16, 0/1 | DHW | - | 41 |
| 53 | 52 | Main weather dependent mode<br>`main_weather_mode` | select | Int16 | Core | 0: fixed; 1: weather_dependent; 2: fixed_scheduled; 3: weather_dependent_scheduled | 41 |
| 54 | 53 | Main weather dependent heating offset<br>`main_heating_offset` | number | Int16; °C | Core | -10..10 °C; step 1 | 41 |
| 55 | 54 | Main weather dependent cooling offset<br>`main_cooling_offset` | number | Int16; °C | Core + cooling | -10..10 °C; step 1 | 41 |
| 56 | 55 | Smart Grid mode<br>`smart_grid_mode` | select | Int16 | Core | 0: free_running; 1: forced_off; 2: recommended_on; 3: forced_on | 41 |
| 57 | 56 | Buffering power limit<br>`buffering_power_limit` | number | Pow16 / 100; kW | Core | 0..20 kW; step 0.01 | 41 |
| 58 | 57 | General power limit<br>`general_power_limit` | number | Pow16 / 100; kW | Core | 0..20 kW; step 0.01 | 41 |
| 59 | 58 | Main thermostat input A<br>`main_thermostat_input` | switch | Int16, 0/1 | External thermostat (main) | Omitted on Micon 20002203 profiles; installer conditions apply | 42 |
| 61 | 60 | Additional thermostat input A<br>`additional_thermostat_input` | switch | Int16, 0/1 | Additional zone | Omitted on Micon 20002203 profiles; installer conditions apply | 42 |
| 63 | 62 | Additional heating water setpoint<br>`additional_heating_setpoint` | number | Int16; °C | Additional zone | Fresh bounds: `additional_heating_lower_limit`, `additional_heating_upper_limit` | 42 |
| 64 | 63 | Additional cooling water setpoint<br>`additional_cooling_setpoint` | number | Int16; °C | Additional zone + cooling | Fresh bounds: `additional_cooling_lower_limit`, `additional_cooling_upper_limit` | 42 |
| 65 | 64 | Additional weather dependent mode<br>`additional_weather_mode` | select | Int16 | Additional zone | 0: fixed; 1: weather_dependent; 2: fixed_scheduled; 3: weather_dependent_scheduled | 42 |
| 66 | 65 | Additional weather dependent heating offset<br>`additional_heating_offset` | number | Int16; °C | Additional zone | -10..10 °C; step 1 | 42 |
| 67 | 66 | Additional weather dependent cooling offset<br>`additional_cooling_offset` | number | Int16; °C | Additional zone + cooling | -10..10 °C; step 1 | 42 |

### Input registers

| Offset | PDU | Name / HA key | Entity | Encoding / unit | Installation group | Constraints / states | Page |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | 20 | Unit abnormality<br>`unit_abnormality` | sensor | Int16 | Core | 0: no_error; 1: fault; 2: warning | 42 |
| 22 | 21 | Unit abnormality code<br>`unit_abnormality_code` | sensor | Text16, high byte then low byte | Core | - | 42 |
| 23 | 22 | Unit abnormality subcode<br>`unit_abnormality_subcode` | sensor | Int16 | Core | - | 43 |
| 30 | 29 | Circulation pump running<br>`circulation_pump_running` | binary_sensor | Int16, 0/1 | Core | - | 43 |
| 31 | 30 | Compressor running<br>`compressor_running` | binary_sensor | Int16, 0/1 | Core | - | 43 |
| 32 | 31 | Booster heater running<br>`booster_heater_running` | binary_sensor | Int16, 0/1 | DHW | - | 43 |
| 33 | 32 | Disinfection operation<br>`disinfection_running` | binary_sensor | Int16, 0/1 | DHW | - | 43 |
| 35 | 34 | Defrost<br>`defrost` | binary_sensor | Int16, 0/1 | Core | - | 43 |
| 36 | 35 | Hot start<br>`hot_start` | binary_sensor | Int16, 0/1 | Core | - | 43 |
| 37 | 36 | 3-way valve<br>`three_way_valve` | sensor | Int16 | DHW | 0: space_heating; 1: dhw | 43 |
| 38 | 37 | Actual operation mode<br>`actual_operation_mode` | sensor | Int16 | Core | 1: heating; 2: cooling | 43 |
| 40 | 39 | Leaving water PHE temperature<br>`leaving_water_phe_temperature` | sensor | Temp16 / 100; °C | Core | - | 43 |
| 41 | 40 | Leaving water BUH temperature<br>`leaving_water_buh_temperature` | sensor | Temp16 / 100; °C | Core | - | 43 |
| 42 | 41 | Return water temperature<br>`return_water_temperature` | sensor | Temp16 / 100; °C | Core | - | 43 |
| 43 | 42 | DHW temperature<br>`dhw_temperature` | sensor | Temp16 / 100; °C | DHW | - | 43 |
| 44 | 43 | Outside temperature<br>`outside_temperature` | sensor | Temp16 / 100; °C | Core | - | 43 |
| 45 | 44 | Liquid refrigerant temperature<br>`liquid_refrigerant_temperature` | sensor | Temp16 / 100; °C | Core | - | 43 |
| 49 | 48 | Flow rate<br>`flow_rate` | sensor | Int16 / 100; L/min | Core | - | 43 |
| 50 | 49 | Remote controller room temperature<br>`room_temperature` | sensor | Temp16 / 100; °C | Room thermostat (main) | - | 43 |
| 51 | 50 | Heat pump power consumption<br>`power_consumption` | sensor | Pow16 / 100; kW | Core | - | 43 |
| 52 | 51 | DHW normal operation<br>`dhw_normal_operation` | binary_sensor | Int16, 0/1 | DHW | - | 43 |
| 53 | 52 | Space heating/cooling normal operation<br>`space_normal_operation` | binary_sensor | Int16, 0/1 | Core | - | 43 |
| 54 | 53 | Main heating setpoint lower limit<br>`main_heating_lower_limit` | sensor | Temp16 / 100; °C | Core | - | 44 |
| 55 | 54 | Main heating setpoint upper limit<br>`main_heating_upper_limit` | sensor | Temp16 / 100; °C | Core | - | 44 |
| 56 | 55 | Main cooling setpoint lower limit<br>`main_cooling_lower_limit` | sensor | Temp16 / 100; °C | Core + cooling | - | 44 |
| 57 | 56 | Main cooling setpoint upper limit<br>`main_cooling_upper_limit` | sensor | Temp16 / 100; °C | Core + cooling | - | 44 |
| 58 | 57 | Additional heating setpoint lower limit<br>`additional_heating_lower_limit` | sensor | Temp16 / 100; °C | Additional zone | - | 44 |
| 59 | 58 | Additional heating setpoint upper limit<br>`additional_heating_upper_limit` | sensor | Temp16 / 100; °C | Additional zone | - | 44 |
| 60 | 59 | Additional cooling setpoint lower limit<br>`additional_cooling_lower_limit` | sensor | Temp16 / 100; °C | Additional zone + cooling | - | 44 |
| 61 | 60 | Additional cooling setpoint upper limit<br>`additional_cooling_upper_limit` | sensor | Temp16 / 100; °C | Additional zone + cooling | - | 44 |
| 76 | 75 | DHW upper temperature<br>`dhw_upper_temperature` | sensor | Temp16 / 100; °C | DHW | Published temperature label; not treated as a setpoint bound | 44 |
| 77 | 76 | DHW lower temperature<br>`dhw_lower_temperature` | sensor | Temp16 / 100; °C | DHW | Published temperature label; not treated as a setpoint bound | 44 |
| 84 | 83 | Room heating setpoint lower limit<br>`room_heating_lower_limit` | sensor | Temp16 / 100; °C | Room thermostat (main) | - | 44 |
| 85 | 84 | Room heating setpoint upper limit<br>`room_heating_upper_limit` | sensor | Temp16 / 100; °C | Room thermostat (main) | - | 44 |
| 86 | 85 | Room cooling setpoint lower limit<br>`room_cooling_lower_limit` | sensor | Temp16 / 100; °C | Room thermostat (main) + cooling | - | 44 |
| 87 | 86 | Room cooling setpoint upper limit<br>`room_cooling_upper_limit` | sensor | Temp16 / 100; °C | Room thermostat (main) + cooling | - | 44 |

### Setpoint and optional-function policy

Water controls require the matching valid input lower/upper pair. Room setpoints intersect that pair with the published 12-30 °C heating / 15-35 °C cooling range. Limits are rounded inward to whole degrees and read afresh before each command. Missing/reversed limits disable the control; there is no guessed range. Readback remains visible without clamping, including values outside the current write range. DHW reheat has its own published 30-60 °C range; IR 76/77 are not used as its bounds.

Altherma setup and Configure expose DHW tank present, additional zone present, main-zone control method and cooling available. They change HA entity defaults, polling and write eligibility; they never write installer settings. The main method selects leaving-water, room-thermostat or external-room-thermostat exposure. The additional thermostat input follows the additional-zone choice independently, subject to model exclusions. Cooling disabled suppresses cooling fields and the requested-mode selector; it retains the actual-mode sensor.

Inactive groups retain disabled registry entries, IDs and customizations. Re-enabling clears integration-owned disables only, preserving individual user disables. Changing the model can still remove inapplicable fields. Enabling a control reads its limit dependencies even if their diagnostic entities are individually disabled. Runtime reads and writes enforce the installation mask independently of entity state.

Existing entries without installation options retain per-entity selection until Configure is saved. Suggestions for legacy entries reflect registry selections, not detected equipment. These options do not establish accessory presence or guarantee register availability.

DHW reheat setpoint propagation requires tank operation enabled, Reheat only and Fixed setpoint mode. External thermostat input behavior depends on commissioning; for [C-07]=1, [C-05] must be 0: SW Contact. These installer settings are not discoverable through this map, so the integration cannot verify every prerequisite. Valid register readback does not prove physical actuation.

The two weather-mode selects do not automatically change any setpoint or offset, and changing a setpoint does not change a mode. Smart Grid/power requests can be overridden by equipment logic. The 15-minute compressor-start reliability override can use max(4.5 kW, requested limit). See the README and manufacturer sections 9.3/13.4 for operation and commissioning.

## Air-to-air use case 4

The profile requires BRP069C4* WLAN-adapter compatibility and outdoor Demand Control, with a maximum of five connected units. Both entities are enabled by default and operate at installation level. This map has no published input registers or independent indoor-unit state/control map.

| Offset | PDU | Name / HA key | Entity | Encoding / unit | Installation group | Constraints / states | Page |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1001 | 1000 | Smart Grid mode<br>`smart_grid_mode` | select | Unscaled 16-bit enum; type cell unspecified | Core | 0: free_running; 1: forced_off; 2: recommended_on; 3: forced_on | 49 |
| 1002 | 1001 | Demand Control power limit<br>`demand_power_limit` | number | Pow16 / 100; kW | Core | 0..20 kW; step 0.01 | 49 |

Smart Grid uses the same four request labels as Altherma, but the device behavior is specific to air-to-air. Forced-off lasts at most two hours and disables Demand Control. HomeHub derives a capacity limit between 40% and 100% from HR 1002 and outdoor capacity; the register is not measured power consumption. Consult sections 10.3.1-10.3.2 for local interaction, restoration and comfort-target changes.

## Polling, validation and identity

The read-only setup probe is IR 21 (PDU 20) for Altherma or HR 1001 (PDU 1000) for air-to-air. Valid probe enums and documented markers are accepted; a response cannot establish hardware identity or authenticate a device. There is no separate gateway-connection-status register to inherit from another vendor's map.

Each poll reads only consecutive selected addresses, without undocumented gaps. A rejected/timed-out block clears only its fields and raw words. An isolated timeout triggers one profile-probe recheck. Connection/protocol failures, a failed probe recheck, or failure of every request fails the update. No-value markers and rejected groups are retried on subsequent polls. Explicit commands are serialized against polling, validate current target availability/limits, write once and refresh actual state. Ambiguous failed writes are not replayed.

Unique IDs use the config entry and semantic field key, independent of endpoint or profile. Reconfiguration preserves common identities, options and user names. After successful setup, obsolete fields are removed. In particular, Smart Grid keeps its identity across the two maps while its PDU address changes; fields outside the selected map cannot be read or written.
