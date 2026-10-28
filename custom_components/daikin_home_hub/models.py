"""Compatibility profiles from EKRHH 4P744838-1E, pp. 7-8."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .registers import AIR_TO_AIR_REGISTERS, ALTHERMA_REGISTERS, Register


@dataclass(frozen=True)
class ModelProfile:
    name: str
    equipment: str
    micon: str | None
    air_to_air: bool = False
    excluded_fields: frozenset[str] = frozenset()

    @property
    def registers(self) -> Mapping[str, Register]:
        return AIR_TO_AIR_REGISTERS if self.air_to_air else ALTHERMA_REGISTERS

    def supports(self, key: str) -> bool:
        return key in self.registers and key not in self.excluded_fields


_NO_THERMOSTAT = frozenset({"main_thermostat_input", "additional_thermostat_input"})
MODELS = MappingProxyType(
    {
        "altherma_3_h_ht": ModelProfile(
            "Daikin Altherma 3 H HT", "EPRA14/16/18DV37/W17", "20017705"
        ),
        "altherma_3_h_mt": ModelProfile(
            "Daikin Altherma 3 H MT", "EPRA08/10/12EV3/W1", "20007903"
        ),
        "altherma_3_r_erga": ModelProfile(
            "Daikin Altherma 3 R ERGA floor/wall",
            "ERGA-EV(7)(H)(A), EHVH/X/Z-E or EHBH/X-E",
            "20002203",
            excluded_fields=_NO_THERMOSTAT,
        ),
        "altherma_3_r_erga_ech2o": ModelProfile(
            "Daikin Altherma 3 R ERGA ECH₂O",
            "ERGA-EV(7)(H)(A), EHSH(B)/X(B)-P-E",
            "20017704",
        ),
        "altherma_3_r_erla": ModelProfile(
            "Daikin Altherma 3 R ERLA", "ERLA11/14/16DV3/W1", "20007903"
        ),
        "altherma_3_r_mt": ModelProfile(
            "Daikin Altherma 3 R MT", "ERRA-EV3/W1", "22009C01"
        ),
        "altherma_3_m_d": ModelProfile(
            "Daikin Altherma 3 M D-series",
            "EBLA/EDLA09/11/14/16D",
            "20002203",
            excluded_fields=_NO_THERMOSTAT,
        ),
        "altherma_3_m_e": ModelProfile(
            "Daikin Altherma 3 M E-series", "EBLA/EDLA04/06/08E", "20017704"
        ),
        "air_to_air": ModelProfile(
            "Daikin air-to-air installation",
            "BRP069C4* WLAN adapter, outdoor Demand Control, maximum 5 units",
            None,
            air_to_air=True,
        ),
    }
)
