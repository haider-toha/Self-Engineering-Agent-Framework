"""Isolated execution of untrusted generated code — the ONLY place code runs.

Every execution in this project (test verification, mutation analysis, and the
independent MBPP+ oracle) goes through this module. Nothing anywhere else may
call ``exec``, ``eval``, ``importlib``, or ``subprocess`` on generated code.

SAFETY BOUNDARY, NOT A SECURITY BOUNDARY
----------------------------------------
This is stated plainly because the project's credibility depends on not
overstating it (see ADR-002 in ``audit/research-pivot/02-thesis-and-architecture.md``).

Our threat model is **accidental damage from code an LLM generated off benign
benchmark prompts**: infinite loops, runaway memory allocation, and stray writes
into the working tree. Against that threat this module is effective.

Our threat model is **not** a malicious adversary. A determined exploit escapes
this sandbox trivially: the child is a full CPython interpreter with an intact
filesystem and network stack. It can read your home directory, open sockets, and
write anywhere the invoking user can write. Do **not** point this at adversarial
input. Anyone running the harness against untrusted prompts should run the entire
harness inside the provided container.

What is actually enforced, per platform
---------------------------------------
=========================  =====================  ==========================
Control                    Linux                  macOS (measured, Darwin 25)
=========================  =====================  ==========================
Wall-clock timeout         yes                    yes
``RLIMIT_CPU``             yes                    yes (SIGXCPU observed)
``RLIMIT_AS`` (memory)     yes                    **NO — silently unavailable**
``RLIMIT_FSIZE``           yes                    yes
Process-group kill         yes                    yes
Scrubbed environment       yes                    yes
Scratch working directory  yes                    yes
=========================  =====================  ==========================

``RLIMIT_AS`` is the honest asterisk. On macOS ``setrlimit(RLIMIT_AS, ...)``
raises ``ValueError: current limit exceeds maximum limit`` and, even where the
call is accepted, the limit is not enforced — a child asked for 2 GB under a
512 MB limit allocated it without complaint. We therefore attempt the limit and
swallow the failure rather than pretend. On macOS the effective backstop against
a memory bomb is the wall-clock timeout and ``RLIMIT_CPU``, not ``RLIMIT_AS``.

We deliberately do **not** set ``RLIMIT_NPROC``: it is accounted against the
invoking user's *system-wide* process count, so a low limit fails
unpredictably depending on unrelated load on the machine.

Concurrency
-----------
``preexec_fn`` is not safe to call from a multi-threaded parent (it runs Python
between ``fork`` and ``exec``, where a lock held by another thread can deadlock
the child). If you parallelise the harness, parallelise with **processes**
(``ProcessPoolExecutor``), not threads. The functions here hold no shared state
and are safe to use from separate processes.
"""

from __future__ import annotations

import math
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

__all__ = ["ExecResult", "ExecStatus", "run_pytest", "run_script"]

ExecStatus = Literal["passed", "failed", "timeout", "error"]

_MB = 1024 * 1024

#: Hard ceiling on captured stdout/stderr, per stream. A runaway ``print`` in a
#: mutant must not become a memory bomb in the *parent* process.
_MAX_CAPTURE_BYTES = 1 * _MB

#: Ceiling on bytes the child may write to any single file. Bounds a runaway
#: writer without interfering with any plausible benchmark workload.
_FSIZE_LIMIT_BYTES = 64 * _MB

#: Grace period to reap a process group after SIGKILL.
_KILL_GRACE_S = 5.0

#: pytest's exit codes (``pytest.ExitCode``). Reproduced rather than imported so
#: that the parent process never needs pytest importable to interpret a result.
_PYTEST_OK = 0
_PYTEST_TESTS_FAILED = 1


@dataclass(frozen=True)
class ExecResult:
    """Outcome of one sandboxed execution.

    Attributes:
        status: ``"passed"`` iff the process exited 0. ``"failed"`` iff a test
            assertion failed. ``"timeout"`` iff the process exhausted its wall
            clock or CPU budget. ``"error"`` for everything else — collection
            errors, import errors, an empty test suite, or a crash.
        stdout: Captured standard output, truncated to 1 MiB with an explicit
            marker appended if it overflowed.
        stderr: Captured standard error, truncated the same way.
        returncode: The process's exit status, negative if it died from signal
            ``n`` (e.g. ``-24`` for SIGXCPU). ``None`` iff the process never
            exited on its own and we had to kill its process group — i.e.
            exactly the wall-clock timeout case.
        duration_s: Wall-clock seconds from spawn to reap.
    """

    status: ExecStatus
    stdout: str
    stderr: str
    returncode: int | None
    duration_s: float


