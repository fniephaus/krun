from krun.util import (format_raw_exec_results,
                       log_and_mail, fatal,
                       check_and_parse_execution_results,
                       run_shell_cmd,
                       ExecutionFailed, get_session_info)
from krun.tests.mocks import MockMailer
from krun.tests import TEST_DIR
from krun.config import Config

import json
import logging
import pytest
import os


def test_fatal(capsys, caplog):
    caplog.setLevel(logging.ERROR)
    msg = "example text"
    with pytest.raises(SystemExit):
        fatal(msg)
    out, err = capsys.readouterr()
    assert out == ""
    assert msg in caplog.text()


def test_log_and_mail():
    log_fn = lambda s: None
    log_and_mail(MockMailer(), log_fn, "subject", "msg", exit=False,
                 bypass_limiter=False)
    with pytest.raises(SystemExit):
        log_and_mail(MockMailer(), log_fn, "", "", exit=True,
                     bypass_limiter=False)
    assert True


def test_format_raw():
    assert format_raw_exec_results([]) == []
    data = [1.33333344444, 4.555555666]
    expected = [1.333333, 4.555556]
    assert format_raw_exec_results(data) == expected


def test_run_shell_cmd():
    msg = "example text"
    out, err, rc = run_shell_cmd("echo " + msg)
    assert out == msg
    assert err == ""
    assert rc == 0


def test_run_shell_cmd_fatal():
    cmd = "nonsensecommand"
    out, err, rc = run_shell_cmd(cmd, False)
    assert rc != 0
    assert cmd in err
    assert out == ""


def test_check_and_parse_execution_results():
    stdout = "[0.000403]"
    stderr = "[iterations_runner.py] iteration 1/1"
    assert check_and_parse_execution_results(stdout, stderr, 0) == json.loads(stdout)
    # Non-zero return code.
    with pytest.raises(ExecutionFailed) as excinfo:
        check_and_parse_execution_results(stdout, stderr, 1)
    expected = """Benchmark returned non-zero or didn't emit JSON list. return code: 1
stdout:
--------------------------------------------------
[0.000403]
--------------------------------------------------

stderr:
--------------------------------------------------
[iterations_runner.py] iteration 1/1
--------------------------------------------------
"""
    assert excinfo.value.message == expected
    # Corrupt Json in STDOUT.
    with pytest.raises(ExecutionFailed) as excinfo:
        check_and_parse_execution_results("[0.000403[", stderr, 0)
    expected = """Benchmark returned non-zero or didn't emit JSON list. Exception string: Expecting , delimiter: line 1 column 10 (char 9)
return code: 0
stdout:
--------------------------------------------------
[0.000403[
--------------------------------------------------

stderr:
--------------------------------------------------
[iterations_runner.py] iteration 1/1
--------------------------------------------------
"""
    assert excinfo.value.message == expected


def test_get_session_info0001():
    path = os.path.join(TEST_DIR, "example.krun")
    config = Config(path)
    info = get_session_info(config)

    assert info["n_proc_execs"] == 8
    assert info["n_in_proc_iters"] == 40
    assert info["skipped_keys"] == set()

    expect_non_skipped_keys = set([
        "dummy:Java:default-java",
        "nbody:Java:default-java",
        "dummy:CPython:default-python",
        "nbody:CPython:default-python",
    ])
    assert info["non_skipped_keys"] == expect_non_skipped_keys


def test_get_session_info0002():
    path = os.path.join(TEST_DIR, "more_complicated.krun")
    config = Config(path)
    info = get_session_info(config)

    # 6 benchmarks, 9 VMs, skipped 3 exact keys, and all 6 CPython keys
    # Then two repetitions (process executions) of all of the above.
    expect_proc_execs = (6 * 9 - 3 - 6) * 2
    assert info["n_proc_execs"] == expect_proc_execs

    # 2000 in-process iterations
    assert info["n_in_proc_iters"] == expect_proc_execs * 2000

    expect_skip_keys = [
        "fasta:JRubyTruffle:default-ruby",
        "richards:HHVM:default-php",
        "spectralnorm:JRubyTruffle:default-ruby",
        "binarytrees:CPython:default-python",
        "richards:CPython:default-python",
        "spectralnorm:CPython:default-python",
        "nbody:CPython:default-python",
        "fasta:CPython:default-python",
        "fannkuch_redux:CPython:default-python",
    ]
    assert info["skipped_keys"] == set(expect_skip_keys)

    expect_non_skipped_keys = [
        'richards:C:default-c',
        'nbody:HHVM:default-php',
        'binarytrees:C:default-c',
        'binarytrees:PyPy:default-python',
        'spectralnorm:Hotspot:default-java',
        'fannkuch_redux:Graal:default-java',
        'nbody:JRubyTruffle:default-ruby',
        'fasta:Graal:default-java',
        'binarytrees:Graal:default-java',
        'fasta:C:default-c',
        'binarytrees:JRubyTruffle:default-ruby',
        'spectralnorm:HHVM:default-php',
        'nbody:PyPy:default-python',
        'fannkuch_redux:C:default-c',
        'fannkuch_redux:JRubyTruffle:default-ruby',
        'fannkuch_redux:Hotspot:default-java',
        'spectralnorm:PyPy:default-python',
        'fasta:PyPy:default-python',
        'binarytrees:Hotspot:default-java',
        'nbody:C:default-c',
        'richards:JRubyTruffle:default-ruby',
        'fasta:V8:default-javascript',
        'nbody:V8:default-javascript',
        'richards:V8:default-javascript',
        'nbody:LuaJIT:default-lua',
        'richards:Hotspot:default-java',
        'fasta:LuaJIT:default-lua',
        'binarytrees:LuaJIT:default-lua',
        'fannkuch_redux:V8:default-javascript',
        'fannkuch_redux:LuaJIT:default-lua',
        'richards:Graal:default-java',
        'binarytrees:V8:default-javascript',
        'spectralnorm:LuaJIT:default-lua',
        'spectralnorm:C:default-c',
        'fannkuch_redux:HHVM:default-php',
        'fannkuch_redux:PyPy:default-python',
        'binarytrees:HHVM:default-php',
        'fasta:HHVM:default-php',
        'spectralnorm:V8:default-javascript',
        'spectralnorm:Graal:default-java',
        'nbody:Graal:default-java',
        'richards:LuaJIT:default-lua',
        'nbody:Hotspot:default-java',
        'richards:PyPy:default-python',
        'fasta:Hotspot:default-java'
    ]
    assert info["non_skipped_keys"] == set(expect_non_skipped_keys)

    # There should be no overlap in the used and skipped keys
    assert info["skipped_keys"].intersection(info["non_skipped_keys"]) == set()
