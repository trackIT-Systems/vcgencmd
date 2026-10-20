# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

"""Against the real firmware; run on a Raspberry Pi with ``pytest -m device``."""

import shutil
import subprocess

import pytest

import vcgencmd
from vcgencmd import transport
from vcgencmd.errors import GencmdError

pytestmark = [
    pytest.mark.device,
    pytest.mark.skipif(not transport.available(), reason="no VideoCore mailbox device"),
]


@pytest.fixture(autouse=True)
def mailbox():
    # A fresh Mailbox per test, not a fake left behind by another test
    previous = transport.set_transport(transport.Mailbox())
    yield transport.get_transport()
    transport.get_transport().close()
    transport.set_transport(previous)


@pytest.mark.skipif(shutil.which("vcgencmd") is None, reason="vcgencmd binary not installed")
@pytest.mark.parametrize(
    "command",
    [
        "version",
        "bootloader_version",
        "get_config int",
        "get_config str",
        "get_throttled",
        "get_rsts",
        "get_mem arm",
        "codec_enabled h264",
    ],
)
def test_same_output_as_the_binary(command):
    binary = subprocess.run(["vcgencmd", *command.split()], capture_output=True, text=True, check=True).stdout
    assert vcgencmd.gencmd(command).strip() == binary.strip()


def test_unknown_command():
    with pytest.raises(GencmdError) as exc:
        vcgencmd.gencmd("bogus_command")
    assert exc.value.message == "Command not registered"


def test_plausible_readings():
    assert 100e6 < vcgencmd.measure_clock("arm") < 4e9
    assert 0.5 < vcgencmd.measure_volts("core") < 1.5
    assert 0 < vcgencmd.measure_temp() < 100
    assert set(vcgencmd.throttled()) == set(vcgencmd.get_throttled_sources())


def test_pmic_on_pi5():
    try:
        readings = vcgencmd.pmic_read_all()
    except GencmdError:
        pytest.skip("board has no PMIC")
    assert set(vcgencmd.pmic_sources()) <= set(readings)
    assert 4.5 < readings["EXT5V_V"] < 5.5
    assert 0 < vcgencmd.measure_temp_pmic() < 100


def test_read_all():
    payload = vcgencmd.read_all()
    assert {"clocks", "voltages", "temperature", "throttled", "version", "config_int"} <= set(payload)


def test_device_in_use(mailbox):
    vcgencmd.gencmd("get_throttled")
    assert mailbox.path in transport.DEVICES
