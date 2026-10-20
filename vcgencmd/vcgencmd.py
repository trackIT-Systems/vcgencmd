# Copyright 2014 Nic McDonald. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""vcgencmd: native binding for vcgencmd (Raspberry Pi)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from . import parsers, transport
from .errors import InvalidArgumentError, PmicUnavailableError
from .parsers import PMIC_ALIASES, RSTS_FLAGS, THROTTLED_FLAGS

__all__ = [
    "BOOTLOADER_FIELDS",
    "CODEC_SOURCES",
    "FREQUENCY_SOURCES",
    "MEMORY_SOURCES",
    "PMIC_ALIASES",
    "PMIC_SOURCES",
    "RSTS_SOURCES",
    "TEMPERATURE_SOURCES",
    "THROTTLED_SOURCES",
    "VERSION_FIELDS",
    "VOLTAGE_SOURCES",
    "InvalidArgumentError",
    "bootloader_version_sources",
    "codec_enabled",
    "codec_sources",
    "config_int_sources",
    "config_str_sources",
    "frequency_sources",
    "gencmd",
    "get_bootloader_version",
    "get_config_int",
    "get_config_str",
    "get_mem",
    "get_rsts",
    "get_rsts_raw",
    "get_rsts_sources",
    "get_throttled",
    "get_throttled_raw",
    "get_throttled_sources",
    "get_version",
    "measure_clock",
    "measure_pmic_adc",
    "measure_temp",
    "measure_temp_pmic",
    "measure_volts",
    "memory_sources",
    "pmic_read_all",
    "pmic_sources",
    "read_temperature",
    "temperature_sources",
    "version_sources",
    "voltage_sources",
]


def gencmd(command: str) -> str:
    """Run a raw gencmd command (e.g. ``"measure_clock arm"``) and return its output."""
    return transport.get_transport().gencmd(command)


def _checked(src: str, sources: Sequence[str]) -> str:
    src = src.lower()
    if src not in sources:
        raise InvalidArgumentError(f"{src} must be one of {list(sources)}")
    return src


FREQUENCY_SOURCES = ("arm", "core", "h264", "hevc", "isp", "v3d", "uart", "pwm", "emmc", "pixel", "vec", "hdmi", "dpi")


def frequency_sources() -> list[str]:
    return list(FREQUENCY_SOURCES)


def measure_clock(src: str) -> int:
    return parsers.parse_frequency(gencmd("measure_clock " + _checked(src, FREQUENCY_SOURCES)))


VOLTAGE_SOURCES = ("core", "sdram_c", "sdram_i", "sdram_p")


def voltage_sources() -> list[str]:
    return list(VOLTAGE_SOURCES)


def measure_volts(src: str) -> float:
    return parsers.parse_volts(gencmd("measure_volts " + _checked(src, VOLTAGE_SOURCES)))


TEMPERATURE_SOURCES = ("soc", "pmic")


def temperature_sources() -> list[str]:
    return list(TEMPERATURE_SOURCES)


def measure_temp() -> float:
    return parsers.parse_temp(gencmd("measure_temp"))


def measure_temp_pmic() -> float:
    return parsers.parse_temp(gencmd("measure_temp pmic"))


def read_temperature(src: str) -> float:
    if _checked(src, TEMPERATURE_SOURCES) == "pmic":
        return measure_temp_pmic()
    return measure_temp()


THROTTLED_SOURCES = (*THROTTLED_FLAGS, "raw")


def get_throttled_sources() -> list[str]:
    return list(THROTTLED_SOURCES)


def get_throttled_raw() -> int:
    return parsers.parse_hex_register(gencmd("get_throttled"))


def get_throttled(src: str | None = None) -> Any:
    """All flags as a dict of bools plus ``raw``; with ``src`` one flag or the raw value."""
    return parsers.decode_flags(get_throttled_raw(), THROTTLED_FLAGS, src)


CODEC_SOURCES = ("h264", "mpg2", "wvc1", "mpg4", "mjpg", "wmv9", "vp8")


def codec_sources() -> list[str]:
    return list(CODEC_SOURCES)


def codec_enabled(src: str) -> bool:
    return parsers.parse_codec(gencmd("codec_enabled " + _checked(src, CODEC_SOURCES)))


MEMORY_SOURCES = ("arm", "gpu")