def run_pytest(
    impl_code: str,
    test_code: str,
    *,
    timeout_s: float = 10.0,
    mem_limit_mb: int = 512,
) -> ExecResult:
    """Run ``test_code`` against ``impl_code`` in an isolated subprocess.

    ``impl_code`` is written to ``tool.py`` and ``test_code`` to ``test_tool.py``
    in a fresh temporary directory, which becomes the child's working directory.
    Tests therefore import the implementation as ``from tool import <fn>``.
    pytest runs as a subprocess (never in-process), and the temporary directory
    is always removed.

    A suite that collects **zero** tests is reported as ``"error"``, not
    ``"passed"``. This is deliberate: an empty suite trivially "passes", and
    admitting a tool on the strength of a vacuous oracle would silently corrupt
    every downstream number.

    Args:
        impl_code: Source of the implementation module.
        test_code: Source of the pytest suite. Never modified (ADR-003).
        timeout_s: Wall-clock budget for the whole pytest run.
        mem_limit_mb: Address-space limit. **Not enforced on macOS** — see the
            module docstring.

    Returns:
        The :class:`ExecResult`. ``status == "passed"`` iff pytest exited 0.
    """
    with tempfile.TemporaryDirectory(
        prefix="sea-sandbox-", ignore_cleanup_errors=True
    ) as root:
        work = Path(root) / "work"
        work.mkdir()
        (work / "tool.py").write_text(impl_code, encoding="utf-8")
        (work / "test_tool.py").write_text(test_code, encoding="utf-8")

        return _spawn(
            argv=[
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "test_tool.py",
            ],
            work=work,
            root=Path(root),
            timeout_s=timeout_s,
            mem_limit_mb=mem_limit_mb,
        )


def run_script(
    source: str,
    *,
    timeout_s: float = 10.0,
    mem_limit_mb: int = 512,
) -> ExecResult:
    """Run an arbitrary Python source string in an isolated subprocess.

    Same isolation as :func:`run_pytest`. Used by the differential-testing
    harness, which drives the independent MBPP+ oracle and needs to execute a
    script rather than a pytest suite.

    Status mapping for a script (CPython exits 1 on any uncaught exception, so
    a script cannot distinguish a failed assertion from a crash the way pytest
    can):

    * ``"passed"``  — exited 0.
    * ``"failed"``  — exited 1, i.e. it raised. That covers ``AssertionError``
      (the differential oracle's signal), and equally ``SyntaxError`` or any
      other uncaught exception. Read ``stderr`` if you need to tell them apart.
    * ``"timeout"`` — exhausted its wall-clock or CPU budget.
    * ``"error"``   — any other exit status, or death by signal.

    Args:
        source: The script source.
        timeout_s: Wall-clock budget.
        mem_limit_mb: Address-space limit. **Not enforced on macOS.**

    Returns:
        The :class:`ExecResult`.
    """
    with tempfile.TemporaryDirectory(
        prefix="sea-sandbox-", ignore_cleanup_errors=True
    ) as root:
        work = Path(root) / "work"
        work.mkdir()
        script = work / "script.py"
        script.write_text(source, encoding="utf-8")

        return _spawn(
            argv=[sys.executable, "script.py"],
            work=work,
            root=Path(root),
            timeout_s=timeout_s,
            mem_limit_mb=mem_limit_mb,
        )


def _spawn(
    *,
    argv: list[str],
    work: Path,
    root: Path,
    timeout_s: float,
    mem_limit_mb: int,
) -> ExecResult:
    """Run ``argv`` under every isolation control this platform supports."""
    # Capture to files rather than pipes. A pipe can deadlock: if the child
    # spawns a grandchild that inherits the write end and outlives it,
    # ``communicate()`` blocks forever waiting for EOF. Files cannot deadlock,
    # and they let us bound what we read back into the parent.
    out_path = root / "stdout.log"
    err_path = root / "stderr.log"

    started = time.monotonic()
    with out_path.open("wb") as out_f, err_path.open("wb") as err_f:
        proc = subprocess.Popen(
            argv,
            cwd=str(work),
            stdin=subprocess.DEVNULL,
            stdout=out_f,
            stderr=err_f,
            env=_scrubbed_env(work),
            preexec_fn=_limits(timeout_s, mem_limit_mb),  # noqa: PLW1509
            # setsid() in the child, so it leads its own process group and we
            # can kill the whole tree. pytest's children would otherwise leak.
            start_new_session=True,
        )

        timed_out = False
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_group(proc)

    duration_s = time.monotonic() - started
    stdout = _read_truncated(out_path)
    stderr = _read_truncated(err_path)
    returncode = None if timed_out else proc.returncode

    return ExecResult(
        status=_classify(timed_out=timed_out, returncode=proc.returncode),
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
        duration_s=duration_s,
    )


