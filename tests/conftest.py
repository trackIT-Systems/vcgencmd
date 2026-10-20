# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from unittest import mock

import pytest

# The package refuses to import without a mailbox device node; pretend there is one.
# Tests that need a real device are marked `device` and check transport.available() themselves.
with mock.patch("os.path.exists", return_value=True):
    import vcgencmd  # noqa: F401

from vcgencmd import transport
from vcgencmd.errors import GencmdError

FIXTURES = Path(__file__).parent / "fixtures"


class FakeTransport:
    """Answers gencmd commands with captured firmware output from tests/fixtures/<board>/."""

    def __init__(self, board: str = "pi5"):
        self.directory = FIXTURES / board
        self.commands = []
        self.overrides = {}

    def set(self, command: str, output: str) -> None:
        self.overrides[command] = output

    def fail(self, command: str, status: int = -1, message: str = "Command not registered") -> None:
        self.overrides[command] = GencmdError(command, status, message, 'error=1 error_msg="{0}"'.format(message))

    def gencmd(self, command: str) -> str:
        self.commands.append(command)
        if command in self.overrides:
            result = self.overrides[command]
            if isinstance(result, Exception):
                raise result
            return result
        path = self.directory / (command.replace(" ", "_") + ".txt")
        if not path.exists():
            raise GencmdError(command, -1, "Command not registered", 'error=1 error_msg="Command not registered"')
        return path.read_text()


def fixture_text(name: str, board: str = "pi5") -> str:
    return (FIXTURES / board / name).read_text()


@pytest.fixture
def fake():
    transport_ = FakeTransport()
    previous = transport.set_transport(transport_)
    yield transport_
    transport.set_transport(previous)
