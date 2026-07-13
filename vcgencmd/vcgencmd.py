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

'''vcgencmd: native binding for vcgencmd (Raspberry Pi).'''

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import re
import subprocess
import sys


class InvalidArgumentError(ValueError):
    pass


def __do_command(command):
    return subprocess.check_output(command).decode('utf-8')


def __lookup(command, src_list, src):
    src = src.lower()

    if src not in src_list:
        raise InvalidArgumentError('{0} must be one of {1}'.format(
            src, src_list))

    return __do_command(['vcgencmd', command, src])


__kGetThrottledSrcs = ['under_voltage', 'freq_capped', 'throttled', 'temp_limit',
                       'under_voltage_occurred', 'freq_capped_occurred', 'throttling_occurred', 'temp_limit_occurred']


def get_throttled_sources():
    return __kGetThrottledSrcs


__kFreqSrcs = ['arm', 'core', 'h264', 'isp', 'v3d', 'uart', 'pwm', 'emmc',
               'pixel', 'vec', 'hdmi', 'dpi']


def frequency_sources():
    return __kFreqSrcs


def measure_clock(src):
    output = __lookup('measure_clock', __kFreqSrcs, src)
    return int(output[output.find('=') + 1:].strip())


__kVoltSrcs = ['core', 'sdram_c', 'sdram_i', 'sdram_p']


def voltage_sources():
    return __kVoltSrcs


def measure_volts(src):
    output = __lookup('measure_volts', __kVoltSrcs, src)
    return float(output[output.find('=') + 1:].strip().rstrip('V'))


def measure_temp():
    output = __lookup('measure_temp', [''], '')
    return float(output[output.find('=') + 1:].strip().rstrip('\'C'))


def get_throttled(src=None):
    output = __do_command(['vcgencmd', 'get_throttled'])
    throttled_hex = output[output.find('=') + 1:].strip()
    throttled_value = int(throttled_hex, 16)

    flags = {
        "under_voltage": (0, "Under-voltage detected"),
        "freq_capped": (1, "Arm frequency capped"),
        "throttled": (2, "Currently throttled"),
        "temp_limit": (3, "Soft temperature limit active"),
        "under_voltage_occurred": (16, "Under-voltage has occurred"),
        "freq_capped_occurred": (17, "Arm frequency capped has occurred"),
        "throttling_occurred": (18, "Throttling has occurred"),
        "temp_limit_occurred": (19, "Soft temperature limit has occurred")
    }

    if src:
        bit, _ = flags[src]
        return bool(throttled_value & (1 << bit))
    else:
        return {key: bool(throttled_value & (1 << bit)) for key, (bit, _) in flags.items()}


__kCodecSrcs = ['h264', 'mpg2', 'wvc1', 'mpg4', 'mjpg', 'wmv9']


def codec_sources():
    return __kCodecSrcs


def codec_enabled(src):
    output = __lookup('codec_enabled', __kCodecSrcs, src)
    status = output[output.find('=') + 1:].strip()
    if status == 'disabled':
        return False
    if status == 'enabled':
        return True
    raise Exception('unknown output \'{0}\''.format(status))


__kMemSrcs = ['arm', 'gpu']


def memory_sources():
    return __kMemSrcs


def get_mem(src):
    output = __lookup('get_mem', __kMemSrcs, src)
    mem = output[output.find('=') + 1:].strip()
    num = int(mem[:-1])
    if mem[-1] == 'M':
        return num * 1024 * 1024
    if mem[-1] == 'G':
        return num * 1024 * 1024 * 1024
    raise Exception('unknown unit \'{0}\''.format(mem[-1]))


__kPmicAliases = {
    'BAT_RTC_V': 'BATT_V',
}

__kPmicSrcs = [
    '3V7_WL_SW_A', '3V3_SYS_A', '1V8_SYS_A', 'DDR_VDD2_A', 'DDR_VDDQ_A',
    '1V1_SYS_A', '0V8_SW_A', 'VDD_CORE_A', '3V3_DAC_A', '3V3_ADC_A',
    '0V8_AON_A', 'HDMI_A', '3V7_WL_SW_V', '3V3_SYS_V', '1V8_SYS_V',
    'DDR_VDD2_V', 'DDR_VDDQ_V', '1V1_SYS_V', '0V8_SW_V', 'VDD_CORE_V',
    '3V3_DAC_V', '3V3_ADC_V', '0V8_AON_V', 'HDMI_V', 'EXT5V_V',
    'BATT_V', 'BAT_RTC_V',
]

__kPmicPattern = re.compile(
    r'^\s*([A-Za-z0-9_]+)\s+(current|volt)\(\d+\)=([0-9.]+)([AV])',
    re.MULTILINE,
)


def pmic_sources():
    return list(__kPmicSrcs)


def __parse_pmic_output(output):
    readings = {}
    for match in __kPmicPattern.finditer(output):
        name, _, value, _ = match.groups()
        readings[name] = float(value)

    for alias, canonical in __kPmicAliases.items():
        if canonical in readings:
            readings[alias] = readings[canonical]

    return readings


def pmic_read_all():
    output = __do_command(['vcgencmd', 'pmic_read_adc'])
    return __parse_pmic_output(output)


def measure_pmic_adc(src):
    src = src.upper()

    if src not in __kPmicSrcs:
        raise InvalidArgumentError('{0} must be one of {1}'.format(
            src, __kPmicSrcs))

    canonical = __kPmicAliases.get(src, src)
    readings = pmic_read_all()

    if canonical not in readings:
        raise Exception('unknown output for \'{0}\''.format(src))

    return readings[canonical]
