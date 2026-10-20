# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

import pytest

import vcgencmd
from vcgencmd.errors import GencmdError, InvalidArgumentError, PmicUnavailableError

# Public names of 0.3.0; 0.4.0 must keep all of them
API_0_3_0 = [
    "InvalidArgumentError",
    "PmicUnavailableError",
    "Selection",
    "get_throttled_sources",
    "frequency_sources",
    "measure_clock",
    "voltage_sources",
    "measure_volts",
    "measure_temp",
    "temperature_sources",
    "measure_temp_pmic",
    "read_temperature",
    "get_throttled_raw",
    "get_throttled",
    "codec_sources",
    "codec_enabled",
    "memory_sources",
    "get_mem",
    "pmic_sources",
    "pmic_read_all",
    "measure_pmic_adc",
    "version_sources",
    "get_version",
    "bootloader_version_sources",
    "get_bootloader_version",
    "get_rsts_sources",
    "get_rsts_raw",
    "get_rsts",
    "get_config_int",
    "get_config_str",
    "config_int_sources",
    "config_str_sources",
    "bootloader_version",
    "clocks",
    "codecs",
    "config_int",
    "config_str",
    "firmware_version",
    "memory",
    "pmic",
    "read",
    "read_all",
    "rsts",
    "temp",
    "temperature",
    "throttled",
    "voltages",
]

# Columns the tsconfig telemetry collectors publish (app/telemetry/collectors/vcgencmd.py)
PMIC_RAILS = (
    "3V7_WL_SW",
    "3V3_SYS",
    "1V8_SYS",
    "DDR_VDD2",
    "DDR_VDDQ",
    "1V1_SYS",
    "0V8_SW",
    "VDD_CORE",
    "3V3_DAC",
    "3V3_ADC",
    "0V8_AON",
    "HDMI",
)
PMIC_COLUMNS = {*(f"{r}_A" for r in PMIC_RAILS), *(f"{r}_V" for r in PMIC_RAILS), "EXT5V_V", "BATT_V", "BAT_RTC_V"}
THROTTLED_COLUMNS = {
    "under_voltage",
    "freq_capped",
    "throttled",
    "temp_limit",
    "under_voltage_occurred",
    "freq_capped_occurred",
    "throttling_occurred",
    "temp_limit_occurred",
    "raw",
}
CLOCK_COLUMNS = {"arm", "core", "h264", "hevc", "isp", "v3d", "uart", "pwm", "emmc", "pixel", "vec", "hdmi", "dpi"}
VOLTAGE_COLUMNS = {"core", "sdram_c", "sdram_i", "sdram_p"}


@pytest.mark.parametrize("name", API_0_3_0)
def test_0_3_0_api_is_kept(name):
    assert hasattr(vcgencmd, name)


def test_low_level_readings(fake):
    assert vcgencmd.measure_clock("arm") == 2400027136
    assert vcgencmd.measure_clock("ARM") == 2400027136
    assert vcgencmd.measure_volts("core") == 0.8605
    assert vcgencmd.measure_temp() == 47.7
    assert vcgencmd.measure_temp_pmic() == 45.8
    assert vcgencmd.read_temperature("soc") == 47.7
    assert vcgencmd.read_temperature("pmic") == 45.8
    assert vcgencmd.codec_enabled("h264") is False
    assert vcgencmd.get_mem("gpu") == 4 * 1024**2
    assert vcgencmd.get_throttled_raw() == 0
    assert vcgencmd.get_rsts_raw() == 0x1000
    assert vcgencmd.get_rsts("power_on_reset") is True
    assert vcgencmd.get_throttled("under_voltage") is False
    assert vcgencmd.measure_pmic_adc("BAT_RTC_V") == vcgencmd.measure_pmic_adc("batt_v")
    assert vcgencmd.get_config_int("arm_freq") == 2400
    assert vcgencmd.get_config_str("overlay_prefix") == "overlays/"
    assert vcgencmd.get_version()["version"] == "2226a853 (release) (embedded)"
    assert vcgencmd.get_bootloader_version()["capabilities"] == 0x7F


def test_commands_sent_to_the_firmware(fake):
    vcgencmd.measure_clock("ARM")
    vcgencmd.read_temperature("pmic")
    vcgencmd.get_config_int("arm_freq")
    assert fake.commands == ["measure_clock arm", "measure_temp pmic", "get_config arm_freq"]


def test_raw_gencmd(fake):
    assert vcgencmd.gencmd("get_throttled").strip() == "throttled=0x0"


