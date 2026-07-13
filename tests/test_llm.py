"""Behavioural tests for ``sea.llm``.

No live API calls.  The OpenAI SDK client is an *external system boundary*, so
it is the one thing we stand a fake in for; everything else — the cache, the
retry policy, the request we construct — is the real code under test.

Two rules these tests obey:

* We never assert that a fake returned what we told it to return and call that
  a result.  We assert **behavioural properties**: how many times the network
  boundary was crossed, what request was put on the wire, what type came back.
* Cache behaviour *is* call-count behaviour.  "A cache hit does not touch the
  network" can only be observed by counting crossings of the boundary, so the
  call counter is the specification here, not an implementation detail.
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import numpy as np
import openai
import pytest

from sea.config import Config
from sea.llm import FakeLLM, LLMClient, LLMError, OpenAIClient

DIM = 4

# --------------------------------------------------------------------------
# Test doubles for the external boundary only.
# --------------------------------------------------------------------------


def _http_error(exc_type: type[openai.APIStatusError], status: int, message: str):
    """Build a *real* openai SDK exception, so retry classification is exercised."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return exc_type(message, response=httpx.Response(status, request=request), body=None)


def rate_limited() -> openai.RateLimitError:
    return _http_error(openai.RateLimitError, 429, "Rate limit reached")


def server_error() -> openai.InternalServerError:
    return _http_error(openai.InternalServerError, 503, "The server is overloaded")


def bad_request(message: str = "Invalid schema") -> openai.BadRequestError:
    return _http_error(openai.BadRequestError, 400, message)


def unsupported_temperature() -> openai.BadRequestError:
    return bad_request(
        "Unsupported value: 'temperature' does not support 0.0 with this model. "
        "Only the default (1) is supported."
    )


class FakeTransport:
    """Stands in for ``openai.OpenAI``, recording the requests it is handed.

    ``errors`` is consumed one item per call; a non-``None`` item is raised.
    Pass ``itertools.repeat(exc)`` to model a persistent outage.
    """

    def __init__(
        self,
        *,
        completion_text: str = "def f(): pass",
        embedding: list[float] | None = None,
        errors: Iterable[BaseException | None] | None = None,
    ) -> None:
        self.completion_requests: list[dict[str, Any]] = []
        self.embedding_requests: list[dict[str, Any]] = []
        self._completion_text = completion_text
        self._embedding = embedding if embedding is not None else [0.5, 0.25, 0.0, -0.5]
        self._errors: Iterator[BaseException | None] = iter(errors or ())
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create_completion)
        )
        self.embeddings = SimpleNamespace(create=self._create_embedding)

    def _maybe_raise(self) -> None:
        error = next(self._errors, None)
        if error is not None:
            raise error

    def _create_completion(self, **kwargs: Any) -> SimpleNamespace:
        self.completion_requests.append(kwargs)
        self._maybe_raise()
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=self._completion_text))
            ]
        )

    def _create_embedding(self, **kwargs: Any) -> SimpleNamespace:
        self.embedding_requests.append(kwargs)
        self._maybe_raise()
        return SimpleNamespace(data=[SimpleNamespace(embedding=list(self._embedding))])


def make_config(tmp_path: Path, **overrides: Any) -> Config:
    defaults: dict[str, Any] = {
        "openai_api_key": "sk-test",
        "model": "gpt-4.1-mini",
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": DIM,
        "cache_dir": tmp_path / "cache",
        "db_path": tmp_path / "registry.db",
        "sandbox_timeout_s": 5.0,
        "sandbox_mem_mb": 512,
        "mutation_max": 30,
        "mutation_tau": 0.8,
        "retrieval_threshold": 0.85,
    }
    return Config(**{**defaults, **overrides})


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    return make_config(tmp_path)


def make_client(cfg: Config, transport: FakeTransport, **kwargs: Any) -> OpenAIClient:
    kwargs.setdefault("max_retries", 3)
    kwargs.setdefault("backoff_base_s", 0.0)  # keep the suite fast, still bounded
    return OpenAIClient(cfg, client=transport, **kwargs)


# --------------------------------------------------------------------------
# Request construction — what we actually put on the wire.
# --------------------------------------------------------------------------


def test_complete_sends_model_messages_and_temperature_from_config(
    cfg: Config,
) -> None:
    transport = FakeTransport()
    client = make_client(cfg, transport)

    client.complete("you are a compiler", "write add(a, b)", temperature=0.0)

    (request,) = transport.completion_requests
    assert request["model"] == "gpt-4.1-mini"
    assert request["messages"] == [
        {"role": "system", "content": "you are a compiler"},
        {"role": "user", "content": "write add(a, b)"},
    ]
    assert request["temperature"] == 0.0


