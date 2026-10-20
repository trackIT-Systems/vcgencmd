# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

import os
import struct

import pytest

from vcgencmd import transport
from vcgencmd.errors import DeviceUnavailableError, GencmdError, MailboxError
from vcgencmd.transport import (
    GET_GENCMD_RESULT,
    IOCTL_MBOX_PROPERTY,
    MAX_STRING,
    RESPONSE_SUCCESS,
    Mailbox,
    pack_gencmd,
    unpack_gencmd,
)


def respond(buf, text, status=0, code=RESPONSE_SUCCESS):
    """Fill a packed message the way the firmware does."""
    struct.pack_into("<I", buf, 4, code)
    struct.pack_into("<I", buf, 16, RESPONSE_SUCCESS | len(text) + 5)
    struct.pack_into("<i", buf, 20, status)
    encoded = text.encode() + b"\0"
    buf[24 : 24 + len(encoded)] = encoded


def test_ioctl_number_matches_iowr_for_the_pointer_size():
    assert transport._iowr(100, 0, 8) == 0xC0086400
    assert transport._iowr(100, 0, 4) == 0xC0046400
    assert IOCTL_MBOX_PROPERTY == transport._iowr(100, 0, struct.calcsize("P"))


def test_pack_layout():
    buf = pack_gencmd("measure_clock arm")
    words = struct.unpack_from("<5I", buf, 0)
    assert words == (len(buf), 0, GET_GENCMD_RESULT, MAX_STRING, 0)
    assert len(buf) == 20 + MAX_STRING + 4
    assert struct.unpack_from("<i", buf, 20)[0] == 0
    assert buf[24 : 24 + 18] == b"measure_clock arm\0"
    assert struct.unpack_from("<I", buf, len(buf) - 4)[0] == 0


def test_pack_rejects_overlong_command():
    pack_gencmd("x" * (MAX_STRING - 5))
    with pytest.raises(ValueError):
        pack_gencmd("x" * (MAX_STRING - 4))


def test_unpack_response():
    buf = pack_gencmd("measure_clock arm")
    respond(buf, "frequency(0)=2400027136")
    assert unpack_gencmd(buf) == (RESPONSE_SUCCESS, 0, "frequency(0)=2400027136")


def test_unpack_longer_command_than_response():
    buf = pack_gencmd("measure_clock arm")
    respond(buf, "x=1")
    # The response NUL ends the string even though the command was longer
    assert unpack_gencmd(buf)[2] == "x=1"


def test_parse_error():
    assert transport.parse_error('error=1 error_msg="Command not registered"') == "Command not registered"
    assert transport.parse_error("frequency(0)=0") is None


@pytest.fixture
def device(monkeypatch):
    """Fake os.open / os.close / fcntl.ioctl for the mailbox device paths."""

    class Device:
        def __init__(self):
            self.denied = set()
            self.opened = []
            self.closed = []
            self.responses = []
            self.ioctl_error = None

        def respond(self, text, status=0, code=RESPONSE_SUCCESS):
            self.responses.append((text, status, code))

    dev = Device()
    real_open, real_close = os.open, os.close

    def fake_open(path, flags, *args, **kwargs):
        if path not in transport.DEVICES:
            return real_open(path, flags, *args, **kwargs)
        if path in dev.denied:
            raise PermissionError(13, "Permission denied", path)
        dev.opened.append(path)
        return 1000 + transport.DEVICES.index(path)

    def fake_close(fd):
        if fd >= 1000:
            dev.closed.append(fd)
        else:
            real_close(fd)

    def fake_ioctl(fd, request, buf, mutate):
        assert request == IOCTL_MBOX_PROPERTY and mutate
        if dev.ioctl_error:
            raise dev.ioctl_error
        text, status, code = dev.responses.pop(0)
        respond(buf, text, status, code)
        return 0

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "close", fake_close)
    monkeypatch.setattr(transport.fcntl, "ioctl", fake_ioctl)
    return dev


def test_mailbox_prefers_the_restricted_device_and_opens_once(device):
    device.respond("throttled=0x0")
    device.respond("throttled=0x50000")
    mailbox = Mailbox()
    assert mailbox.gencmd("get_throttled") == "throttled=0x0"
    assert mailbox.gencmd("get_throttled") == "throttled=0x50000"
    assert device.opened == ["/dev/vcio_gencmd"]
    assert mailbox.path == "/dev/vcio_gencmd"


def test_mailbox_falls_back_to_vcio(device):
    device.denied.add("/dev/vcio_gencmd")
    device.respond("throttled=0x0")
    mailbox = Mailbox()
    mailbox.gencmd("get_throttled")
    assert mailbox.path == "/dev/vcio"


def test_mailbox_without_device(device):
    device.denied.update(transport.DEVICES)
    with pytest.raises(DeviceUnavailableError) as exc:
        Mailbox().gencmd("get_throttled")
    assert set(exc.value.errors) == set(transport.DEVICES)


def test_gencmd_error_status(device):
    device.respond('error=1 error_msg="Command not registered"', status=-1)
    with pytest.raises(GencmdError) as exc:
        Mailbox().gencmd("bogus")
    assert exc.value.command == "bogus"
    assert exc.value.status == -1
    assert exc.value.message == "Command not registered"


def test_rejected_response_code(device):
    device.respond("", code=0x80000001)
    with pytest.raises(MailboxError):
        Mailbox().gencmd("get_throttled")


def test_ioctl_failure(device):
    device.ioctl_error = PermissionError(1, "Operation not permitted")
    with pytest.raises(MailboxError):
        Mailbox().gencmd("get_throttled")


def test_close_and_context_manager(device):
    device.respond("throttled=0x0")
    device.respond("throttled=0x0")
    with Mailbox() as mailbox:
        mailbox.gencmd("get_throttled")
    assert device.closed == [1000]
    assert mailbox.path is None
    # Reopens on the next call
    mailbox.gencmd("get_throttled")
    assert device.opened == ["/dev/vcio_gencmd", "/dev/vcio_gencmd"]


def test_available(tmp_path):
    present = tmp_path / "vcio"
    present.touch()
    assert transport.available([str(tmp_path / "missing"), str(present)])
    assert not transport.available([str(tmp_path / "missing")])


def test_set_transport_replaces_the_default():
    class Echo:
        def gencmd(self, command):
            return command

    previous = transport.set_transport(Echo())
    try:
        assert transport.get_transport().gencmd("hi") == "hi"
    finally:
        transport.set_transport(previous)


def test_default_transport_is_a_mailbox():
    previous = transport.set_transport(None)
    try:
        assert isinstance(transport.get_transport(), Mailbox)
    finally:
        transport.set_transport(previous)
