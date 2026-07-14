# vcgencmd - Native Python binding for Raspberry Pi vcgencmd

Python wrapper around Broadcom's `vcgencmd` tool for reading VideoCore firmware
telemetry on Raspberry Pi. Supports clocks, voltages, temperature, codecs,
memory split, throttle/under-voltage status, and (on Pi 5) PMIC ADC rails.

Requires Python 3.7+ and the `vcgencmd` binary on `PATH`.

## Install

```bash
# from PyPI / git
pip3 install git+https://github.com/nicmcd/vcgencmd.git

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
| `-a`, `--all` | Select every telemetry group (same as default) |
| `-f`, `--format` | `text` (default), `csv`, or `json` |
| `-i`, `--interval MS` | Poll every N milliseconds until interrupted |
| `--clocks [SOURCE ...]` | Clock frequencies (Hz); omit SOURCEs for all |
| `--voltages [SOURCE ...]` | Core/SDRAM voltages (V) |
| `--temp` | SoC temperature (°C) |
| `--codecs [SOURCE ...]` | Codec enablement |
| `--memory [SOURCE ...]` | ARM/GPU memory split (bytes) |
| `--throttled [FLAG ...]` | Throttle and under-voltage flags |
| `--pmic [SOURCE ...]` | Pi 5 PMIC ADC channels (A / V) |

**Selection:** no group flags → all groups. Any group flag → only those groups.
Within a group, omitting source names reads every source in that group.

**Interval mode:** loops until Ctrl+C. CSV prints the header once then appends
rows. JSON emits JSONL (`{"timestamp": "...", "readings": {...}}` per line).
Text prefixes each poll with a timestamp and separates polls with a blank line.

### Output formats

**Text** — grouped sections with aligned keys (PMIC split into voltage/current).

**JSON (single-shot)** — nested object, e.g.:

```json
{
  "clocks": {"arm": 2400000000},
  "temperature": {"soc": 48.8},
  "pmic": {
    "voltage": {"BATT_V": 2.56},
    "current": {"3V3_SYS_A": 0.056}
  }
}
```

**CSV** — `timestamp,group,key,value,unit` (PMIC rows use `pmic_voltage` /
`pmic_current` as the group column).

## Programmatic Usage

### Low-level API

Import `vcgencmd` for individual readings (each call spawns the `vcgencmd`
binary):

```python
import vcgencmd

vcgencmd.measure_clock("arm")       # -> int (Hz)
vcgencmd.measure_volts("core")      # -> float (V)
vcgencmd.measure_temp()             # -> float (°C)
vcgencmd.get_throttled()            # -> dict of bool flags
vcgencmd.pmic_read_all()            # -> dict (Pi 5 only)
vcgencmd.measure_pmic_adc("BATT_V") # -> float
```

Source lists: `frequency_sources()`, `voltage_sources()`, `codec_sources()`,
`memory_sources()`, `get_throttled_sources()`, `pmic_sources()`.

### Structured snapshots (CLI-equivalent dicts)

The CLI is built on `vcgencmd.readings` and `vcgencmd.formatters`. Use these
to get the same nested dict shape as `python3 -m vcgencmd -f json` without
shelling out:

```python
from vcgencmd.readings import Selection, collect
from vcgencmd.formatters import readings_to_dict, format_once

# equivalent to: python3 -m vcgencmd -a -f json
payload = readings_to_dict(collect(Selection()))

# equivalent to: --clocks arm --temp
selection = Selection(groups={"clocks": ["arm"], "temperature": None})
payload = readings_to_dict(collect(selection))

# as a formatted JSON string
json_text = format_once("json", collect(Selection()))
```

`Selection.groups` maps group names to `None` (all sources) or a list of
specific source names. An empty `Selection()` selects everything.

## Telemetry groups

| Group | Sources | Notes |
|-------|---------|-------|
| `clocks` | arm, core, h264, isp, v3d, uart, pwm, emmc, pixel, vec, hdmi, dpi | Hz |
| `voltages` | core, sdram_c, sdram_i, sdram_p | V |
| `temperature` | soc | °C |
| `codecs` | h264, mpg2, wvc1, mpg4, mjpg, wmv9 | bool |
| `memory` | arm, gpu | bytes |
| `throttled` | under_voltage, freq_capped, throttled, temp_limit, *_occurred | batched read |
| `pmic` | 26 channels (12 A, 14 V) | Pi 5 only; batched via `pmic_read_adc` |

PMIC alias: `BAT_RTC_V` maps to `BATT_V`.

## Package layout

```
vcgencmd/
  __init__.py      # re-exports low-level API; checks vcgencmd binary exists
  vcgencmd.py      # subprocess bindings to the vcgencmd binary
  readings.py      # group registry, Selection, collect()
  formatters.py    # text / csv / json output
  cli.py           # argparse CLI and interval polling loop
  __main__.py      # python -m vcgencmd entry point
pyproject.toml     # PEP 621 project metadata
```

## Integration example (pymqttutil)

Nested dict snapshots work directly with
[pymqttutil](https://github.com/trackIT-Systems/pymqttutil) — return a dict
from `func` and it is published as JSON:

```ini
[vcgencmd]
func = "readings_to_dict(collect(Selection()))"
requires = ["vcgencmd.readings", "vcgencmd.formatters"]
scheduling_interval = "5s"
```

## Authors

- Nic McDonald <nicci02@hotmail.com> — original package
- Jonas Höchst <hoechst@trackit.systems> — CLI, PMIC integration, packaging

## License

Apache License 2.0