def memory_sources() -> list[str]:
    return list(MEMORY_SOURCES)


def get_mem(src: str) -> int:
    return parsers.parse_mem(gencmd("get_mem " + _checked(src, MEMORY_SOURCES)))


PMIC_SOURCES = (
    "3V7_WL_SW_A",
    "3V3_SYS_A",
    "1V8_SYS_A",
    "DDR_VDD2_A",
    "DDR_VDDQ_A",
    "1V1_SYS_A",
    "0V8_SW_A",
    "VDD_CORE_A",
    "3V3_DAC_A",
    "3V3_ADC_A",
    "0V8_AON_A",
    "HDMI_A",
    "3V7_WL_SW_V",
    "3V3_SYS_V",
    "1V8_SYS_V",
    "DDR_VDD2_V",
    "DDR_VDDQ_V",
    "1V1_SYS_V",
    "0V8_SW_V",
    "VDD_CORE_V",
    "3V3_DAC_V",
    "3V3_ADC_V",
    "0V8_AON_V",
    "HDMI_V",
    "EXT5V_V",
    "BATT_V",
    "BAT_RTC_V",
)


def pmic_sources() -> list[str]:
    return list(PMIC_SOURCES)


def pmic_read_all() -> dict[str, float]:
    return parsers.parse_pmic(gencmd("pmic_read_adc"))


def measure_pmic_adc(src: str) -> float:
    src = src.upper()
    if src not in PMIC_SOURCES:
        raise InvalidArgumentError(f"{src} must be one of {list(PMIC_SOURCES)}")

    canonical = PMIC_ALIASES.get(src, src)
    readings = pmic_read_all()
    if canonical not in readings:
        raise PmicUnavailableError(f"no PMIC reading for '{src}'")
    return readings[canonical]


VERSION_FIELDS = ("date", "copyright", "version")


def version_sources() -> list[str]:
    return list(VERSION_FIELDS)


def get_version() -> dict[str, str]:
    return parsers.parse_version(gencmd("version"))


BOOTLOADER_FIELDS = ("date", "version", "timestamp", "update-time", "capabilities")


def bootloader_version_sources() -> list[str]:
    return list(BOOTLOADER_FIELDS)


def get_bootloader_version() -> dict[str, Any]:
    return parsers.parse_bootloader_version(gencmd("bootloader_version"))


RSTS_SOURCES = (*RSTS_FLAGS, "raw")


def get_rsts_sources() -> list[str]:
    return list(RSTS_SOURCES)


def get_rsts_raw() -> int:
    return parsers.parse_hex_register(gencmd("get_rsts"))


def get_rsts(src: str | None = None) -> Any:
    """All reset flags as a dict of bools plus ``raw``; with ``src`` one flag or the raw value."""
    return parsers.decode_flags(get_rsts_raw(), RSTS_FLAGS, src)


def _get_config(kind: str, key: str | None = None) -> Any:
    listing = "get_config " + kind
    if key is None:
        return parsers.parse_config(gencmd(listing))

    if not key or key in ("int", "str") or any(char.isspace() for char in key):
        raise InvalidArgumentError(f"invalid config key {key!r}")

    # "get_config int|str" lists only keys that differ from their default, and ignores
    # a key after it; "get_config <key>" also knows keys at their default
    raw = parsers.parse_config_value(gencmd("get_config " + key), key)
    if raw is not None:
        value = parsers.coerce_scalar(raw)
    else:
        # Indexed keys (e.g. hdmi_cvt:0) are only in the listing
        readings = parsers.parse_config(gencmd(listing))
        if key not in readings:
            raise InvalidArgumentError(f"unknown config key '{key}'")
        value = readings[key]

    if kind == "int" and not isinstance(value, int):
        raise InvalidArgumentError(f"config key '{key}' is not an integer: {value!r}")
    return value


def get_config_int(key: str | None = None) -> Any:
    """Integer config keys that differ from their default; with ``key``, that key's value."""
    return _get_config("int", key)


def get_config_str(key: str | None = None) -> Any:
    """String config keys that differ from their default; with ``key``, that key's value."""
    return _get_config("str", key)


def config_int_sources() -> list[str]:
    return list(get_config_int().keys())


def config_str_sources() -> list[str]:
    return list(get_config_str().keys())
