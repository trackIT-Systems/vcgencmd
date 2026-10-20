# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

"""Pure parsers for gencmd response text; no I/O."""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional, Tuple, Union

from .errors import InvalidArgumentError, ParseError

# Flag name -> (bit, description)
FlagTable = Mapping[str, Tuple[int, str]]

THROTTLED_FLAGS: FlagTable = {
    "under_voltage": (0, "Under-voltage detected"),
    "freq_capped": (1, "Arm frequency capped"),
    "throttled": (2, "Currently throttled"),
    "temp_limit": (3, "Soft temperature limit active"),
    "under_voltage_occurred": (16, "Under-voltage has occurred"),
    "freq_capped_occurred": (17, "Arm frequency capped has occurred"),
    "throttling_occurred": (18, "Throttling has occurred"),
    "temp_limit_occurred": (19, "Soft temperature limit has occurred"),
}

RSTS_FLAGS: FlagTable = {
    "debugger_quick_reset": (0, "Had a debugger quick reset"),
    "debugger_full_reset": (1, "Had a debugger full reset"),
    "debugger_hard_reset": (2, "Had a debugger hard reset"),
    "watchdog_quick_reset": (4, "Had a watchdog quick reset"),
    "watchdog_full_reset": (5, "Had a watchdog full reset"),
    "watchdog_hard_reset": (6, "Had a watchdog hard reset"),
    "software_quick_reset": (8, "Had a software quick reset"),
    "software_full_reset": (9, "Had a software full reset"),
    "software_hard_reset": (10, "Had a software hard reset"),
    "power_on_reset": (12, "Had a power-on reset"),
}

# Alias -> channel name in pmic_read_adc output
PMIC_ALIASES = {
    "BAT_RTC_V": "BATT_V",
}

_PMIC_PATTERN = re.compile(
    r"^\s*([A-Za-z0-9_]+)\s+(current|volt)\(\d+\)=([0-9.]+)([AV])",
    re.MULTILINE,
)

_MEM_UNITS = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}


def _value(output: str) -> str:
    """The part after '=' of a single ``key=value`` line."""
    key, sep, value = output.strip().partition("=")
    if not sep:
        raise ParseError("expected key=value, got {0!r}".format(output))
    return value.strip()


def _number(convert, text: str, output: str):
    try:
        return convert(text)
    except ValueError:
        raise ParseError("cannot parse {0!r}".format(output)) from None


def parse_frequency(output: str) -> int:
    """``frequency(0)=2400027136`` -> Hz."""
    return _number(int, _value(output), output)


def parse_volts(output: str) -> float:
    """``volt=0.8605V`` -> V."""
    return _number(float, _value(output).rstrip("V"), output)


def parse_temp(output: str) -> float:
    """``temp=47.7'C`` -> °C."""
    return _number(float, _value(output).rstrip("'C"), output)


def parse_hex_register(output: str) -> int:
    """``throttled=0x0`` or ``get_rsts=1000`` -> register value (always hex)."""
    return _number(lambda text: int(text, 16), _value(output), output)


def parse_mem(output: str) -> int:
    """``arm=1020M`` -> bytes."""
    value = _value(output)
    unit = _MEM_UNITS.get(value[-1:])
    if unit is None:
        raise ParseError("unknown memory unit in {0!r}".format(output))
    return _number(int, value[:-1], output) * unit


def parse_codec(output: str) -> bool:
    """``h264=enabled`` / ``h264=disabled`` -> bool."""
    status = _value(output)
    if status == "enabled":
        return True
    if status == "disabled":
        return False
    raise ParseError("unknown codec status {0!r}".format(status))


def parse_pmic(output: str) -> Dict[str, float]:
    """``pmic_read_adc`` output -> channel name -> A / V, including aliases."""
    readings = {}
    for match in _PMIC_PATTERN.finditer(output):
        name, _, value, _ = match.groups()
        readings[name] = float(value)

    for alias, canonical in PMIC_ALIASES.items():
        if canonical in readings:
            readings[alias] = readings[canonical]

    return readings


def _lines(output: str):
    return [line.strip() for line in output.splitlines() if line.strip()]


def coerce_scalar(value: str) -> Union[int, str]:
    if value.startswith("0x"):
        try:
            return int(value, 16)
        except ValueError:
            return value
    try:
        return int(value)
    except ValueError:
        return value


def parse_version(output: str) -> Dict[str, str]:
    """``version`` output: date line, copyright line, version line."""
    lines = _lines(output)
    readings = {}
    if lines:
        readings["date"] = lines[0]
    for line in lines[1:]:
        if line.startswith("version "):
            readings["version"] = line[len("version "):]
        elif line.startswith("Copyright"):
            readings["copyright"] = line
    return readings


def parse_bootloader_version(output: str) -> Dict[str, Any]:
    """``bootloader_version`` output: optional date line, then ``key value`` lines."""
    lines = _lines(output)
    readings: Dict[str, Any] = {}
    start = 0
    if lines and "/" in lines[0] and " " in lines[0]:
        readings["date"] = lines[0]
        start = 1
    for line in lines[start:]:
        if line.startswith("version "):
            readings["version"] = line[len("version "):]
        elif " " in line:
            key, _, value = line.partition(" ")
            readings[key] = coerce_scalar(value)
    return readings


def parse_config(output: str) -> Dict[str, Union[int, str]]:
    """``get_config int|str`` output: ``key=value`` lines."""
    readings = {}
    for line in _lines(output):
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        readings[key.strip()] = coerce_scalar(value.strip())
    return readings


def decode_flags(value: int, flags: FlagTable, src: Optional[str] = None) -> Any:
    """Decode a status register.

    Without ``src``: dict of every flag as bool plus ``raw``. With ``src``:
    that flag as bool, or the register value for ``"raw"``.
    """
    if src == "raw":
        return value
    if src:
        if src not in flags:
            raise InvalidArgumentError("{0} must be one of {1}".format(src, [*flags, "raw"]))
        bit, _ = flags[src]
        return bool(value & (1 << bit))

    readings: Dict[str, Any] = {key: bool(value & (1 << bit)) for key, (bit, _) in flags.items()}
    readings["raw"] = value
    return readings
