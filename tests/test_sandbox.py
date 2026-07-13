"""Behavioural tests for sea.sandbox — the only place code is ever executed.

These tests exercise the real sandbox against real subprocesses. Nothing about
the unit under test is mocked: the timeout tests really spawn runaway
processes, and the orphan test really interrogates the OS process table.
"""

from __future__ import annotations

import glob
import os
import tempfile
import time
from pathlib import Path

import pytest

from sea.sandbox import ExecResult, run_pytest, run_script

PASSING_IMPL = "def add(a, b):\n    return a + b\n"
PASSING_TEST = "from tool import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"


def _is_alive(pid: int) -> bool:
    """True if a process with this pid currently exists."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_for_death(pid: int, timeout_s: float) -> bool:
    """Poll until the process disappears. Returns False if it outlives us."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not _is_alive(pid):
            return True
        time.sleep(0.05)
    return not _is_alive(pid)


def _sandbox_temp_dirs(scratch: Path) -> set[str]:
    """Sandbox scratch directories inside a scratch root WE own.

    This used to glob the *global* system temp directory. That made the two
    cleanup tests flaky for a reason that had nothing to do with the code under
    test: any other process creating a ``sea-sandbox-*`` directory in the shared
    namespace during the assertion window -- notably ``test_per_tool``'s
    ``ProcessPoolExecutor`` workers, which run the sandbox concurrently -- would
    show up as a "leak" here.

    Diagnosis (10/10 trials): ``run_script`` created and removed *exactly* its
    own directory every time; the directories flagged as leaked were ones this
    process never created. The production code was right and the test was wrong.

    Scoping to a private ``scratch`` root makes the assertion mean what it always
    claimed to mean -- *this call cleaned up after itself* -- and makes it immune
    to unrelated processes. It is a stronger test, not a weaker one: it now
    asserts the root is left completely empty, rather than merely no-worse-off.
    """
    return set(glob.glob(os.path.join(str(scratch), "sea-sandbox-*")))


# --------------------------------------------------------------------------
# run_pytest: status classification
# --------------------------------------------------------------------------


def test_run_pytest_passing_suite_reports_passed() -> None:
    result = run_pytest(PASSING_IMPL, PASSING_TEST)

    assert isinstance(result, ExecResult)
    assert result.status == "passed"
    assert result.returncode == 0
    assert result.duration_s > 0


def test_run_pytest_failing_assertion_reports_failed() -> None:
    wrong_impl = "def add(a, b):\n    return a * b\n"

    result = run_pytest(wrong_impl, PASSING_TEST)

    assert result.status == "failed"
    assert result.returncode != 0


def test_run_pytest_syntax_error_in_impl_reports_error() -> None:
    broken_impl = "def add(a, b)\n    return a + b\n"

    result = run_pytest(broken_impl, PASSING_TEST)

    assert result.status == "error"


def test_run_pytest_import_error_reports_error() -> None:
    """The suite imports a name the implementation does not define."""
    impl = "def subtract(a, b):\n    return a - b\n"

    result = run_pytest(impl, PASSING_TEST)

    assert result.status == "error"


def test_run_pytest_empty_suite_reports_error_not_passed() -> None:
    """A vacuous suite must never look like a passing suite.

    pytest exits 5 ("no tests collected") here. Reporting that as ``passed``
    would let a tool be admitted on the strength of an oracle that asserts
    nothing, which would silently corrupt every downstream number.
    """
    result = run_pytest(PASSING_IMPL, "# no tests here\n")

    assert result.status == "error"


def test_run_pytest_runaway_test_reports_timeout() -> None:
    hanging_test = "def test_hangs():\n    while True:\n        pass\n"

    result = run_pytest(PASSING_IMPL, hanging_test, timeout_s=2.0)

    assert result.status == "timeout"
    # The process never exited on its own; we killed its group.
    assert result.returncode is None


# --------------------------------------------------------------------------
# Isolation: process group, environment, working directory, cleanup
# --------------------------------------------------------------------------