@pytest.mark.parametrize(
    "call",
    [
        lambda: vcgencmd.measure_clock("bogus"),
        lambda: vcgencmd.measure_volts("bogus"),
        lambda: vcgencmd.read_temperature("bogus"),
        lambda: vcgencmd.codec_enabled("bogus"),
        lambda: vcgencmd.get_mem("bogus"),
        lambda: vcgencmd.measure_pmic_adc("bogus"),
        lambda: vcgencmd.get_throttled("bogus"),
        lambda: vcgencmd.get_rsts("bogus"),
        lambda: vcgencmd.get_config_int("bogus"),
    ],
)
def test_invalid_arguments(fake, call):
    with pytest.raises(InvalidArgumentError):
        call()
    # Source names are checked before anything is sent, except for config keys
    assert fake.commands in ([], ["get_throttled"], ["get_rsts"], ["get_config bogus", "get_config int"])


def test_config_key_at_its_default(fake):
    # over_voltage=0 is not in the "get_config int" listing, but the firmware knows it
    assert "over_voltage" not in vcgencmd.get_config_int()
    assert vcgencmd.get_config_int("over_voltage") == 0
    assert fake.commands[-1] == "get_config over_voltage"


def test_config_str_key(fake):
    assert vcgencmd.get_config_str("overlay_prefix") == "overlays/"
    assert fake.commands == ["get_config overlay_prefix"]


def test_indexed_config_key_falls_back_to_the_listing(fake):
    # The firmware does not resolve hdmi_cvt:0 on its own, only lists it
    assert vcgencmd.get_config_str("hdmi_cvt:0") == ""
    assert fake.commands == ["get_config hdmi_cvt:0", "get_config str"]


def test_config_int_rejects_a_string_key(fake):
    with pytest.raises(InvalidArgumentError, match="not an integer"):
        vcgencmd.get_config_int("overlay_prefix")


@pytest.mark.parametrize("key", ["", "arm freq", "int", "str"])
def test_invalid_config_key_is_not_sent(fake, key):
    with pytest.raises(InvalidArgumentError):
        vcgencmd.get_config_int(key)
    assert fake.commands == []


def test_config_group_with_keys(fake):
    assert vcgencmd.config_int(["arm_freq", "over_voltage"]) == {"arm_freq": 2400, "over_voltage": 0}
    assert fake.commands == ["get_config arm_freq", "get_config over_voltage"]


def test_config_group_without_keys_reads_the_listing_once(fake):
    assert vcgencmd.config_int()["arm_freq"] == 2400
    assert fake.commands == ["get_config int"]


def test_unknown_command(fake):
    with pytest.raises(GencmdError) as exc:
        vcgencmd.gencmd("bogus")
    assert exc.value.message == "Command not registered"


def test_sources_are_copies():
    vcgencmd.frequency_sources().append("bogus")
    assert "bogus" not in vcgencmd.frequency_sources()


def test_group_helpers_have_the_tsconfig_columns(fake):
    assert set(vcgencmd.pmic()) == PMIC_COLUMNS
    assert set(vcgencmd.throttled()) == THROTTLED_COLUMNS
    assert set(vcgencmd.clocks()) == CLOCK_COLUMNS
    assert set(vcgencmd.voltages()) == VOLTAGE_COLUMNS
    assert vcgencmd.temperature() == {"soc": 47.7, "pmic": 45.8}


def test_group_helpers_with_sources(fake):
    assert vcgencmd.clocks(["arm"]) == {"arm": 2400027136}
    assert vcgencmd.pmic(["BATT_V"]) == {"BATT_V": vcgencmd.pmic_read_all()["BATT_V"]}
    assert vcgencmd.rsts(["power_on_reset"]) == {"power_on_reset": True, "raw": 0x1000}
    assert vcgencmd.config_int(["arm_freq"]) == {"arm_freq": 2400}


def test_read_all(fake):
    payload = vcgencmd.read_all()
    assert list(payload) == [
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
    assert payload["memory"] == {"arm": 1020 * 1024**2, "gpu": 4 * 1024**2}


def test_read_selection(fake):
    assert vcgencmd.read(clocks=["arm"], temp=None) == {
        "clocks": {"arm": 2400027136},
        "temperature": {"soc": 47.7, "pmic": 45.8},
    }
    with pytest.raises(ValueError):
        vcgencmd.read()


def test_board_without_pmic(fake):
    # Raspberry Pi 4 and older: the firmware has no PMIC commands
    fake.fail("pmic_read_adc")
    fake.fail("measure_temp pmic")
    assert vcgencmd.temperature() == {"soc": 47.7}
    assert "pmic" not in vcgencmd.read_all()
    with pytest.raises(PmicUnavailableError):
        vcgencmd.pmic()
    with pytest.raises(GencmdError):
        vcgencmd.pmic_read_all()


def test_pmic_channel_missing_from_output(fake):
    fake.set("pmic_read_adc", "")
    with pytest.raises(PmicUnavailableError):
        vcgencmd.measure_pmic_adc("BATT_V")