def test_complete_extracts_content_from_the_sdk_response_shape(cfg: Config) -> None:
    """We unwrap ``choices[0].message.content`` — the shape the SDK documents."""
    transport = FakeTransport(completion_text="def add(a, b): return a + b")
    client = make_client(cfg, transport)

    assert client.complete("s", "u") == "def add(a, b): return a + b"


def test_embed_sends_model_and_input(cfg: Config) -> None:
    transport = FakeTransport()
    client = make_client(cfg, transport)

    client.embed("reverse a string")

    (request,) = transport.embedding_requests
    assert request["model"] == "text-embedding-3-small"
    assert request["input"] == "reverse a string"


def test_embed_returns_a_float32_vector(cfg: Config) -> None:
    transport = FakeTransport(embedding=[1.0, 2.0, 3.0, 4.0])
    client = make_client(cfg, transport)

    vector = client.embed("anything")

    assert isinstance(vector, np.ndarray)
    assert vector.dtype == np.float32
    assert vector.shape == (DIM,)


def test_embed_rejects_a_vector_of_the_wrong_dimension(cfg: Config) -> None:
    """A model/dim mismatch must fail loudly, not silently poison the registry."""
    transport = FakeTransport(embedding=[1.0, 2.0])  # cfg says DIM == 4
    client = make_client(cfg, transport)

    with pytest.raises(LLMError, match="dimension"):
        client.embed("anything")


# --------------------------------------------------------------------------
# The cache. The point of it is that a hit does not cross the network boundary.
# --------------------------------------------------------------------------


def test_repeated_completion_hits_the_cache_and_skips_the_network(cfg: Config) -> None:
    transport = FakeTransport()
    client = make_client(cfg, transport)

    first = client.complete("s", "u", temperature=0.0)
    second = client.complete("s", "u", temperature=0.0)

    assert len(transport.completion_requests) == 1, "second call must not hit the API"
    assert first == second
    assert client.cache_stats == {"hits": 1, "misses": 1}


def test_repeated_embedding_hits_the_cache_and_skips_the_network(cfg: Config) -> None:
    transport = FakeTransport()
    client = make_client(cfg, transport)

    first = client.embed("same text")
    second = client.embed("same text")

    assert len(transport.embedding_requests) == 1
    np.testing.assert_array_equal(first, second)
    assert client.cache_stats == {"hits": 1, "misses": 1}


def test_cached_embedding_rehydrates_from_disk_as_float32(cfg: Config) -> None:
    transport = FakeTransport(embedding=[0.1, 0.2, 0.3, 0.4])
    client = make_client(cfg, transport)
    client.embed("text")  # populate the cache

    reloaded = make_client(cfg, FakeTransport(embedding=[9.0, 9.0, 9.0, 9.0]))
    vector = reloaded.embed("text")

    assert vector.dtype == np.float32
    np.testing.assert_allclose(vector, np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32))


def test_cache_survives_process_restart_so_a_reviewer_can_replay_offline(
    cfg: Config,
) -> None:
    """A fresh client over the same cache_dir answers without any transport call."""
    warm = make_client(cfg, FakeTransport(completion_text="cached answer"))
    warm.complete("s", "u")

    cold_transport = FakeTransport(completion_text="THIS WOULD BE A NETWORK CALL")
    cold = make_client(cfg, cold_transport)
    answer = cold.complete("s", "u")

    assert cold_transport.completion_requests == [], "cache hit must not touch the API"
    assert answer == "cached answer"
    assert cold.cache_stats == {"hits": 1, "misses": 0}


@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param(
            {"system": "a", "user": "u", "temperature": 0.0},
            {"system": "b", "user": "u", "temperature": 0.0},
            id="system-differs",
        ),
        pytest.param(
            {"system": "s", "user": "x", "temperature": 0.0},
            {"system": "s", "user": "y", "temperature": 0.0},
            id="user-differs",
        ),
        pytest.param(
            {"system": "s", "user": "u", "temperature": 0.0},
            {"system": "s", "user": "u", "temperature": 0.7},
            id="temperature-differs",
        ),
    ],
)
def test_completion_cache_key_separates_different_requests(
    tmp_path: Path, first: dict[str, Any], second: dict[str, Any]
) -> None:
    cfg = make_config(tmp_path)
    transport = FakeTransport()
    client = make_client(cfg, transport)

    client.complete(first["system"], first["user"], temperature=first["temperature"])
    client.complete(second["system"], second["user"], temperature=second["temperature"])

    assert len(transport.completion_requests) == 2
    assert client.cache_stats == {"hits": 0, "misses": 2}


