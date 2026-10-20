# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

import json

from vcgencmd.cli import main


def test_json(fake, capsys):
    assert main(["-f", "json", "--clocks", "arm", "--temp"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "clocks": {"arm": 2400027136},
        "temperature": {"soc": 47.7, "pmic": 45.8},
    }


def test_csv(fake, capsys):
    assert main(["-f", "csv", "--voltages", "core"]) == 0
    header, row = capsys.readouterr().out.strip().splitlines()
    assert header == "timestamp,group,key,value,unit"
    assert row.split(",")[1:] == ["voltages", "core", "0.8605", "V"]


def test_text(fake, capsys):
    assert main(["--throttled", "under_voltage"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Throttled Status:",
        "  raw          : 0",
        "  under_voltage: False",
    ]


def test_default_groups(fake, capsys):
    assert main(["-f", "json"]) == 0
    assert list(json.loads(capsys.readouterr().out)) == [
        "clocks", "voltages", "temperature", "codecs", "memory", "throttled", "pmic",
    ]


def test_explicit_pmic_without_pmic(fake, capsys):
    fake.fail("pmic_read_adc")
    assert main(["--pmic"]) == 1
    assert "PMIC readings unavailable" in capsys.readouterr().err


def test_firmware_error(fake, capsys):
    fake.fail("get_config int")
    assert main(["--config-int"]) == 1
    assert "Command not registered" in capsys.readouterr().err
