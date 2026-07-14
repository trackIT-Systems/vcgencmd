# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from . import vcgencmd


class PmicUnavailableError(Exception):
    pass


@dataclass
class ReadingGroup:
    name: str
    label: str
    unit: Optional[str]
    values: Dict[str, Any]


@dataclass
class Selection:
    """Telemetry group selection for the CLI.

    An empty ``groups`` dict means select every group and every source.
    Each key maps to ``None`` (all sources in the group) or a list of
    specific source names.
    """

    groups: Dict[str, Optional[List[str]]] = field(default_factory=dict)
    all_groups: bool = False

    def wants_group(self, name: str) -> bool:
        if self.all_groups or not self.groups:
            return True
        return name in self.groups

    def sources_for(self, name: str, all_sources: List[str]) -> List[str]:
        if not self.groups:
            return list(all_sources)
        selected = self.groups.get(name)
        if selected is None:
            return list(all_sources)
        return list(selected)

    def pmic_explicit(self) -> bool:
        return "pmic" in self.groups


@dataclass(frozen=True)
class GroupSpec:
    name: str
    label: str
    unit: Optional[str]
    sources: Callable[[], List[str]]
    read: Callable[..., Any]
    batched: bool = False
    default: bool = True


GROUPS: Dict[str, GroupSpec] = {
    "clocks": GroupSpec(
        name="clocks",
        label="Clock Frequencies",
        unit="Hz",
        sources=vcgencmd.frequency_sources,
        read=vcgencmd.measure_clock,
    ),
    "voltages": GroupSpec(
        name="voltages",
        label="Voltages",
        unit="V",
        sources=vcgencmd.voltage_sources,
        read=vcgencmd.measure_volts,
    ),
    "temperature": GroupSpec(
        name="temperature",
        label="Temperatures",
        unit="C",
        sources=vcgencmd.temperature_sources,
        read=vcgencmd.read_temperature,
    ),
    "codecs": GroupSpec(
        name="codecs",
        label="Codecs Enabled",
        unit=None,
        sources=vcgencmd.codec_sources,
        read=vcgencmd.codec_enabled,
    ),
    "memory": GroupSpec(
        name="memory",
        label="Memory Allocation",
        unit="bytes",
        sources=vcgencmd.memory_sources,
        read=vcgencmd.get_mem,
    ),
    "throttled": GroupSpec(
        name="throttled",
        label="Throttled Status",
        unit=None,
        sources=vcgencmd.get_throttled_sources,
        read=vcgencmd.get_throttled,
        batched=True,
    ),
    "pmic": GroupSpec(
        name="pmic",
        label="PMIC",
        unit=None,
        sources=vcgencmd.pmic_sources,
        read=vcgencmd.measure_pmic_adc,
        batched=True,
    ),
    "version": GroupSpec(
        name="version",
        label="Firmware Version",
        unit=None,
        sources=vcgencmd.version_sources,
        read=vcgencmd.get_version,
        batched=True,
        default=False,
    ),
    "bootloader": GroupSpec(
        name="bootloader",
        label="Bootloader Version",
        unit=None,
        sources=vcgencmd.bootloader_version_sources,
        read=vcgencmd.get_bootloader_version,
        batched=True,
        default=False,
    ),
    "rsts": GroupSpec(
        name="rsts",
        label="Reset Status",
        unit=None,
        sources=vcgencmd.get_rsts_sources,
        read=vcgencmd.get_rsts,
        batched=True,
        default=False,
    ),
    "config_int": GroupSpec(
        name="config_int",
        label="Firmware Config (int)",
        unit=None,
        sources=vcgencmd.config_int_sources,
        read=vcgencmd.get_config_int,
        batched=True,
        default=False,
    ),
    "config_str": GroupSpec(
        name="config_str",
        label="Firmware Config (str)",
        unit=None,
        sources=vcgencmd.config_str_sources,
        read=vcgencmd.get_config_str,
        batched=True,
        default=False,
    ),
}

GROUP_ORDER = [
    "clocks",
    "voltages",
    "temperature",
    "codecs",
    "memory",
    "throttled",
    "pmic",
    "version",
    "bootloader",
    "rsts",
    "config_int",
    "config_str",
]


def _collect_batched_dict(
    spec: GroupSpec,
    sources: List[str],
    readings: Dict[str, Any],
) -> ReadingGroup:
    if sources:
        values = {}
        for src in sources:
            if src not in readings:
                raise vcgencmd.InvalidArgumentError(
                    "unknown {0} key '{1}'".format(spec.name, src))
            values[src] = readings[src]
    else:
        values = dict(readings)
    return ReadingGroup(spec.name, spec.label, spec.unit, values)


def _collect_batched_status(
    spec: GroupSpec,
    sources: List[str],
    readings: Dict[str, Any],
) -> ReadingGroup:
    values = {src: readings[src] for src in sources}
    values["raw"] = readings["raw"]
    return ReadingGroup(spec.name, spec.label, spec.unit, values)


def _collect_batched_throttled(spec: GroupSpec, sources: List[str]) -> ReadingGroup:
    return _collect_batched_status(spec, sources, vcgencmd.get_throttled())


def _collect_batched_rsts(spec: GroupSpec, sources: List[str]) -> ReadingGroup:
    return _collect_batched_status(spec, sources, vcgencmd.get_rsts())


def _collect_batched_pmic(spec: GroupSpec, sources: List[str]) -> ReadingGroup:
    from .vcgencmd import __kPmicAliases

    try:
        readings = vcgencmd.pmic_read_all()
    except Exception as exc:
        raise PmicUnavailableError(str(exc)) from exc

    values = {}
    for src in sources:
        canonical = __kPmicAliases.get(src, src)
        if canonical not in readings:
            raise PmicUnavailableError("unknown output for '{0}'".format(src))
        values[src] = readings[canonical]

    return ReadingGroup(spec.name, spec.label, spec.unit, values)


def _collect_temperature(spec: GroupSpec, sources: List[str]) -> ReadingGroup:
    values = {}
    for src in sources:
        try:
            values[src] = spec.read(src)
        except Exception:
            if src == "pmic" and len(sources) > 1:
                continue
            raise
    return ReadingGroup(spec.name, spec.label, spec.unit, values)


def _collect_simple(spec: GroupSpec, sources: List[str]) -> ReadingGroup:
    values = {}
    for src in sources:
        values[src] = spec.read(src)
    return ReadingGroup(spec.name, spec.label, spec.unit, values)


def collect(selection: Selection) -> List[ReadingGroup]:
    results: List[ReadingGroup] = []

    for name in GROUP_ORDER:
        if not selection.wants_group(name):
            continue

        spec = GROUPS[name]
        if not selection.groups and not spec.default and not selection.all_groups:
            continue

        sources = selection.sources_for(name, spec.sources())

        if spec.batched and name == "throttled":
            results.append(_collect_batched_throttled(spec, sources))
        elif spec.batched and name == "rsts":
            results.append(_collect_batched_rsts(spec, sources))
        elif spec.batched and name == "pmic":
            try:
                results.append(_collect_batched_pmic(spec, sources))
            except PmicUnavailableError:
                if selection.pmic_explicit():
                    raise
        elif spec.batched and name in ("version", "bootloader", "config_int", "config_str"):
            results.append(_collect_batched_dict(spec, sources, spec.read()))
        elif name == "temperature":
            results.append(_collect_temperature(spec, sources))
        elif not sources:
            continue
        else:
            results.append(_collect_simple(spec, sources))

    return results
