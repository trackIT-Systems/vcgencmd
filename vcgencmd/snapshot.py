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
    temp: bool = False,
    codecs: Any = _UNSET,
    memory: Any = _UNSET,
    throttled: Any = _UNSET,
    pmic: Any = _UNSET,
) -> Selection:
    groups: Dict[str, Optional[List[str]]] = {}

    if clocks is not _UNSET:
        groups["clocks"] = _normalize_group(clocks)
    if voltages is not _UNSET:
        groups["voltages"] = _normalize_group(voltages)
    if temp:
        groups["temperature"] = None
    if codecs is not _UNSET:
        groups["codecs"] = _normalize_group(codecs)
    if memory is not _UNSET:
        groups["memory"] = _normalize_group(memory)
    if throttled is not _UNSET:
        groups["throttled"] = _normalize_group(throttled)
    if pmic is not _UNSET:
        groups["pmic"] = _normalize_group(pmic)

    return Selection(groups=groups)


def read_all() -> Dict[str, Any]:
    """Return all telemetry groups as a nested dict.

    Equivalent to ``python3 -m vcgencmd -a -f json``.
    """
    return readings_to_dict(collect(Selection()))


def read(
    *,
    clocks: GroupSources = _UNSET,
    voltages: GroupSources = _UNSET,
    temp: bool = False,
    codecs: GroupSources = _UNSET,
    memory: GroupSources = _UNSET,
    throttled: GroupSources = _UNSET,
    pmic: GroupSources = _UNSET,
) -> Dict[str, Any]:
    """Return selected telemetry groups as a nested dict.

    Omit a group keyword to exclude it. Pass ``None`` or an empty sequence to
    include every source in that group, or pass source names to limit the
    result.

    Example::

        read(clocks=["arm", "core"], temp=True)
    """
    selection = selection_from_kwargs(
        clocks=clocks,
        voltages=voltages,
        temp=temp,
        codecs=codecs,
        memory=memory,
        throttled=throttled,
        pmic=pmic,
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


def temperature() -> Dict[str, Any]:
    """Return SoC temperature (°C) as a flat dict keyed by ``soc``."""
    return _read_group("temperature", None)


def temp() -> Dict[str, Any]:
    """Alias for :func:`temperature`."""
    return temperature()


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
