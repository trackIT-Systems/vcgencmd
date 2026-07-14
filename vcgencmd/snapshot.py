# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from .formatters import readings_to_dict
from .readings import Selection, collect

_UNSET = object()

GroupSources = Union[None, Sequence[str]]


def _normalize_group(sources: GroupSources) -> Optional[List[str]]:
    if sources is None or sources == []:
        return None
    return list(sources)


def selection_from_kwargs(
    *,
    clocks: Any = _UNSET,
    voltages: Any = _UNSET,
    temp: Any = _UNSET,
    codecs: Any = _UNSET,
    memory: Any = _UNSET,
    throttled: Any = _UNSET,
    pmic: Any = _UNSET,
    version: Any = _UNSET,
    bootloader: Any = _UNSET,
    rsts: Any = _UNSET,
    config_int: Any = _UNSET,
    config_str: Any = _UNSET,
) -> Selection:
    groups: Dict[str, Optional[List[str]]] = {}

    if clocks is not _UNSET:
        groups["clocks"] = _normalize_group(clocks)
    if voltages is not _UNSET:
        groups["voltages"] = _normalize_group(voltages)
    if temp is not _UNSET:
        groups["temperature"] = _normalize_group(temp)
    if codecs is not _UNSET:
        groups["codecs"] = _normalize_group(codecs)
    if memory is not _UNSET:
        groups["memory"] = _normalize_group(memory)
    if throttled is not _UNSET:
        groups["throttled"] = _normalize_group(throttled)
    if pmic is not _UNSET:
        groups["pmic"] = _normalize_group(pmic)
    if version is not _UNSET:
        groups["version"] = _normalize_group(version)
    if bootloader is not _UNSET:
        groups["bootloader"] = _normalize_group(bootloader)
    if rsts is not _UNSET:
        groups["rsts"] = None if rsts is True else _normalize_group(rsts)
    if config_int is not _UNSET:
        groups["config_int"] = _normalize_group(config_int)
    if config_str is not _UNSET:
        groups["config_str"] = _normalize_group(config_str)

    return Selection(groups=groups)


def read_all() -> Dict[str, Any]:
    """Return all telemetry groups as a nested dict.

    Equivalent to ``python3 -m vcgencmd -a -f json``.
    """
    return readings_to_dict(collect(Selection(all_groups=True)))


def read(
    *,
    clocks: GroupSources = _UNSET,
    voltages: GroupSources = _UNSET,
    temp: Any = _UNSET,
    codecs: GroupSources = _UNSET,
    memory: GroupSources = _UNSET,
    throttled: GroupSources = _UNSET,
    pmic: GroupSources = _UNSET,
    version: GroupSources = _UNSET,
    bootloader: GroupSources = _UNSET,
    rsts: Any = _UNSET,
    config_int: GroupSources = _UNSET,
    config_str: GroupSources = _UNSET,
) -> Dict[str, Any]:
    """Return selected telemetry groups as a nested dict.

    Omit a group keyword to exclude it. Pass ``None`` or an empty sequence to
    include every source in that group, or pass source names to limit the
    result.

    Example::

        read(clocks=["arm", "core"], temp=None)
    """
    selection = selection_from_kwargs(
        clocks=clocks,
        voltages=voltages,
        temp=temp,
        codecs=codecs,
        memory=memory,
        throttled=throttled,
        pmic=pmic,
        version=version,
        bootloader=bootloader,
        rsts=rsts,
        config_int=config_int,
        config_str=config_str,
    )
    if not selection.groups:
        raise ValueError("read() requires at least one group; use read_all() for everything")
    return readings_to_dict(collect(selection))


def _read_group(group: str, sources: GroupSources = None) -> Dict[str, Any]:
    """Return one telemetry group as a flat source-to-value dict."""
    selection = Selection(groups={group: _normalize_group(sources)})
    groups = collect(selection)
    if not groups:
        return {}
    return dict(groups[0].values)


def clocks(sources: GroupSources = None) -> Dict[str, Any]:
    """Return clock frequencies (Hz) as a flat dict."""
    return _read_group("clocks", sources)


def voltages(sources: GroupSources = None) -> Dict[str, Any]:
    """Return core/SDRAM voltages (V) as a flat dict."""
    return _read_group("voltages", sources)


def temperature(sources: GroupSources = None) -> Dict[str, Any]:
    """Return firmware temperatures (°C) as a flat dict keyed by ``soc`` / ``pmic``."""
    return _read_group("temperature", sources)


def temp(sources: GroupSources = None) -> Dict[str, Any]:
    """Alias for :func:`temperature`."""
    return temperature(sources)


def codecs(sources: GroupSources = None) -> Dict[str, Any]:
    """Return codec enablement flags as a flat dict."""
    return _read_group("codecs", sources)


def memory(sources: GroupSources = None) -> Dict[str, Any]:
    """Return ARM/GPU memory split (bytes) as a flat dict."""
    return _read_group("memory", sources)


def throttled(sources: GroupSources = None) -> Dict[str, Any]:
    """Return throttle and under-voltage flags as a flat dict."""
    return _read_group("throttled", sources)


def pmic(sources: GroupSources = None) -> Dict[str, Any]:
    """Return Pi 5 PMIC ADC readings as a flat dict."""
    return _read_group("pmic", sources)


def firmware_version(sources: GroupSources = None) -> Dict[str, Any]:
    """Return VideoCore firmware version fields as a flat dict."""
    return _read_group("version", sources)


def bootloader_version(sources: GroupSources = None) -> Dict[str, Any]:
    """Return EEPROM bootloader version fields as a flat dict."""
    return _read_group("bootloader", sources)


def rsts(sources: GroupSources = None) -> Dict[str, Any]:
    """Return PM_RSTS reset-reason flags as a flat dict of bools."""
    return _read_group("rsts", sources)


def config_int(sources: GroupSources = None) -> Dict[str, Any]:
    """Return integer firmware config keys as a flat dict."""
    return _read_group("config_int", sources)


def config_str(sources: GroupSources = None) -> Dict[str, Any]:
    """Return string firmware config keys as a flat dict."""
    return _read_group("config_str", sources)
