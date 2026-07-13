"""Thin OpenAI client with a content-addressed disk cache.

The cache is not an optimization.  It is what makes the experiment
**replayable**: a reviewer can re-run the whole sweep from a committed cache
directory without an API key and without spending a cent, and get byte-identical
prompts and responses.  It is also what makes a re-run deterministic even when
the model is not.

Verified against the OpenAI docs (developers.openai.com, July 2026):

* ``OpenAI(api_key=...)``
* ``client.chat.completions.create(model=..., messages=[...])``
  → ``response.choices[0].message.content``
* ``client.embeddings.create(model=..., input=..., encoding_format="float")``
  → ``response.data[0].embedding``
* ``text-embedding-3-small`` returns **1536** floats by default.
* Reasoning models (the GPT-5.x family) reject any ``temperature`` other than
  their default.  We detect that rejection, drop the parameter, and **warn** —
  never silently, because a caller that asked for greedy decoding and got
  sampling deserves to know.

Failures are raised, never swallowed into an empty string.  An empty completion
that looks like a valid one is how you get a research number that is a lie.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import warnings
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, TypeVar, runtime_checkable

import numpy as np
import openai

from sea.config import Config

__all__ = [
    "DEFAULT_BACKOFF_BASE_S",
    "DEFAULT_BACKOFF_MAX_S",
    "DEFAULT_MAX_RETRIES",
    "FakeLLM",
    "LLMClient",
    "LLMError",
    "OpenAIClient",
]

T = TypeVar("T")

DEFAULT_MAX_RETRIES = 5
DEFAULT_BACKOFF_BASE_S = 1.0
DEFAULT_BACKOFF_MAX_S = 30.0


class LLMError(RuntimeError):
    """A completion or embedding could not be produced.

    Always raised on a persistent failure.  There is deliberately no "return an
    empty string and carry on" path.
    """


@runtime_checkable
class LLMClient(Protocol):
    """The only surface the rest of the harness may depend on."""

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        """Return the model's reply to a (system, user) prompt pair."""
        ...

    def embed(self, text: str) -> np.ndarray:
        """Return a 1-D ``float32`` embedding of ``text``."""
        ...


# --------------------------------------------------------------------------
# Error classification
# --------------------------------------------------------------------------


def _is_transient(exc: BaseException) -> bool:
    """True for failures that a later identical request might survive."""
    if isinstance(
        exc,
        (
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.InternalServerError,
        ),
    ):
        return True
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


def _is_temperature_rejection(exc: BaseException | None) -> bool:
    """True for the 400 a reasoning model returns for a non-default temperature."""
    return isinstance(exc, openai.BadRequestError) and "temperature" in str(exc).lower()


# --------------------------------------------------------------------------
# Content-addressed cache keys
# --------------------------------------------------------------------------


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def completion_key(model: str, system: str, user: str, temperature: float) -> str:
    """sha256 over everything that can change a completion."""
    return _digest(
        {
            "kind": "completion",
            "model": model,
            "system": system,
            "user": user,
            "temperature": float(temperature),
        }
    )


def embedding_key(embedding_model: str, text: str) -> str:
    """sha256 over everything that can change an embedding."""
    return _digest({"kind": "embedding", "model": embedding_model, "text": text})