def test_timeout_kills_whole_process_group_leaving_no_orphans(tmp_path: Path) -> None:
    """A grandchild of the sandboxed process must not survive the timeout.

    This is the failure the process-group kill exists to prevent: killing only
    the direct child leaves pytest's children (or anything a mutant spawned)
    running forever. The runaway here spawns a 120-second sleeper, records both
    pids somewhere we can still read after cleanup, and then hangs.
    """
    pid_file = tmp_path / "pids.txt"
    source = (
        "import os, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        f"with open({str(pid_file)!r}, 'w') as f:\n"
        "    f.write(f'{os.getpid()} {child.pid}')\n"
        "    f.flush()\n"
        "    os.fsync(f.fileno())\n"
        "while True:\n"
        "    time.sleep(0.05)\n"
    )

    result = run_script(source, timeout_s=3.0)

    assert result.status == "timeout"
    runner_pid, sleeper_pid = (int(p) for p in pid_file.read_text().split())
    assert _wait_for_death(runner_pid, 5.0), "sandboxed process survived the timeout"
    assert _wait_for_death(sleeper_pid, 5.0), "orphaned grandchild survived the timeout"


def test_child_cannot_see_parent_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generated code must not inherit credentials from the host environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-canary-must-not-leak")
    # Guard against the test passing vacuously: the key really is set here.
    assert os.environ["OPENAI_API_KEY"] == "sk-canary-must-not-leak"

    result = run_script(
        "import os\nprint(repr(os.environ.get('OPENAI_API_KEY')))\n"
    )

    assert result.status == "passed"
    assert "sk-canary-must-not-leak" not in result.stdout
    assert "None" in result.stdout


def test_pytest_suite_cannot_read_api_key_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same guarantee, asserted from inside a sandboxed pytest suite."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-canary-must-not-leak")

    suite = (
        "import os\n\n\n"
        "def test_no_api_key_visible():\n"
        "    assert os.environ.get('OPENAI_API_KEY') is None\n"
    )
    result = run_pytest(PASSING_IMPL, suite)

    assert result.status == "passed"


def test_relative_writes_land_in_scratch_dir_not_the_repo() -> None:
    """Stray writes go to the throwaway cwd, not the working tree."""
    result = run_script("open('stray.txt', 'w').write('should not escape')\n")

    assert result.status == "passed"
    assert not Path("stray.txt").exists()


def test_temp_dirs_are_cleaned_up_on_success(tmp_path: Path) -> None:
    run_pytest(PASSING_IMPL, PASSING_TEST, scratch_root=tmp_path)

    assert _sandbox_temp_dirs(tmp_path) == set(), "scratch dir survived a clean run"


def test_temp_dirs_are_cleaned_up_after_timeout(tmp_path: Path) -> None:
    """Cleanup must survive the hard path, where we SIGKILL a live process.

    The scratch root is private to this test, so the assertion is about *this
    call* and cannot be perturbed by another process running the sandbox
    concurrently. See ``_sandbox_temp_dirs``.
    """
    result = run_script("while True:\n    pass\n", timeout_s=2.0, scratch_root=tmp_path)

    assert result.status == "timeout"
    assert _sandbox_temp_dirs(tmp_path) == set(), (
        "scratch dir leaked after the process group was SIGKILLed"
    )


def test_temp_dirs_are_cleaned_up_across_many_timeouts(tmp_path: Path) -> None:
    """Cleanup must hold under repetition, not just once.

    A sweep takes the timeout path ~10^5 times; a leak rate of even 1% would
    bury the machine in scratch trees full of generated code.
    """
    for _ in range(5):
        run_script("while True:\n    pass\n", timeout_s=1.0, scratch_root=tmp_path)

    assert _sandbox_temp_dirs(tmp_path) == set(), "cleanup leaks under repetition"


# --------------------------------------------------------------------------
# run_script
# --------------------------------------------------------------------------


def test_run_script_success_captures_stdout() -> None:
    result = run_script("print('hello from the sandbox')\n")

    assert result.status == "passed"
    assert result.returncode == 0
    assert "hello from the sandbox" in result.stdout


def test_run_script_uncaught_exception_reports_failed() -> None:
    result = run_script("raise RuntimeError('boom')\n")

    assert result.status == "failed"
    assert "RuntimeError: boom" in result.stderr


def test_run_script_syntax_error_reports_failed() -> None:
    result = run_script("def broken(:\n    pass\n")

    assert result.status == "failed"
    assert "SyntaxError" in result.stderr


def test_run_script_infinite_loop_reports_timeout() -> None:
    started = time.monotonic()

    result = run_script("while True:\n    pass\n", timeout_s=2.0)

    elapsed = time.monotonic() - started
    assert result.status == "timeout"
    assert result.returncode is None
    # It was actually stopped, not merely reported as stopped.
    assert elapsed < 15.0
