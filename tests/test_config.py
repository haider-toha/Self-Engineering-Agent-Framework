"""Behavioural tests for ``sea.config`` — the fail-fast configuration boundary.

The seam under test is ``Config.from_env()`` plus the *import* of the module
itself.  The old ``config.py`` raised inside a ``try`` at module scope and
swallowed the error, so the process continued with a broken config.  The
import-time test below is the regression guard for exactly that bug.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from sea.config import Config, ConfigError

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every numeric knob, with a value that cannot be parsed as a number.
GARBAGE_NUMERICS = [
    ("SEA_EMBEDDING_DIM", "lots"),
    ("SEA_SANDBOX_TIMEOUT_S", "soon"),
    ("SEA_SANDBOX_MEM_MB", "heaps"),
    ("SEA_MUTATION_MAX", "many"),
    ("SEA_MUTATION_TAU", "banana"),
    ("SEA_RETRIEVAL_THRESHOLD", "high"),
]

# Values that parse but are outside the range the field can legally take.
OUT_OF_RANGE_NUMERICS = [
    ("SEA_EMBEDDING_DIM", "0"),
    ("SEA_SANDBOX_TIMEOUT_S", "-1"),
    ("SEA_SANDBOX_MEM_MB", "0"),
    ("SEA_MUTATION_MAX", "0"),
    ("SEA_MUTATION_TAU", "1.5"),
    ("SEA_MUTATION_TAU", "-0.1"),
    ("SEA_RETRIEVAL_THRESHOLD", "1.5"),
]


@pytest.fixture(autouse=True)
def scrubbed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from an environment with no SEA / OpenAI settings."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for key in list(os.environ):
        if key.startswith("SEA_"):
            monkeypatch.delenv(key, raising=False)


# --------------------------------------------------------------------------
# Fail fast on a missing key — the hard requirement.
# --------------------------------------------------------------------------


def test_from_env_raises_config_error_when_api_key_absent() -> None:
    with pytest.raises(ConfigError) as exc_info:
        Config.from_env()
    assert "OPENAI_API_KEY" in str(exc_info.value)


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_from_env_raises_config_error_when_api_key_blank(
    monkeypatch: pytest.MonkeyPatch, blank: str
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", blank)
    with pytest.raises(ConfigError):
        Config.from_env()


def test_config_error_is_not_a_valueerror() -> None:
    """Callers must be able to distinguish config failure from a stray ValueError."""
    assert issubclass(ConfigError, Exception)
    assert not issubclass(ConfigError, ValueError)


# --------------------------------------------------------------------------
# The happy path and its defaults.
# --------------------------------------------------------------------------


def test_from_env_succeeds_when_api_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    cfg = Config.from_env()

    assert cfg.openai_api_key == "sk-test-123"


def test_from_env_strips_surrounding_whitespace_from_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "  sk-test-123\n")

    assert Config.from_env().openai_api_key == "sk-test-123"


def test_defaults_match_the_verified_openai_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defaults are pinned against the OpenAI docs, not against memory.

    ``text-embedding-3-small`` emits 1536 dimensions by default (verified on
    developers.openai.com).  ``gpt-4`` is deprecated with a shutdown date and
    must never be the default again.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    cfg = Config.from_env()

    assert cfg.embedding_model == "text-embedding-3-small"
    assert cfg.embedding_dim == 1536
    assert cfg.model != "gpt-4"


def test_path_fields_are_path_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    cfg = Config.from_env()

    assert isinstance(cfg.cache_dir, Path)
    assert isinstance(cfg.db_path, Path)


def test_from_env_creates_no_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reading config is pure: it validates, it does not touch the filesystem."""
    cache_dir = tmp_path / "does-not-exist-yet"
    db_path = tmp_path / "also-missing" / "registry.db"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("SEA_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("SEA_DB_PATH", str(db_path))

    Config.from_env()

    assert not cache_dir.exists()
    assert not db_path.parent.exists()


def test_env_vars_override_every_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("SEA_MODEL", "gpt-5.6-terra")
    monkeypatch.setenv("SEA_EMBEDDING_MODEL", "text-embedding-3-large")
    monkeypatch.setenv("SEA_EMBEDDING_DIM", "3072")
    monkeypatch.setenv("SEA_CACHE_DIR", "/tmp/sea-cache")
    monkeypatch.setenv("SEA_DB_PATH", "/tmp/sea.db")
    monkeypatch.setenv("SEA_SANDBOX_TIMEOUT_S", "12.5")
    monkeypatch.setenv("SEA_SANDBOX_MEM_MB", "256")
    monkeypatch.setenv("SEA_MUTATION_MAX", "17")
    monkeypatch.setenv("SEA_MUTATION_TAU", "0.65")
    monkeypatch.setenv("SEA_RETRIEVAL_THRESHOLD", "0.42")

    cfg = Config.from_env()

    assert cfg.model == "gpt-5.6-terra"
    assert cfg.embedding_model == "text-embedding-3-large"
    assert cfg.embedding_dim == 3072
    assert cfg.cache_dir == Path("/tmp/sea-cache")
    assert cfg.db_path == Path("/tmp/sea.db")
    assert cfg.sandbox_timeout_s == 12.5
    assert cfg.sandbox_mem_mb == 256
    assert cfg.mutation_max == 17
    assert cfg.mutation_tau == 0.65
    assert cfg.retrieval_threshold == 0.42


def test_config_is_immutable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    cfg = Config.from_env()

    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
        cfg.model = "something-else"  # type: ignore[misc]


# --------------------------------------------------------------------------
# Garbage numerics surface as ConfigError, never a raw ValueError from float().
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("var", "value"), GARBAGE_NUMERICS)
def test_unparseable_numeric_raises_config_error(
    monkeypatch: pytest.MonkeyPatch, var: str, value: str
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv(var, value)

    with pytest.raises(ConfigError) as exc_info:
        Config.from_env()

    message = str(exc_info.value)
    assert var in message, "error must name the offending environment variable"
    assert value in message, "error must show the value that could not be parsed"
    assert not isinstance(exc_info.value, ValueError), (
        "a bare ValueError from float()/int() must not escape from_env()"
    )


@pytest.mark.parametrize(("var", "value"), OUT_OF_RANGE_NUMERICS)
def test_out_of_range_numeric_raises_config_error(
    monkeypatch: pytest.MonkeyPatch, var: str, value: str
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv(var, value)

    with pytest.raises(ConfigError) as exc_info:
        Config.from_env()

    assert var in str(exc_info.value)


def test_blank_model_name_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("SEA_MODEL", "   ")

    with pytest.raises(ConfigError):
        Config.from_env()


# --------------------------------------------------------------------------
# THE regression test: importing the module must have no validation side effect.
# --------------------------------------------------------------------------


def test_importing_sea_config_without_env_neither_raises_nor_prints() -> None:
    """Import must be inert.

    The predecessor validated at module scope inside a ``try``/``except`` and
    logged-and-continued.  A fresh interpreter with *no* OPENAI_API_KEY must
    import ``sea.config`` with a clean exit and produce no output at all — no
    exception, and no "warning: key missing" chatter either.
    """
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(REPO_ROOT)}
    assert "OPENAI_API_KEY" not in env

    result = subprocess.run(
        [sys.executable, "-c", "import sea.config; assert sea.config.Config"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, f"import raised:\n{result.stderr}"
    assert result.stdout == "", f"import printed to stdout: {result.stdout!r}"
    assert result.stderr == "", f"import printed to stderr: {result.stderr!r}"
