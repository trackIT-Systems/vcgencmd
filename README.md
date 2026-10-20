# vcgencmd - Raspberry Pi VideoCore firmware telemetry for Python

Reads VideoCore firmware telemetry on Raspberry Pi: clocks, voltages,
temperature, codecs, memory split, throttle/under-voltage status, and (on Pi 5)
PMIC ADC rails.

The package sends gencmd commands to the firmware itself, through the same
mailbox ioctl the `vcgencmd` binary uses. The binary does not need to be
installed. See [Firmware access](#firmware-access).

Requires Python 3.9+ and read access to `/dev/vcio_gencmd` (group `video`) or
`/dev/vcio` (root).

## Install

```bash
# from PyPI / git
pip3 install git+https://github.com/trackIT-Systems/vcgencmd.git

# editable from source
pip3 install -e .
```

Packaging uses `pyproject.toml` (PEP 517/518, setuptools build backend). The
version string is read dynamically from `vcgencmd.__version__`.

## Command-Line Interface

Entry point: `python3 -m vcgencmd`

Run `python3 -m vcgencmd --help` for full usage. With no group flags, all
telemetry groups are collected and printed in grouped text format.

### Examples

```bash
# All readings, grouped text (default)
python3 -m vcgencmd

# JSON output for selected clocks and temperature
python3 -m vcgencmd -f json --clocks arm core --temp

# CSV snapshot of voltages
python3 -m vcgencmd -f csv --voltages core sdram_p

# Stream CSV rows every 50 ms (Ctrl+C to stop)
python3 -m vcgencmd -f csv -i 50 --clocks arm

# Stream JSONL every 100 ms
python3 -m vcgencmd -f json -i 100 --temp

# Pi 5 PMIC channels
python3 -m vcgencmd --pmic BATT_V EXT5V_V

# Throttle flags subset
python3 -m vcgencmd --throttled throttled under_voltage_occurred
```

### Flags

| Flag | Description |
|------|-------------|
| `-a`, `--all` | Every group, including version, bootloader, rsts, and config |
| `-f`, `--format` | `text` (default), `csv`, or `json` |
| `-i`, `--interval MS` | Poll every N milliseconds until interrupted |
| `--clocks [SOURCE ...]` | Clock frequencies (Hz); omit SOURCEs for all |
| `--voltages [SOURCE ...]` | Core/SDRAM voltages (V) |
| `--temp [SOURCE ...]` | SoC and/or PMIC temperature (°C); omit for both |
| `--codecs [SOURCE ...]` | Codec enablement |
| `--memory [SOURCE ...]` | ARM/GPU memory split (bytes) |
| `--throttled [FLAG ...]` | Throttle and under-voltage flags |
| `--pmic [SOURCE ...]` | Pi 5 PMIC ADC channels (A / V) |
| `--version [FIELD ...]` | VideoCore firmware version (opt-in) |
| `--bootloader [FIELD ...]` | EEPROM bootloader version (opt-in) |
| `--rsts [FLAG ...]` | Reset reason flags (PM_RSTS); omit for all |
| `--config-int [KEY ...]` | Integer firmware config keys (opt-in) |
| `--config-str [KEY ...]` | String firmware config keys (opt-in) |

**Selection:** no group flags → default telemetry groups. `-a` / `--all` → every
group (including opt-in identity/config groups). Any other group flag → only
those groups.
Within a group, omitting source names reads every source in that group.

**Interval mode:** loops until Ctrl+C. CSV prints the header once then appends
rows. JSON emits JSONL (`{"timestamp": "...", "readings": {...}}` per line).
Text prefixes each poll with a timestamp and separates polls with a blank line.

### Output formats

**Text** — grouped sections with aligned keys.

**JSON (single-shot)** — nested object by telemetry group, e.g.:

```json
{
  "clocks": {"arm": 2400000000},
  "temperature": {"soc": 48.8, "pmic": 50.6},
  "pmic": {
    "BATT_V": 2.56,
    "3V3_SYS_A": 0.056
  }
}
```

**CSV** — `timestamp,group,key,value,unit` (PMIC channels use group `pmic`).

## Programmatic Usage

### Low-level API

Import `vcgencmd` for individual readings (each call is one gencmd command):

```python
import vcgencmd

vcgencmd.measure_clock("arm")       # -> int (Hz)
vcgencmd.measure_volts("core")      # -> float (V)
vcgencmd.measure_temp()             # -> float (°C), SoC
vcgencmd.measure_temp_pmic()        # -> float (°C), PMIC (Pi 5)
vcgencmd.get_version()              # -> dict
vcgencmd.get_bootloader_version()   # -> dict
vcgencmd.get_rsts()                 # -> dict of bool flags + raw int
vcgencmd.get_rsts_raw()             # -> int (PM_RSTS register)
vcgencmd.get_config_int()           # -> dict
vcgencmd.get_config_str()           # -> dict
vcgencmd.get_throttled()            # -> dict of bool flags + raw int
vcgencmd.get_throttled_raw()        # -> int (throttled register)
vcgencmd.pmic_read_all()            # -> dict (Pi 5 only)
vcgencmd.measure_pmic_adc("BATT_V") # -> float
vcgencmd.gencmd("get_config arm_freq")  # -> str, any raw gencmd command
```

Source lists: `frequency_sources()`, `voltage_sources()`, `codec_sources()`,
`memory_sources()`, `get_throttled_sources()`, `get_rsts_sources()`, `pmic_sources()`,
`version_sources()`, `bootloader_version_sources()`.

### Group helpers (flat dicts)

Each telemetry group has a dedicated helper that returns a **flat** dict —
ideal for mqttutil and other consumers that cannot handle nesting:

```python
import vcgencmd

vcgencmd.pmic()                          # all PMIC channels
vcgencmd.pmic(["BATT_V", "3V3_SYS_A"])   # subset
vcgencmd.throttled()
vcgencmd.clocks(["arm"])
vcgencmd.temperature()                   # {"soc": 48.8, "pmic": 50.6}
vcgencmd.temperature(["pmic"])            # PMIC only
```

Available: `clocks()`, `voltages()`, `temperature()` / `temp()`, `codecs()`,
`memory()`, `throttled()`, `pmic()`, `firmware_version()`, `bootloader_version()`,
`rsts()`, `config_int()`, `config_str()`. Pass `None` or omit sources for all
entries in that group.

### Structured snapshots (nested by group)

Use `read_all()` or `read()` for the same nested dict shape as
`python3 -m vcgencmd -f json`:

```python
import vcgencmd

# equivalent to: python3 -m vcgencmd -a -f json
payload = vcgencmd.read_all()

# equivalent to: --clocks arm --temp
payload = vcgencmd.read(clocks=["arm"], temp=None)

# firmware identity / config (opt-in groups)
payload = vcgencmd.read(version=None, rsts=True)
payload = vcgencmd.read(config_int=["arm_freq", "total_mem"])

# all clocks in the group
payload = vcgencmd.read(clocks=None)
```

Omit a keyword to exclude that group. Pass `None` or `[]` to include every
source in a group, or pass source names to limit the result.

Lower-level building blocks remain available:

```python
from vcgencmd.readings import Selection, collect
from vcgencmd.formatters import readings_to_dict, format_once

payload = readings_to_dict(collect(Selection()))
json_text = format_once("json", collect(Selection()))
```

## Firmware access

`vcgencmd.transport.Mailbox` opens `/dev/vcio_gencmd` and falls back to
`/dev/vcio`, in the same order as the `vcgencmd` binary.
`/dev/vcio_gencmd` only allows gencmd and is usually `root:video 0660`;
`/dev/vcio` is the full mailbox and usually root-only. The device is opened on
the first command and kept open; one mailbox is shared by the whole process,
and threads may use it concurrently.

`import vcgencmd` raises `ImportError` when neither device node exists, so
callers can treat a failed import as "not a Raspberry Pi". The check only looks
for the device nodes; nothing is sent to the firmware.

To use a different transport, e.g. a fake in tests, pass any object with a
`gencmd(command) -> str` method to `vcgencmd.transport.set_transport()`.

### Errors

All errors derive from `vcgencmd.VcgencmdError`:

| Exception | Raised when |
|-----------|-------------|
| `DeviceUnavailableError` | no mailbox device could be opened (`.errors` holds the `OSError` per device) |
| `MailboxError` | the ioctl failed or the firmware rejected the mailbox request |
| `GencmdError` | the firmware returned a non-zero status, e.g. an unknown command (`.command`, `.status`, `.message`) |
| `ParseError` | the output had an unexpected format (also a `ValueError`) |
| `InvalidArgumentError` | unknown source, flag or config key (also a `ValueError`) |
| `PmicUnavailableError` | no PMIC readings (only Raspberry Pi 5 has a PMIC ADC) |

## Telemetry groups

| Group | Sources | Notes |
|-------|---------|-------|
| `clocks` | arm, core, h264, hevc, isp, v3d, uart, pwm, emmc, pixel, vec, hdmi, dpi | Hz |
| `voltages` | core, sdram_c, sdram_i, sdram_p | V |
| `temperature` | soc, pmic | °C; pmic via `measure_temp pmic` (Pi 5) |
| `codecs` | h264, mpg2, wvc1, mpg4, mjpg, wmv9, vp8 | bool |
| `memory` | arm, gpu | bytes |
| `throttled` | under_voltage, freq_capped, throttled, temp_limit, *_occurred, raw | batched read |
| `pmic` | 26 channels (12 A, 14 V) | Pi 5 only; batched via `pmic_read_adc` |
| `version` | date, copyright, version | opt-in; not in default output |
| `bootloader` | date, version, timestamp, update-time, capabilities | opt-in |
| `rsts` | debugger_*, watchdog_*, software_*, power_on_reset, raw | batched read; PM_RSTS flags |
| `config_int` | firmware keys | opt-in; batched `get_config int` |
| `config_str` | firmware keys | opt-in; batched `get_config str` |

PMIC alias: `BAT_RTC_V` maps to `BATT_V`.

## Package layout

```
vcgencmd/
  __init__.py      # re-exports the public API; checks a mailbox device exists
  transport.py     # mailbox ioctl: Mailbox, set_transport()
  parsers.py       # pure parsers for gencmd output
  errors.py        # exception hierarchy
  vcgencmd.py      # low-level API: one function per reading
  snapshot.py      # group helpers, read(), read_all()
  readings.py      # group registry, Selection, collect()
  formatters.py    # text / csv / json output
  cli.py           # argparse CLI and interval polling loop
  __main__.py      # python -m vcgencmd entry point
tests/             # unit tests with captured firmware output; device tests
pyproject.toml     # PEP 621 project metadata
```

## Tests

```bash
pip3 install -e ".[test]"
python3 -m pytest              # unit tests, run anywhere
python3 -m pytest -m device    # against the firmware, on a Raspberry Pi
```

Unit tests replace the mailbox with a fake that answers from output captured
on a Raspberry Pi 5 (`tests/fixtures/pi5/`). Device tests compare with the
`vcgencmd` binary when it is installed.

## Integration example (pymqttutil)

Nested dict snapshots work directly with
[pymqttutil](https://github.com/trackIT-Systems/pymqttutil) — return a dict
from `func` and it is published as JSON:

```ini
[vcgencmd]
func = "vcgencmd.pmic()"
requires = ["vcgencmd"]
scheduling_interval = "5s"
```

## Authors

- Nic McDonald <nicci02@hotmail.com> — original package
- Jonas Höchst <hoechst@trackit.systems> — CLI, PMIC integration, mailbox transport, packaging

## License

Apache License 2.0