def _classify(*, timed_out: bool, returncode: int | None) -> ExecStatus:
    """Map a process outcome onto the four-valued status.

    ``SIGXCPU`` is reported as a timeout, not an error: it means the process
    exhausted its CPU budget, which is the same fault as running out of wall
    clock. It fires as a backstop when the process burns CPU faster than the
    wall clock elapses, or if the parent dies before it can kill the group.
    """
    if timed_out:
        return "timeout"
    if returncode == _PYTEST_OK:
        return "passed"
    if returncode == -signal.SIGXCPU:
        return "timeout"
    if returncode == _PYTEST_TESTS_FAILED:
        return "failed"
    # Everything else: collection error (2), internal error (3), usage error
    # (4), no tests collected (5), or death by any other signal.
    return "error"


def _limits(timeout_s: float, mem_limit_mb: int) -> Callable[[], None]:
    """Build the ``preexec_fn`` that clamps the child's resources.

    Runs in the child between ``fork`` and ``exec``. It must never raise (that
    would abort the spawn) and must never write to stdio (that would pollute
    the captured output of every single run).
    """
    # Leave the wall-clock timeout as the primary control and the CPU limit as a
    # backstop, so a process that is merely slow is reported as a timeout by the
    # parent rather than racing a SIGXCPU.
    cpu_seconds = max(1, math.ceil(timeout_s) + 1)

    def preexec() -> None:
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        except (ValueError, OSError):
            pass

        # RLIMIT_AS is a real control on Linux and a no-op on macOS, where the
        # call raises outright. Attempt it, never depend on it. See module docs.
        try:
            limit = mem_limit_mb * _MB
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        except (ValueError, OSError, AttributeError):
            pass

        try:
            resource.setrlimit(
                resource.RLIMIT_FSIZE, (_FSIZE_LIMIT_BYTES, _FSIZE_LIMIT_BYTES)
            )
        except (ValueError, OSError, AttributeError):
            pass

    return preexec


def _scrubbed_env(work: Path) -> dict[str, str]:
    """Build a minimal environment for the child.

    The parent's environment is **not** inherited. This is what keeps
    ``OPENAI_API_KEY`` (and every other credential on the machine) out of reach
    of generated code, and it also stops the parent's ``PYTHONPATH`` from
    leaking the repository onto the child's import path.

    ``sys.executable`` is passed as an absolute path, so the child still finds
    its own virtualenv: CPython resolves its prefix from the interpreter's
    location via ``pyvenv.cfg``, not from the environment. ``PYTHONHOME`` is
    therefore deliberately absent — setting it would break exactly that.
    """
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        # Point HOME and TMPDIR at the scratch directory so that anything the
        # child writes "helpfully" lands somewhere we delete.
        "HOME": str(work),
        "TMPDIR": str(work),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
        # Determinism and hygiene: no .pyc litter, no user site-packages
        # shadowing the venv, no randomised hash seed, and no third-party pytest
        # plugins auto-loading into the child (which would make every one of the
        # ~10^5 executions slower and non-hermetic).
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }


def _kill_process_group(proc: subprocess.Popen[bytes]) -> None:
    """SIGKILL the child's entire process group and reap it.

    Killing ``proc`` alone is not enough: pytest and any subprocess a mutant
    spawns are separate processes, and they survive the death of their parent.
    The child was started with ``start_new_session=True``, so its process group
    id equals its pid and one ``killpg`` takes down the whole tree.
    """
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        # Already dead, or already reparented. Nothing to kill.
        pass

    try:
        proc.wait(timeout=_KILL_GRACE_S)
    except subprocess.TimeoutExpired:
        # Should be unreachable: SIGKILL is not catchable. Belt and braces so a
        # single wedged execution can never hang a 400-task sweep.
        proc.kill()
        try:
            proc.wait(timeout=_KILL_GRACE_S)
        except subprocess.TimeoutExpired:
            pass


def _read_truncated(path: Path) -> str:
    """Read at most ``_MAX_CAPTURE_BYTES`` from ``path``, flagging truncation."""
    try:
        with path.open("rb") as handle:
            data = handle.read(_MAX_CAPTURE_BYTES + 1)
    except OSError:
        return ""

    if len(data) > _MAX_CAPTURE_BYTES:
        text = data[:_MAX_CAPTURE_BYTES].decode("utf-8", errors="replace")
        return f"{text}\n[sea.sandbox: output truncated at {_MAX_CAPTURE_BYTES} bytes]"
    return data.decode("utf-8", errors="replace")