def test_completion_cache_key_separates_different_models(tmp_path: Path) -> None:
    cache_dir = tmp_path / "shared-cache"
    transport_a = FakeTransport()
    transport_b = FakeTransport()

    make_client(
        make_config(tmp_path, model="gpt-4.1-mini", cache_dir=cache_dir), transport_a
    ).complete("s", "u")
    client_b = make_client(
        make_config(tmp_path, model="gpt-5.6-terra", cache_dir=cache_dir), transport_b
    )
    client_b.complete("s", "u")

    assert len(transport_b.completion_requests) == 1, "a new model must not reuse a cache entry"
    assert client_b.cache_stats == {"hits": 0, "misses": 1}


def test_embedding_cache_key_separates_different_texts_and_models(
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "shared-cache"
    transport = FakeTransport()
    client = make_client(make_config(tmp_path, cache_dir=cache_dir), transport)

    client.embed("alpha")
    client.embed("beta")
    assert len(transport.embedding_requests) == 2

    other_model = make_client(
        make_config(
            tmp_path, cache_dir=cache_dir, embedding_model="text-embedding-3-large"
        ),
        transport,
    )
    other_model.embed("alpha")
    assert len(transport.embedding_requests) == 3


def test_cache_dir_override_takes_precedence_over_config(tmp_path: Path) -> None:
    override = tmp_path / "explicit"
    cfg = make_config(tmp_path, cache_dir=tmp_path / "from-config")
    client = OpenAIClient(cfg, cache_dir=override, client=FakeTransport())

    client.complete("s", "u")

    assert list(override.rglob("*.json")), "entries must land in the override directory"
    assert not (tmp_path / "from-config").exists()


def test_a_corrupt_cache_entry_is_treated_as_a_miss_not_a_crash(cfg: Config) -> None:
    transport = FakeTransport(completion_text="fresh")
    client = make_client(cfg, transport)
    client.complete("s", "u")
    entry = next(iter(cfg.cache_dir.rglob("*.json")))
    entry.write_text("{ this is not json", encoding="utf-8")

    with pytest.warns(UserWarning):
        answer = make_client(cfg, transport).complete("s", "u")

    assert answer == "fresh"
    assert len(transport.completion_requests) == 2, "corrupt entry must be re-fetched"


def test_cached_entry_is_human_readable_json(cfg: Config) -> None:
    """A reviewer must be able to open the cache and see what was asked."""
    client = make_client(cfg, FakeTransport(completion_text="answer"))
    client.complete("sys prompt", "user prompt", temperature=0.0)

    entry = json.loads(next(iter(cfg.cache_dir.rglob("*.json"))).read_text())

    assert entry["model"] == "gpt-4.1-mini"
    assert entry["system"] == "sys prompt"
    assert entry["user"] == "user prompt"
    assert entry["temperature"] == 0.0
    assert entry["response"] == "answer"


# --------------------------------------------------------------------------
# Retry: bounded, and a persistent failure is raised — never swallowed.
# --------------------------------------------------------------------------


def test_transient_errors_are_retried_and_then_succeed(cfg: Config) -> None:
    transport = FakeTransport(
        completion_text="recovered", errors=[rate_limited(), server_error(), None]
    )
    client = make_client(cfg, transport, max_retries=5)

    answer = client.complete("s", "u")

    assert len(transport.completion_requests) == 3
    assert answer == "recovered"


def test_a_persistent_failure_gives_up_and_raises_rather_than_returning_empty(
    cfg: Config,
) -> None:
    transport = FakeTransport(errors=itertools.repeat(server_error()))
    client = make_client(cfg, transport, max_retries=3)

    with pytest.raises(LLMError) as exc_info:
        client.complete("s", "u")

    assert len(transport.completion_requests) == 3, "retries must be bounded"
    assert isinstance(exc_info.value.__cause__, openai.InternalServerError)


def test_a_persistent_embedding_failure_raises(cfg: Config) -> None:
    transport = FakeTransport(errors=itertools.repeat(rate_limited()))
    client = make_client(cfg, transport, max_retries=2)

    with pytest.raises(LLMError):
        client.embed("text")

    assert len(transport.embedding_requests) == 2


def test_a_failed_call_is_never_cached(cfg: Config) -> None:
    transport = FakeTransport(errors=itertools.repeat(server_error()))
    client = make_client(cfg, transport, max_retries=2)
    with pytest.raises(LLMError):
        client.complete("s", "u")

    assert list(cfg.cache_dir.rglob("*.json")) == []

    recovered = make_client(cfg, FakeTransport(completion_text="ok"))
    assert recovered.complete("s", "u") == "ok"
    assert recovered.cache_stats == {"hits": 0, "misses": 1}


def test_a_non_transient_error_is_not_retried(cfg: Config) -> None:
    transport = FakeTransport(errors=itertools.repeat(bad_request()))
    client = make_client(cfg, transport, max_retries=5)

    with pytest.raises(LLMError):
        client.complete("s", "u")

    assert len(transport.completion_requests) == 1, "a 400 is not worth retrying"


# --------------------------------------------------------------------------
# Reasoning models reject a non-default `temperature`. Degrade loudly, not silently.
# --------------------------------------------------------------------------


def test_a_model_that_rejects_temperature_is_retried_without_it_and_warns(
    cfg: Config,
) -> None:
    transport = FakeTransport(
        completion_text="ok", errors=[unsupported_temperature(), None]
    )
    client = make_client(cfg, transport)

    with pytest.warns(UserWarning, match="temperature"):
        answer = client.complete("s", "u", temperature=0.0)

    assert answer == "ok"
    first, second = transport.completion_requests
    assert first["temperature"] == 0.0
    assert "temperature" not in second, "the retry must omit the rejected parameter"


def test_temperature_is_dropped_for_subsequent_calls_to_the_same_model(
    cfg: Config,
) -> None:
    """We learn the model's capability once; we do not eat a 400 on every call."""
    transport = FakeTransport(errors=[unsupported_temperature(), None])
    client = make_client(cfg, transport)
    with pytest.warns(UserWarning):
        client.complete("s", "first")

    client.complete("s", "second")

    assert len(transport.completion_requests) == 3
    assert "temperature" not in transport.completion_requests[-1]


# --------------------------------------------------------------------------
# FakeLLM — a pipeline seam, never a source of research numbers.
# --------------------------------------------------------------------------


def test_openai_client_and_fake_llm_both_satisfy_the_protocol(cfg: Config) -> None:
    assert isinstance(make_client(cfg, FakeTransport()), LLMClient)
    assert isinstance(FakeLLM(embedding_dim=DIM), LLMClient)


def test_fake_llm_replays_a_scripted_completion() -> None:
    fake = FakeLLM(completions={"write add": "def add(a, b): return a + b"})

    assert fake.complete("sys", "write add") == "def add(a, b): return a + b"
    assert fake.completion_calls == 1


def test_fake_llm_accepts_a_callable_script() -> None:
    fake = FakeLLM(completions=lambda system, user, temperature: f"echo:{user}")

    assert fake.complete("sys", "hello") == "echo:hello"


def test_fake_llm_refuses_an_unscripted_prompt_instead_of_returning_empty() -> None:
    """Silence on an unscripted prompt would let a pipeline bug pass a test."""
    fake = FakeLLM(completions={"known": "ok"})

    with pytest.raises(KeyError):
        fake.complete("sys", "unknown")


def test_fake_llm_falls_back_to_a_default_when_one_is_given() -> None:
    fake = FakeLLM(completions={}, default_completion="stub")

    assert fake.complete("sys", "anything") == "stub"


def test_fake_llm_embeddings_are_deterministic_unit_float32_vectors() -> None:
    fake = FakeLLM(embedding_dim=DIM)

    first = fake.embed("reverse a string")
    second = fake.embed("reverse a string")
    other = fake.embed("sort a list")

    assert first.dtype == np.float32
    assert first.shape == (DIM,)
    np.testing.assert_array_equal(first, second)
    assert float(np.linalg.norm(first)) == pytest.approx(1.0, abs=1e-5)
    assert not np.array_equal(first, other)
    assert fake.embed_calls == 3


def test_fake_llm_replays_a_scripted_embedding() -> None:
    fake = FakeLLM(embeddings={"x": [1.0, 0.0, 0.0, 0.0]}, embedding_dim=DIM)

    vector = fake.embed("x")

    assert vector.dtype == np.float32
    np.testing.assert_array_equal(vector, np.array([1, 0, 0, 0], dtype=np.float32))
