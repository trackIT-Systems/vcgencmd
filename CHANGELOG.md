# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - Unreleased

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
