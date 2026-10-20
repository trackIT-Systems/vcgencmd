# Copyright 2014 Nic McDonald. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import transport
from .errors import (
    DeviceUnavailableError,
    GencmdError,
    MailboxError,
    ParseError,
    PmicUnavailableError,
    VcgencmdError,
)
from .readings import Selection
from .snapshot import (
    bootloader_version,
    clocks,
    codecs,
    config_int,
    config_str,
    firmware_version,
    memory,
    pmic,
    read,
    read_all,
    rsts,
    temp,
    temperature,
    throttled,
    voltages,
)
from .vcgencmd import *  # noqa: F403

__version__ = '0.4.0'

# Off a Raspberry Pi the import fails, so callers can treat ImportError as "not available".
# Only checks that a device node exists; nothing is sent to the firmware.
if not transport.available():
    raise ImportError('no VideoCore mailbox device ({0})'.format(', '.join(transport.DEVICES)))
