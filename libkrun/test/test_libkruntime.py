# Copyright (c) 2017 King's College London
# created by the Software Development Team <http://soft-dev.org/>
#
# The Universal Permissive License (UPL), Version 1.0
#
# Subject to the condition set forth below, permission is hereby granted to any
# person obtaining a copy of this software, associated documentation and/or
# data (collectively the "Software"), free of charge and under any and all
# copyright rights in the Software, and any and all patent rights owned or
# freely licensable by each licensor hereunder covering either (i) the
# unmodified Software as contributed to or provided by such licensor, or (ii)
# the Larger Works (as defined below), to deal in both
#
# (a) the Software, and
# (b) any piece of software and/or hardware listed in the lrgrwrks.txt file if
# one is included with the Software (each a "Larger Work" to which the Software
# is contributed by such licensors),
#
# without restriction, including without limitation the rights to copy, create
# derivative works of, display, perform, and distribute the Software and make,
# use, sell, offer for sale, import, export, have made, and have sold the
# Software and the Larger Work(s), and to sublicense the foregoing rights on
# either these or other terms.
#
# This license is subject to the following condition: The above copyright
# notice and either this complete permission notice or at a minimum a reference
# to the UPL must be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from subprocess import Popen, PIPE
import os
import sys
import pytest

# Some core cycle tests collect two readings as fast as possible, so the delta
# should be pretty small (but it ultimately depends upon the CPU).
NOT_MANY_CYCLES = 500000

DIR = os.path.abspath(os.path.dirname(__file__))
TEST_PROG_PATH = os.path.join(DIR, "test_prog")

sys.path.append(os.path.join(DIR, "..", ".."))
from krun.platform import detect_platform
PLATFORM = detect_platform(None, None)

CORECYCLES_SUPPORT = sys.platform.startswith("linux") and \
    not PLATFORM.is_virtual()

APERF_MPERF_SUPPORT = sys.platform.startswith("linux") and \
    not PLATFORM.is_virtual()

def invoke_c_prog(mode):
    assert os.path.exists(TEST_PROG_PATH)

    p = Popen(TEST_PROG_PATH + " " + mode,
              stderr=PIPE, stdout=PIPE, shell=True)
    out, err = p.communicate()
    return p.returncode, out.strip(), err.strip()


def parse_keyvals(out, doubles=False):
    dct = {}
    for line in out.splitlines():
        key, val = line.split("=")
        if doubles:
            dct[key.strip()] = float(val)
        else:
            dct[key.strip()] = int(val)
    return dct


class TestLibKrunTime(object):
    @pytest.mark.skipif(not CORECYCLES_SUPPORT,
                        reason="no performance counters")
    def test_cycles_u64(self):
        rv, out, _ = invoke_c_prog("cycles_u64")
        assert rv == 0
        dct = parse_keyvals(out)

        assert 0 <= dct["cycles_u64_delta"] <= NOT_MANY_CYCLES

    @pytest.mark.skipif(not CORECYCLES_SUPPORT,
                        reason="no performance counters")
    def test_cycles_double(self):
        rv, out, _ = invoke_c_prog("cycles_double")
        assert rv == 0
        dct = parse_keyvals(out, True)
        assert 0 <= dct["cycles_double_delta"] <= NOT_MANY_CYCLES

    def test_cycles_double_prec_ok(self):
        rv, out, _ = invoke_c_prog("cycles_double_prec_ok")
        assert rv == 0
        assert out == "OK"

    def test_cycles_double_prec_bad(self):
        rv, _, err = invoke_c_prog("cycles_double_prec_bad")
        assert rv == 1
        assert "Loss of precision detected!" in err

    @pytest.mark.skipif(not CORECYCLES_SUPPORT, reason="would divide by zero")
    def test_cycles_u64_double_ratio(self):
        rv, out, _ = invoke_c_prog("cycles_u64_double_ratio")
        assert rv == 0
        dct = parse_keyvals(out, True)
        # within 2x of each other
        assert 0.5 <= dct["cycles_u64_double_ratio"] <= 2

    def test_clock_gettime_monotonic(self):
        rv, out, _ = invoke_c_prog("clock_gettime_monotonic")
        assert rv == 0
        dct = parse_keyvals(out, True)
        # Depends on speed of CPU, but should be very close to 1
        assert 0.95 <= dct["monotonic_delta"] <= 1.05

    @pytest.mark.skipif(not CORECYCLES_SUPPORT, reason="would not make sense")
    def test_msr_time(self):
        rv, out, _ = invoke_c_prog("msr_time")
        assert rv == 0
        dct = parse_keyvals(out, True)

        # On Linux I expect reading core cycles (via the MSR device nodes) to
        # be slower than reading the monotonic clock via a system call. This
        # is why the readings are ordered as they are in the iterations runner.
        assert dct["monotonic_delta_msrs"] > dct["monotonic_delta_nothing"]

    @pytest.mark.skipif(not APERF_MPERF_SUPPORT,
                        reason="no performance counters")
    def test_aperf_mperf(self):
        rv, out, _ = invoke_c_prog("aperf_mperf")
        assert rv == 0
        dct = parse_keyvals(out, doubles=False)

        assert dct["aperf"] > 0
        assert dct["mperf"] > 0

        # aperf is ticking for a subset of the time mperf is
        assert dct["aperf"] <= dct["mperf"]

    @pytest.mark.skipif(not APERF_MPERF_SUPPORT,
                        reason="no performance counters")
    def test_aperf(self):
        rv, out, _ = invoke_c_prog("aperf")
        assert rv == 0
        dct = parse_keyvals(out)
        assert dct["aperf_start"] < dct["aperf_stop"]

    @pytest.mark.skipif(not APERF_MPERF_SUPPORT,
                        reason="no performance counters")
    def test_mperf(self):
        rv, out, _ = invoke_c_prog("mperf")
        assert rv == 0
        dct = parse_keyvals(out)
        assert dct["mperf_start"] < dct["mperf_stop"]

    def test_core_bounds_check(self):
        rv, _, err = invoke_c_prog("core_bounds_check")
        assert rv != 0
        assert "core out of range" in err

    def test_mdata_index_bounds_check(self):
        rv, _, err = invoke_c_prog("mdata_index_bounds_check")
        assert rv != 0
        assert "mdata index out of range" in err

    def test_read_everything_all_cores(self):
        rv, out, err = invoke_c_prog("read_everything_all_cores")
        assert rv == 0
        dct = parse_keyvals(out, doubles=True)

        # Two wallclock measurements
        expect = 2

        # Two more for measurements for each core
        if CORECYCLES_SUPPORT:
            expect += PLATFORM.num_cpus * 2

        # Two more for measurements for each aperf and mperf on each core
        if APERF_MPERF_SUPPORT:
            expect += 2 * PLATFORM.num_cpus * 2

        assert len(dct) == expect
