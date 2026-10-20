# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

import pytest
from conftest import fixture_text

from vcgencmd import parsers
from vcgencmd.errors import InvalidArgumentError, ParseError


def test_frequency():
    assert parsers.parse_frequency(fixture_text("measure_clock_arm.txt")) == 2400027136
    assert parsers.parse_frequency(fixture_text("measure_clock_v3d.txt")) == 0


def test_volts():
    assert parsers.parse_volts(fixture_text("measure_volts_core.txt")) == 0.8605
    assert parsers.parse_volts(fixture_text("measure_volts_sdram_p.txt")) == 1.1


def test_temp():
    assert parsers.parse_temp(fixture_text("measure_temp.txt")) == 47.7
    assert parsers.parse_temp(fixture_text("measure_temp_pmic.txt")) == 45.8
    assert parsers.parse_temp("temp=-5.0'C") == -5.0


def test_hex_register():
    assert parsers.parse_hex_register(fixture_text("get_throttled.txt")) == 0
    assert parsers.parse_hex_register("throttled=0x50005") == 0x50005
    # get_rsts prints hex without the 0x prefix
    assert parsers.parse_hex_register(fixture_text("get_rsts.txt")) == 0x1000


def test_mem():
    assert parsers.parse_mem(fixture_text("get_mem_arm.txt")) == 1020 * 1024**2
    assert parsers.parse_mem(fixture_text("get_mem_gpu.txt")) == 4 * 1024**2
    assert parsers.parse_mem("arm=7G") == 7 * 1024**3
    with pytest.raises(ParseError):
        parsers.parse_mem("arm=7T")


def test_codec():
    assert parsers.parse_codec(fixture_text("codec_enabled_h264.txt")) is False
    assert parsers.parse_codec("h264=enabled") is True
    with pytest.raises(ParseError):
        parsers.parse_codec("h264=unknown")


@pytest.mark.parametrize(
    "parse",
    [
        parsers.parse_frequency,
        parsers.parse_volts,
        parsers.parse_temp,
        parsers.parse_hex_register,
        parsers.parse_mem,
        parsers.parse_codec,
    ],
)
@pytest.mark.parametrize("output", ["", "no equals sign", "x=garbage", 'error=1 error_msg="Command not registered"'])
def test_garbage_raises_parse_error(parse, output):
    with pytest.raises(ParseError):
        parse(output)


def test_parse_error_is_a_value_error():
    with pytest.raises(ValueError):
        parsers.parse_frequency("x=garbage")


def test_pmic():
    readings = parsers.parse_pmic(fixture_text("pmic_read_adc.txt"))
    assert readings["3V7_WL_SW_A"] == 0.0585558
    assert readings["HDMI_A"] == 0.0233211
    assert readings["3V7_WL_SW_V"] == 3.729471
    assert readings["BAT_RTC_V"] == readings["BATT_V"]
    assert len([key for key in readings if key.endswith("_A")]) == 12
    assert len([key for key in readings if key.endswith("_V")]) == 15


def test_pmic_without_pmic():
    assert parsers.parse_pmic("") == {}


def test_version():
    assert parsers.parse_version(fixture_text("version.txt")) == {
        "date": "2025/12/08 19:29:54",
        "copyright": "Copyright (c) 2012 Broadcom",
        "version": "2226a853 (release) (embedded)",
    }


def test_bootloader_version():
    assert parsers.parse_bootloader_version(fixture_text("bootloader_version.txt")) == {
        "date": "2025/12/08 19:29:54",
        "version": "2226a853bb9f5fd80392e3a4a89e457aeca88008 (release)",
        "timestamp": 1765222194,
        "update-time": 1774614063,
        "capabilities": 0x7F,
    }


def test_bootloader_version_without_date_line():
    assert parsers.parse_bootloader_version("version abc (release)\ntimestamp 1") == {
        "version": "abc (release)",
        "timestamp": 1,
    }


def test_config_int():
    config = parsers.parse_config(fixture_text("get_config_int.txt"))
    assert config["arm_freq"] == 2400
    assert config["display_default_lcd"] == -1
    assert all(isinstance(value, int) for value in config.values())


def test_config_str():
    config = parsers.parse_config(fixture_text("get_config_str.txt"))
    assert config["overlay_prefix"] == "overlays/"
    assert config["hdmi_cvt:0"] == ""


def test_config_value():
    assert parsers.parse_config_value(fixture_text("get_config_arm_freq.txt"), "arm_freq") == "2400"
    assert parsers.parse_config_value(fixture_text("get_config_over_voltage.txt"), "over_voltage") == "0"
    assert parsers.parse_config_value(fixture_text("get_config_bogus_key.txt"), "bogus_key") is None
    assert parsers.parse_config_value(fixture_text("get_config_hdmi_cvt:0.txt"), "hdmi_cvt:0") is None
    with pytest.raises(ParseError):
        parsers.parse_config_value("total_mem=8192", "arm_freq")
    with pytest.raises(ParseError):
        parsers.parse_config_value("garbage", "arm_freq")


def test_coerce_scalar():
    assert parsers.coerce_scalar("0x1f") == 31
    assert parsers.coerce_scalar("0xzz") == "0xzz"
    assert parsers.coerce_scalar("-3") == -3
    assert parsers.coerce_scalar("overlays/") == "overlays/"


def test_decode_flags():
    value = (1 << 0) | (1 << 16)
    flags = parsers.decode_flags(value, parsers.THROTTLED_FLAGS)
    assert flags["under_voltage"] is True
    assert flags["under_voltage_occurred"] is True
    assert flags["throttled"] is False
    assert flags["raw"] == value
    assert parsers.decode_flags(value, parsers.THROTTLED_FLAGS, "under_voltage") is True
    assert parsers.decode_flags(value, parsers.THROTTLED_FLAGS, "freq_capped") is False
    assert parsers.decode_flags(value, parsers.THROTTLED_FLAGS, "raw") == value
    with pytest.raises(InvalidArgumentError):
        parsers.decode_flags(value, parsers.THROTTLED_FLAGS, "bogus")


def test_rsts_flags():
    flags = parsers.decode_flags(0x1000, parsers.RSTS_FLAGS)
    assert flags["power_on_reset"] is True
    assert not any(value for key, value in flags.items() if key not in ("power_on_reset", "raw"))
