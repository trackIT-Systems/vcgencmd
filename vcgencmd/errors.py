# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Dict, Optional


class VcgencmdError(Exception):
    """Base class of every error this package raises."""


class DeviceUnavailableError(VcgencmdError):
    """No VideoCore mailbox device could be opened."""

    def __init__(self, errors: Dict[str, OSError]):
        self.errors = errors
        detail = "; ".join("{0}: {1}".format(path, err.strerror or err) for path, err in errors.items())
        super().__init__("no VideoCore mailbox device available ({0})".format(detail))


class MailboxError(VcgencmdError):
    """The mailbox ioctl failed or the firmware rejected the request."""


class GencmdError(VcgencmdError):
    """The firmware ran the command and returned a non-zero status."""

    def __init__(self, command: str, status: int, message: Optional[str], output: str):
        self.command = command
        self.status = status
        self.message = message
        self.output = output
        super().__init__("'{0}' failed with status {1}: {2}".format(command, status, message or output))


class ParseError(VcgencmdError, ValueError):
    """The firmware output did not have the expected format."""


class InvalidArgumentError(VcgencmdError, ValueError):
    """A source, flag or key name is not known."""


class PmicUnavailableError(VcgencmdError):
    """The board has no PMIC ADC (only Raspberry Pi 5 has one)."""
