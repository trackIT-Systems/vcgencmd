# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import sys
import time

from . import vcgencmd
from .formatters import format_once, format_sample, format_timestamp
from .readings import PmicUnavailableError, Selection, collect


EPILOG = """\
examples:
  python -m vcgencmd
  python -m vcgencmd -f json --clocks arm
  python -m vcgencmd -f csv --voltages core sdram_p
  python -m vcgencmd -f csv -i 50 --clocks arm core
  python -m vcgencmd -f json -i 100 --temp
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m vcgencmd",
        description="Query Raspberry Pi VideoCore telemetry via vcgencmd.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="select every group, including version, bootloader, rsts, and config",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["text", "csv", "json"],
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        metavar="MS",
        help="poll interval in milliseconds; loop until interrupted",
    )
    parser.add_argument(
        "--clocks",
        nargs="*",
        default=None,
        metavar="SOURCE",
        choices=vcgencmd.frequency_sources(),
        help="clock frequencies; omit SOURCEs to read all clocks",
    )
    parser.add_argument(
        "--voltages",
        nargs="*",
        default=None,
        metavar="SOURCE",
        choices=vcgencmd.voltage_sources(),
        help="core/SDRAM voltages; omit SOURCEs to read all voltages",
    )
    parser.add_argument(
        "--temp",
        nargs="*",
        default=None,
        metavar="SOURCE",
        choices=vcgencmd.temperature_sources(),
        help="temperatures (°C); omit SOURCEs for soc and pmic (Pi 5)",
    )
    parser.add_argument(
        "--codecs",
        nargs="*",
        default=None,
        metavar="SOURCE",
        choices=vcgencmd.codec_sources(),
        help="codec enablement; omit SOURCEs to read all codecs",
    )
    parser.add_argument(
        "--memory",
        nargs="*",
        default=None,
        metavar="SOURCE",
        choices=vcgencmd.memory_sources(),
        help="ARM/GPU memory split; omit SOURCEs to read all memory values",
    )
    parser.add_argument(
        "--throttled",
        nargs="*",
        default=None,
        metavar="FLAG",
        choices=vcgencmd.get_throttled_sources(),
        help="throttle/under-voltage flags; omit FLAGs to read all",
    )
    parser.add_argument(
        "--pmic",
        nargs="*",
        default=None,
        metavar="SOURCE",
        choices=vcgencmd.pmic_sources(),
        help="Pi 5 PMIC ADC channels; omit SOURCEs to read all PMIC values",
    )
    parser.add_argument(
        "--version",
        nargs="*",
        default=None,
        metavar="FIELD",
        choices=vcgencmd.version_sources(),
        help="VideoCore firmware version; omit FIELDs for all",
    )
    parser.add_argument(
        "--bootloader",
        nargs="*",
        default=None,
        metavar="FIELD",
        choices=vcgencmd.bootloader_version_sources(),
        help="EEPROM bootloader version; omit FIELDs for all",
    )
    parser.add_argument(
        "--rsts",
        nargs="*",
        default=None,
        metavar="FLAG",
        choices=vcgencmd.get_rsts_sources(),
        help="reset reason flags (PM_RSTS); omit FLAGs to read all",
    )
    parser.add_argument(
        "--config-int",
        nargs="*",
        default=None,
        metavar="KEY",
        help="firmware integer config keys; omit KEYs for all",
    )
    parser.add_argument(
        "--config-str",
        nargs="*",
        default=None,
        metavar="KEY",
        help="firmware string config keys; omit KEYs for all",
    )
    return parser


def _group_value(selected):
    if selected is None:
        return None
    if selected == []:
        return None
    return list(selected)


def build_selection(args: argparse.Namespace) -> Selection:
    groups = {}

    if args.clocks is not None:
        groups["clocks"] = _group_value(args.clocks)
    if args.voltages is not None:
        groups["voltages"] = _group_value(args.voltages)
    if args.temp is not None:
        groups["temperature"] = _group_value(args.temp)
    if args.codecs is not None:
        groups["codecs"] = _group_value(args.codecs)
    if args.memory is not None:
        groups["memory"] = _group_value(args.memory)
    if args.throttled is not None:
        groups["throttled"] = _group_value(args.throttled)
    if args.pmic is not None:
        groups["pmic"] = _group_value(args.pmic)
    if args.version is not None:
        groups["version"] = _group_value(args.version)
    if args.bootloader is not None:
        groups["bootloader"] = _group_value(args.bootloader)
    if args.rsts is not None:
        groups["rsts"] = _group_value(args.rsts)
    if args.config_int is not None:
        groups["config_int"] = _group_value(args.config_int)
    if args.config_str is not None:
        groups["config_str"] = _group_value(args.config_str)

    if args.all:
        return Selection(all_groups=True)
    if not groups:
        return Selection()

    return Selection(groups=groups)


def run_poll_loop(selection: Selection, interval_ms: int, fmt: str) -> int:
    interval_sec = interval_ms / 1000.0
    warned = False
    poll_count = 0
    header_printed = False

    try:
        while True:
            t0 = time.monotonic()
            groups = collect(selection)
            timestamp = format_timestamp()

            if fmt == "csv":
                output = format_sample(
                    fmt,
                    groups,
                    timestamp,
                    include_header=not header_printed,
                    streaming=True,
                )
                header_printed = True
            else:
                if fmt == "text" and poll_count > 0:
                    print()
                output = format_sample(
                    fmt,
                    groups,
                    timestamp,
                    streaming=True,
                )

            if output:
                print(output)
            sys.stdout.flush()
            poll_count += 1

            elapsed = time.monotonic() - t0
            if elapsed > interval_sec and not warned:
                print(
                    "warning: poll time ({0:.3f}s) exceeds interval ({1}ms); "
                    "subprocess overhead may limit achievable rate".format(
                        elapsed, interval_ms),
                    file=sys.stderr,
                )
                warned = True

            sleep_for = interval_sec - (time.monotonic() - t0)
            if sleep_for > 0:
                time.sleep(sleep_for)
    except KeyboardInterrupt:
        if poll_count:
            print("stopped after {0} poll(s)".format(poll_count), file=sys.stderr)
        return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.interval is not None and args.interval <= 0:
        parser.error("interval must be a positive integer (milliseconds)")

    selection = build_selection(args)

    try:
        if args.interval is None:
            groups = collect(selection)
            print(format_once(args.format, groups))
            return 0
        return run_poll_loop(selection, args.interval, args.format)
    except PmicUnavailableError as exc:
        print("error: PMIC readings unavailable: {0}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
