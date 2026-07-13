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

from . import vcgencmd

import argparse
import sys


def __do(label, sources, function):
    print('{0}:'.format(label))
    max_len = 1 + max(len(src) for src in sources)  # Find the longest source name
    for src in sources:
        if src == '':
            val = function()
        else:
            val = function(src)
        print('  {0}{1}: {2}'.format(
            src, ' ' * (max_len - len(src)), str(val)))


def __do_pmic(label, suffix, readings):
    sources = [src for src in vcgencmd.pmic_sources() if src.endswith(suffix)]
    print('{0}:'.format(label))
    max_len = 1 + max(len(src) for src in sources)
    for src in sources:
        val = readings[src]
        print('  {0}{1}: {2}'.format(
            src, ' ' * (max_len - len(src)), str(val)))


def main(args):
    kTxtLen = 10

    __do('Clock Frequencies (Hz)',
         vcgencmd.frequency_sources(),
         vcgencmd.measure_clock)
    __do('Voltages (V)',
         vcgencmd.voltage_sources(),
         vcgencmd.measure_volts)
    __do('Temperatures (C)',
         [''],
         vcgencmd.measure_temp)
    __do('Codecs Enabled',
         vcgencmd.codec_sources(),
         vcgencmd.codec_enabled)
    __do('Memory Allocation (bytes)',
         vcgencmd.memory_sources(),
         vcgencmd.get_mem)
    __do('Throttled Status',
         vcgencmd.get_throttled_sources(),
         vcgencmd.get_throttled)

    try:
        pmic_readings = vcgencmd.pmic_read_all()
        __do_pmic('PMIC Voltages (V)', '_V', pmic_readings)
        __do_pmic('PMIC Currents (A)', '_A', pmic_readings)
    except Exception:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    sys.exit(main(args))
