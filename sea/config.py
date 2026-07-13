"""Fail-fast configuration for the SEA harness.

Contract
--------
1. Importing this module **never** raises, prints, logs, or reads a secret.
   There is deliberately no module-level validation.  The predecessor
   (``config.py``) validated at module scope inside a ``try``/``except`` and
   swallowed the failure, so the process carried on with a broken config.
2. :meth:`Config.from_env` is the *only* place validation happens, and it
   raises :class:`ConfigError` rather than returning a degraded object.
3. Every parse failure is reported as a :class:`ConfigError` that names the
   offending environment variable and shows the value it choked on.  A raw
   ``ValueError`` from deep inside ``float()`` never escapes.

Defaults are pinned against the OpenAI documentation, not memory:

* ``text-embedding-3-small`` emits **1536** dimensions by default.
* ``gpt-4`` is deprecated (shutdown 2026-10-23) and is never the default.
* The default chat model is a **non-reasoning** model, because the harness
  needs greedy decoding (``temperature=0``) for reproducibility.  The GPT-5.x
  reasoning family rejects ``temperature`` values other than its default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DEFAULT_CACHE_DIR",
    "DEFAULT_DB_PATH",
    "DEFAULT_EMBEDDING_DIM",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_MODEL",
    "Config",
    "ConfigError",
]


class ConfigError(Exception):
    """Configuration is missing or unusable.

    Deliberately **not** a subclass of ``ValueError``: a ``ValueError`` leaking
    out of :meth:`Config.from_env` would mean a numeric parse escaped
    unhandled, which is the bug this type exists to make impossible to miss.
    """


# --- Defaults (verified against developers.openai.com, July 2026) -----------

#: Non-reasoning, current, cheap, and honours ``temperature=0`` for greedy
#: decoding.  Reasoning models (GPT-5.x) reject a non-default ``temperature``,
#: which would make synthesis non-deterministic and the experiment unreplayable.
#: Override with ``SEA_MODEL`` to run a different model tier.
DEFAULT_MODEL = "gpt-4.1-mini"

#: 1536 dimensions by default; supports the ``dimensions`` parameter for
#: truncation, which we do not use.
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIM = 1536

#: One hidden directory holds everything the harness generates.
DEFAULT_CACHE_DIR = Path(".sea/cache")
DEFAULT_DB_PATH = Path(".sea/registry.db")

_DEFAULT_SANDBOX_TIMEOUT_S = 5.0
_DEFAULT_SANDBOX_MEM_MB = 512
_DEFAULT_MUTATION_MAX = 30
_DEFAULT_MUTATION_TAU = 0.8
_DEFAULT_RETRIEVAL_THRESHOLD = 0.85


def _env_str(name: str, default: str) -> str:
    """Read a non-empty string from the environment."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip()
    if not value:
        raise ConfigError(
            f"{name} is set but empty. Either unset it to use the default "
            f"({default!r}) or give it a value."
        )
    return value


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip()
    if not value:
        raise ConfigError(
            f"{name} is set but empty. Either unset it to use the default "
            f"({str(default)!r}) or give it a path."
        )
    return Path(value)


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ConfigError(
            f"{name} must be an integer, got {raw!r}."
        ) from exc
    if value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}, got {value}.")
    return value


def _env_float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    exclusive_minimum: bool = False,
) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}.") from exc
    if value != value:  # NaN
        raise ConfigError(f"{name} must be a number, got {raw!r}.")
    if minimum is not None:
        if exclusive_minimum and value <= minimum:
            raise ConfigError(f"{name} must be > {minimum}, got {value}.")
        if not exclusive_minimum and value < minimum:
            raise ConfigError(f"{name} must be >= {minimum}, got {value}.")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be <= {maximum}, got {value}.")
    return value


@dataclass(frozen=True)
class Config:
    """Immutable harness configuration.

    Construct it with :meth:`from_env`, or directly in tests.
    """

    openai_api_key: str
    model: str
    embedding_model: str
    embedding_dim: int
    cache_dir: Path
    db_path: Path
    sandbox_timeout_s: float
    sandbox_mem_mb: int
    mutation_max: int
    mutation_tau: float
    """Admission gate: a tool is admitted iff its mutation score >= this."""
    retrieval_threshold: float
    """Reuse gate: an existing tool is reused iff cosine similarity >= this."""

    @classmethod
    def from_env(cls) -> "Config":
        """Build a config from ``os.environ``.

        Reads only the process environment — no ``.env`` file, no network, no
        filesystem writes.  Callers that use a ``.env`` should export it first.

        Raises:
            ConfigError: ``OPENAI_API_KEY`` is missing or blank, or any
                ``SEA_*`` value cannot be parsed or is out of range.
        """
        raw_key = os.environ.get("OPENAI_API_KEY")
        if raw_key is None or not raw_key.strip():
            raise ConfigError(
                "OPENAI_API_KEY is not set. The harness cannot synthesize or "
                "embed anything without it. Export it and re-run:\n"
                "    export OPENAI_API_KEY=sk-..."
            )

        return cls(
            openai_api_key=raw_key.strip(),
            model=_env_str("SEA_MODEL", DEFAULT_MODEL),
            embedding_model=_env_str("SEA_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
            embedding_dim=_env_int(
                "SEA_EMBEDDING_DIM", DEFAULT_EMBEDDING_DIM, minimum=1
            ),
            cache_dir=_env_path("SEA_CACHE_DIR", DEFAULT_CACHE_DIR),
            db_path=_env_path("SEA_DB_PATH", DEFAULT_DB_PATH),
            sandbox_timeout_s=_env_float(
                "SEA_SANDBOX_TIMEOUT_S",
                _DEFAULT_SANDBOX_TIMEOUT_S,
                minimum=0.0,
                exclusive_minimum=True,
            ),
            sandbox_mem_mb=_env_int(
                "SEA_SANDBOX_MEM_MB", _DEFAULT_SANDBOX_MEM_MB, minimum=1
            ),
            mutation_max=_env_int(
                "SEA_MUTATION_MAX", _DEFAULT_MUTATION_MAX, minimum=1
            ),
            mutation_tau=_env_float(
                "SEA_MUTATION_TAU", _DEFAULT_MUTATION_TAU, minimum=0.0, maximum=1.0
            ),
            retrieval_threshold=_env_float(
                "SEA_RETRIEVAL_THRESHOLD",
                _DEFAULT_RETRIEVAL_THRESHOLD,
                minimum=0.0,
                maximum=1.0,
            ),
        )
