# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-10-20

### Fixed

- `get_config_int(key)`, `get_config_str(key)`, `--config-int KEY` and
  `config_int([...])` find keys at their default value (e.g. `over_voltage`):
  they look the key up with `get_config <key>` instead of searching the
  `get_config int|str` listing, which only contains keys that differ from their
  default. Indexed keys such as `hdmi_cvt:0` still come from the listing
- `get_config_int(key)` raises `InvalidArgumentError` for keys that are not
  integers

### Changed

- Requires Python 3.11+ (3.9 and 3.10 are end of life or not shipped by
  supported Raspberry Pi OS releases)
- Code follows ruff's default rules and formatting; CI checks both
- CI uses current major versions of its GitHub Actions

## [0.4.0] - 2026-10-20

### Changed

- Commands go to the firmware through the mailbox ioctl on `/dev/vcio_gencmd`
  (falling back to `/dev/vcio`) instead of running the `vcgencmd` binary
- `import vcgencmd` checks that a mailbox device node exists instead of running
  the binary; it still raises `ImportError` off a Raspberry Pi
- Errors are typed and derive from `VcgencmdError`; unexpected output raises
  `ParseError` instead of a bare `Exception`
- Parsing moved into pure functions in `vcgencmd.parsers`
- Requires Python 3.9+

### Added

- `gencmd(command)` for raw gencmd commands
- `vcgencmd.transport` (`Mailbox`, `set_transport()`) and `vcgencmd.errors`
  (`DeviceUnavailableError`, `MailboxError`, `GencmdError`, `ParseError`)
- Source lists as constants (`FREQUENCY_SOURCES`, `PMIC_SOURCES`, …)
- Unit tests with captured Raspberry Pi 5 output, device tests, CI workflow

### Removed

- Dependency on the `vcgencmd` binary

## [0.3.0] - 2026-07-14

### Added

- PMIC temperature via `vcgencmd measure_temp pmic` (`measure_temp_pmic()`,
  `temperature_sources()`); included in `--temp` / `temperature()` on Pi 5
- `hevc` clock and `vp8` codec sources
- Opt-in groups: `version`, `bootloader`, `rsts`, `config_int`, `config_str`
  (`--version`, `--bootloader`, `--rsts`, `--config-int`, `--config-str`)
- `get_rsts()` parses PM_RSTS into named boolean flags (like `get_throttled()`);
  both status groups also include a `raw` integer register value
- Snapshot helpers: `firmware_version()`, `bootloader_version()`, `rsts()`,
  `config_int()`, `config_str()`

### Changed

- Default CLI output excludes opt-in groups; `-a` / `read_all()` include every group
- `--temp` accepts optional `soc` / `pmic` sources
- `get_throttled()` and `get_rsts()` expose parsed flags plus `raw` register value

## [0.2.0] - 2026-07-14

### Added

- Modern argparse CLI via `python3 -m vcgencmd` with per-group selectors
  (`--clocks`, `--voltages`, `--temp`, `--codecs`, `--memory`, `--throttled`,
  `--pmic`)
- Output formats: grouped text, CSV, and JSON
- Interval polling (`-i MS`) with CSV streaming and JSONL output
- Raspberry Pi 5 PMIC ADC support (`pmic_read_all()`, `measure_pmic_adc()`,
  `pmic_sources()`)
- Throttle and under-voltage status (`get_throttled()`, `get_throttled_sources()`)
- Structured collection and formatting layers (`readings.py`, `formatters.py`,
  `cli.py`)
- Public snapshot API: `read_all()` and `read()` for nested dict output
- Per-group flat dict helpers: `clocks()`, `voltages()`, `temperature()` /
  `temp()`, `codecs()`, `memory()`, `throttled()`, `pmic()`
- `pyproject.toml` packaging (PEP 517/518, PEP 621) replacing `setup.py`

### Changed

- Default CLI behaviour shows all telemetry groups (equivalent to `-a`)
- README rewritten with CLI, programmatic, and pymqttutil integration docs
- PMIC output is a flat channel map under `pmic` (no `voltage` / `current`
  sub-objects); CSV and CLI text use a single `pmic` group/section

## [0.1.0] - 2016-01-30

### Added

- Initial Python binding to the `vcgencmd` binary
- Support for clock frequencies, voltages, temperature, codec status, and
  memory split queries
- Basic `python3 -m vcgencmd` dump-all CLI
- `setup.py` packaging