class OpenAIClient:
    """:class:`LLMClient` backed by the OpenAI SDK, in front of a disk cache.

    Args:
        cfg: Harness configuration (model names, key, cache dir).
        cache_dir: Overrides ``cfg.cache_dir``.
        client: The SDK client. Injectable so the network boundary can be
            faked in tests; in production leave it ``None`` and a real
            ``openai.OpenAI`` is built from ``cfg``.
        max_retries: Total attempts per request, including the first. Bounded
            on purpose — a persistent failure must surface, not spin.
        backoff_base_s: First backoff delay; doubles each retry.
        backoff_max_s: Ceiling on any single backoff delay.
    """

    def __init__(
        self,
        cfg: Config,
        *,
        cache_dir: Path | None = None,
        client: Any | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base_s: float = DEFAULT_BACKOFF_BASE_S,
        backoff_max_s: float = DEFAULT_BACKOFF_MAX_S,
    ) -> None:
        if max_retries < 1:
            raise ValueError(f"max_retries must be >= 1, got {max_retries}")

        self._cfg = cfg
        root = Path(cache_dir) if cache_dir is not None else Path(cfg.cache_dir)
        self._completions_dir = root / "completions"
        self._embeddings_dir = root / "embeddings"
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._backoff_max_s = backoff_max_s
        self._hits = 0
        self._misses = 0
        # Learned on the first 400: reasoning models reject a custom temperature.
        self._supports_temperature = True

        # The SDK retries internally by default; disable it so our bounded
        # backoff is the only retry policy in play.
        self._client = (
            client
            if client is not None
            else openai.OpenAI(api_key=cfg.openai_api_key, max_retries=0)
        )

    # -- cache ------------------------------------------------------------

    @property
    def cache_stats(self) -> dict[str, int]:
        """Cache hits and misses over this client's lifetime."""
        return {"hits": self._hits, "misses": self._misses}

    @property
    def cache_dir(self) -> Path:
        return self._completions_dir.parent

    def _read(self, path: Path, field: str) -> Any | None:
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload[field]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            warnings.warn(
                f"Ignoring unreadable cache entry {path}: {exc}. It will be re-fetched.",
                UserWarning,
                stacklevel=3,
            )
            return None

    def _write(self, path: Path, payload: Mapping[str, Any]) -> None:
        """Write atomically, so an interrupted overnight run leaves no half-entry."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp, path)

    # -- retry ------------------------------------------------------------

    def _with_retry(self, operation: str, call: Callable[[], T]) -> T:
        for attempt in range(1, self._max_retries + 1):
            try:
                return call()
            except Exception as exc:
                if not _is_transient(exc) or attempt == self._max_retries:
                    raise LLMError(
                        f"{operation} failed after {attempt} attempt(s): "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
                delay = min(
                    self._backoff_base_s * (2 ** (attempt - 1)), self._backoff_max_s
                )
                time.sleep(delay)
        raise AssertionError("unreachable: the loop above always returns or raises")

    # -- completions ------------------------------------------------------

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        key = completion_key(self._cfg.model, system, user, temperature)
        path = self._completions_dir / f"{key}.json"

        cached = self._read(path, "response")
        if isinstance(cached, str):
            self._hits += 1
            return cached
        self._misses += 1

        text = self._request_completion(system, user, temperature)
        self._write(
            path,
            {
                "key": key,
                "kind": "completion",
                "model": self._cfg.model,
                "temperature": temperature,
                "system": system,
                "user": user,
                "response": text,
            },
        )
        return text

    def _request_completion(self, system: str, user: str, temperature: float) -> str:
        def call(with_temperature: bool) -> Any:
            kwargs: dict[str, Any] = {
                "model": self._cfg.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            if with_temperature:
                kwargs["temperature"] = temperature
            return self._client.chat.completions.create(**kwargs)

        send_temperature = self._supports_temperature
        try:
            response = self._with_retry(
                "chat completion", lambda: call(send_temperature)
            )
        except LLMError as err:
            if not (send_temperature and _is_temperature_rejection(err.__cause__)):
                raise
            warnings.warn(
                f"Model {self._cfg.model!r} rejected temperature={temperature!r} "
                "(reasoning models only accept their default). Retrying without it. "
                "Sampling is now at the model's default, so this run is NOT greedy "
                "and NOT deterministic — pick a non-reasoning model if you need it.",
                UserWarning,
                stacklevel=3,
            )
            self._supports_temperature = False
            response = self._with_retry("chat completion", lambda: call(False))

        return _extract_content(response, self._cfg.model)

    # -- embeddings -------------------------------------------------------

    def embed(self, text: str) -> np.ndarray:
        key = embedding_key(self._cfg.embedding_model, text)
        path = self._embeddings_dir / f"{key}.json"

        cached = self._read(path, "embedding")
        if isinstance(cached, list):
            self._hits += 1
            return self._as_vector(cached)
        self._misses += 1

        response = self._with_retry(
            "embedding",
            lambda: self._client.embeddings.create(
                model=self._cfg.embedding_model,
                input=text,
                encoding_format="float",
            ),
        )
        raw = _extract_embedding(response, self._cfg.embedding_model)
        vector = self._as_vector(raw)

        self._write(
            path,
            {
                "key": key,
                "kind": "embedding",
                "model": self._cfg.embedding_model,
                "dim": int(vector.shape[0]),
                "text": text,
                "embedding": [float(x) for x in vector],
            },
        )
        return vector

    def _as_vector(self, raw: Sequence[float]) -> np.ndarray:
        vector = np.asarray(raw, dtype=np.float32)
        expected = self._cfg.embedding_dim
        if vector.ndim != 1 or vector.shape[0] != expected:
            raise LLMError(
                f"Model {self._cfg.embedding_model!r} returned an embedding of "
                f"dimension {vector.shape} but the config expects {expected}. "
                "Fix SEA_EMBEDDING_DIM or SEA_EMBEDDING_MODEL — a mismatch here "
                "silently corrupts retrieval."
            )
        return vector


def _extract_content(response: Any, model: str) -> str:
    """Unwrap ``choices[0].message.content``, refusing to invent a result."""
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise LLMError(
            f"Model {model!r} returned an unrecognised response shape: {response!r}"
        ) from exc
    if content is None:
        raise LLMError(
            f"Model {model!r} returned no content (content=None). Refusing to "
            "substitute an empty string."
        )
    return str(content)


def _extract_embedding(response: Any, model: str) -> Sequence[float]:
    try:
        return response.data[0].embedding
    except (AttributeError, IndexError, TypeError) as exc:
        raise LLMError(
            f"Model {model!r} returned an unrecognised embedding response: {response!r}"
        ) from exc


class FakeLLM:
    """An :class:`LLMClient` driven by a script.

    A seam for testing the *pipeline* — never a source of research numbers.
    Anything measured through a ``FakeLLM`` is a statement about our plumbing,
    not about a model.

    Args:
        completions: Either a mapping (keyed by ``user`` prompt, or by a
            ``(system, user)`` tuple) or a callable
            ``(system, user, temperature) -> str``.
        embeddings: Either a mapping ``text -> vector`` or a callable
            ``text -> vector``.  Unscripted text falls back to a deterministic
            pseudo-random unit vector derived from ``sha256(text)``, so
            retrieval tests get real, stable, distinguishable geometry.
        embedding_dim: Width of generated vectors.
        default_completion: Returned for an unscripted prompt.  Left ``None``,
            an unscripted prompt raises ``KeyError`` — silence would let a
            prompt-construction bug slip through a green test.
    """

    def __init__(
        self,
        completions: Mapping[Any, str] | Callable[..., str] | None = None,
        embeddings: (
            Mapping[str, Sequence[float]] | Callable[[str], Sequence[float]] | None
        ) = None,
        *,
        embedding_dim: int = 1536,
        default_completion: str | None = None,
    ) -> None:
        if embedding_dim < 1:
            raise ValueError(f"embedding_dim must be >= 1, got {embedding_dim}")
        self._completions = completions
        self._embeddings = embeddings
        self._dim = embedding_dim
        self._default = default_completion
        self.completion_calls = 0
        self.embed_calls = 0
        self.prompts: list[tuple[str, str, float]] = []
        self.texts: list[str] = []

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        self.completion_calls += 1
        self.prompts.append((system, user, temperature))

        if callable(self._completions):
            return self._completions(system=system, user=user, temperature=temperature)

        if isinstance(self._completions, Mapping):
            for candidate in ((system, user), user):
                if candidate in self._completions:
                    return self._completions[candidate]

        if self._default is not None:
            return self._default

        raise KeyError(
            f"FakeLLM has no scripted completion for user prompt {user!r}. "
            "Script it, or pass default_completion=... if you meant to stub it."
        )

    def embed(self, text: str) -> np.ndarray:
        self.embed_calls += 1
        self.texts.append(text)

        if callable(self._embeddings):
            return self._coerce(self._embeddings(text))
        if isinstance(self._embeddings, Mapping) and text in self._embeddings:
            return self._coerce(self._embeddings[text])
        return self._deterministic(text)

    def _coerce(self, raw: Sequence[float]) -> np.ndarray:
        return np.asarray(raw, dtype=np.float32)

    def _deterministic(self, text: str) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
        vector = np.random.default_rng(seed).standard_normal(self._dim)
        return (vector / np.linalg.norm(vector)).astype(np.float32)
