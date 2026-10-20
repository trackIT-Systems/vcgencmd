# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

"""Send gencmd commands to the VideoCore firmware through the mailbox ioctl.

This is what the ``vcgencmd`` binary does (raspberrypi/utils, vcgencmd.c): one
mailbox property message with the GET_GENCMD_RESULT tag, sent to
``/dev/vcio_gencmd`` (gencmd only, group ``video``) or ``/dev/vcio`` (root).
"""

from __future__ import annotations

import fcntl
import os
import re
import struct
import threading
from typing import Dict, Optional, Protocol, Sequence, Tuple

from .errors import DeviceUnavailableError, GencmdError, MailboxError

# Restricted device first, full mailbox as fallback, like the vcgencmd binary
DEVICES = ("/dev/vcio_gencmd", "/dev/vcio")

GET_GENCMD_RESULT = 0x00030080
MAX_STRING = 4096
RESPONSE_SUCCESS = 0x80000000

# Words before the value buffer: size, request code, tag, buffer length, request length
_HEADER = struct.Struct("<5I")
# The value buffer starts with the gencmd status, followed by the command / response string
_STATUS_OFFSET = _HEADER.size
_STRING_OFFSET = _STATUS_OFFSET + 4
_MESSAGE_SIZE = _HEADER.size + MAX_STRING + 4  # + end tag

_ERROR_PATTERN = re.compile(r'error=(-?\d+)\s+error_msg="([^"]*)"')


def _iowr(type_: int, nr: int, size: int) -> int:
    # Linux _IOC(_IOC_READ | _IOC_WRITE, type, nr, size)
    return (3 << 30) | (size << 16) | (type_ << 8) | nr


# _IOWR(100, 0, char *): the argument size is the size of a pointer
IOCTL_MBOX_PROPERTY = _iowr(100, 0, struct.calcsize("P"))


def pack_gencmd(command: str) -> bytearray:
    """Build the mailbox property message for one gencmd command."""
    encoded = command.encode("ascii") + b"\0"
    # The status word takes the first 4 bytes of the value buffer
    if len(encoded) > MAX_STRING - 4:
        raise ValueError("command longer than {0} bytes".format(MAX_STRING - 5))

    buf = bytearray(_MESSAGE_SIZE)
    _HEADER.pack_into(buf, 0, _MESSAGE_SIZE, 0, GET_GENCMD_RESULT, MAX_STRING, 0)
    buf[_STRING_OFFSET:_STRING_OFFSET + len(encoded)] = encoded
    # The end tag (0) is already in place
    return buf


def unpack_gencmd(buf: bytes) -> Tuple[int, int, str]:
    """Return (response code, gencmd status, response text) from a sent message."""
    _, code, _, _, _ = _HEADER.unpack_from(buf, 0)
    (status,) = struct.unpack_from("<i", buf, _STATUS_OFFSET)
    raw = bytes(buf[_STRING_OFFSET:_HEADER.size + MAX_STRING])
    text = raw.split(b"\0", 1)[0].decode("utf-8", errors="replace")
    return code, status, text


def parse_error(text: str) -> Optional[str]:
    """Return error_msg from a firmware error response, if there is one."""
    match = _ERROR_PATTERN.search(text)
    return match.group(2) if match else None


class Transport(Protocol):
    def gencmd(self, command: str) -> str: ...


class Mailbox:
    """A VideoCore mailbox device, opened on first use and shared by threads."""

    def __init__(self, devices: Sequence[str] = DEVICES):
        self.devices = tuple(devices)
        self.path: Optional[str] = None
        self._fd: Optional[int] = None
        self._lock = threading.Lock()

    def __enter__(self) -> "Mailbox":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _open(self) -> int:
        errors: Dict[str, OSError] = {}
        for path in self.devices:
            try:
                fd = os.open(path, os.O_RDONLY)
            except OSError as err:
                errors[path] = err
                continue
            self.path = path
            return fd
        raise DeviceUnavailableError(errors)

    def close(self) -> None:
        with self._lock:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
                self.path = None

    def gencmd(self, command: str) -> str:
        """Run one gencmd command and return its response text."""
        buf = pack_gencmd(command)
        with self._lock:
            if self._fd is None:
                self._fd = self._open()
            try:
                fcntl.ioctl(self._fd, IOCTL_MBOX_PROPERTY, buf, True)
            except OSError as err:
                raise MailboxError("mailbox ioctl on {0} failed: {1}".format(self.path, err)) from err

        code, status, text = unpack_gencmd(buf)
        if code != RESPONSE_SUCCESS:
            raise MailboxError("firmware rejected '{0}' with response code 0x{1:08x}".format(command, code))
        if status != 0:
            raise GencmdError(command, status, parse_error(text), text)
        return text


def available(devices: Sequence[str] = DEVICES) -> bool:
    """Whether a mailbox device node exists; does not talk to the firmware."""
    return any(os.path.exists(path) for path in devices)


_default: Optional[Transport] = None
_default_lock = threading.Lock()


def get_transport() -> Transport:
    """Return the process-wide transport, creating a :class:`Mailbox` on first use."""
    global _default
    with _default_lock:
        if _default is None:
            _default = Mailbox()
        return _default


def set_transport(transport: Optional[Transport]) -> Optional[Transport]:
    """Replace the process-wide transport (e.g. with a fake in tests); returns the old one.

    ``None`` resets to a fresh :class:`Mailbox` on next use.
    """
    global _default
    with _default_lock:
        previous, _default = _default, transport
        return previous
