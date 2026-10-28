"""Independent transcription of EKRHH 4P744838-1E, pp. 41-44 and 49.

These fixtures deliberately do not import the integration's register definitions.
Offsets are the one-based decimal numbers printed by Daikin.
"""

# offset: (entity key, representative wire word, decoded value)
HOLDING = {
    1: ("main_heating_setpoint", 35, 35),
    2: ("main_cooling_setpoint", 18, 18),
    3: ("operation_mode", 0, 0),
    4: ("space_conditioning", 1, True),
    6: ("room_heating_setpoint", 21, 21),
    7: ("room_cooling_setpoint", 25, 25),
    9: ("quiet_mode", 0, False),
    10: ("dhw_reheat_setpoint", 50, 50),
    12: ("dhw_reheat", 1, True),
    13: ("dhw_booster", 0, False),
    53: ("main_weather_mode", 1, 1),
    54: ("main_heating_offset", 65533, -3),
    55: ("main_cooling_offset", 2, 2),
    56: ("smart_grid_mode", 0, 0),
    57: ("buffering_power_limit", 450, 4.5),
    58: ("general_power_limit", 800, 8.0),
    59: ("main_thermostat_input", 0, False),
    61: ("additional_thermostat_input", 0, False),
    63: ("additional_heating_setpoint", 40, 40),
    64: ("additional_cooling_setpoint", 20, 20),
    65: ("additional_weather_mode", 3, 3),
    66: ("additional_heating_offset", 65535, -1),
    67: ("additional_cooling_offset", 0, 0),
}
INPUT = {
    21: ("unit_abnormality", 1, 1),
    22: ("unit_abnormality_code", 0x5538, "U8"),
    23: ("unit_abnormality_subcode", 12, 12),
    30: ("circulation_pump_running", 1, True),
    31: ("compressor_running", 1, True),
    32: ("booster_heater_running", 0, False),
    33: ("disinfection_running", 0, False),
    35: ("defrost", 0, False),
    36: ("hot_start", 0, False),
    37: ("three_way_valve", 1, 1),
    38: ("actual_operation_mode", 1, 1),
    40: ("leaving_water_phe_temperature", 3525, 35.25),
    41: ("leaving_water_buh_temperature", 3575, 35.75),
    42: ("return_water_temperature", 3125, 31.25),
    43: ("dhw_temperature", 4950, 49.5),
    44: ("outside_temperature", 65011, -5.25),
    45: ("liquid_refrigerant_temperature", 4025, 40.25),
    49: ("flow_rate", 1250, 12.5),
    50: ("room_temperature", 2125, 21.25),
    51: ("power_consumption", 425, 4.25),
    52: ("dhw_normal_operation", 0, False),
    53: ("space_normal_operation", 1, True),
    54: ("main_heating_lower_limit", 2500, 25.0),
    55: ("main_heating_upper_limit", 5500, 55.0),
    56: ("main_cooling_lower_limit", 500, 5.0),
    57: ("main_cooling_upper_limit", 2200, 22.0),
    58: ("additional_heating_lower_limit", 2500, 25.0),
    59: ("additional_heating_upper_limit", 6000, 60.0),
    60: ("additional_cooling_lower_limit", 700, 7.0),
    61: ("additional_cooling_upper_limit", 2300, 23.0),
    76: ("dhw_upper_temperature", 5000, 50.0),
    77: ("dhw_lower_temperature", 4000, 40.0),
    84: ("room_heating_lower_limit", 1400, 14.0),
    85: ("room_heating_upper_limit", 2800, 28.0),
    86: ("room_cooling_lower_limit", 1800, 18.0),
    87: ("room_cooling_upper_limit", 3200, 32.0),
}
AIR_TO_AIR = {
    1001: ("smart_grid_mode", 2, 2),
    1002: ("demand_power_limit", 625, 6.25),
}

# Manual page 7: these two profiles exclude HR 59 and 61.
PROFILES = {
    "altherma_3_h_ht": False,
    "altherma_3_h_mt": False,
    "altherma_3_r_erga": True,
    "altherma_3_r_erga_ech2o": False,
    "altherma_3_r_erla": False,
    "altherma_3_r_mt": False,
    "altherma_3_m_d": True,
    "altherma_3_m_e": False,
    "air_to_air": False,
}
