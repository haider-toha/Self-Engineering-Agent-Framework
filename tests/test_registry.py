"""Behavioural tests for ``sea.registry``.

The database is real (a temp-file SQLite), not a mock — per the mocking rules,
you prefer a test DB to a fake one.  Every vector below is a real vector and
every expected cosine is computed by hand from the definition
``cos(a, b) = a·b / (|a||b|)``, never by re-running the implementation.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from sea.registry import Registry, RegistryError, ToolRecord

DIM = 4

# Three orthogonal unit vectors, so similarity ordering is unambiguous.
VEC_A = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
VEC_B = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
VEC_C = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)

# A query that leans hard towards A. By hand:
#   |q|      = sqrt(0.9^2 + 0.1^2) = sqrt(0.82) = 0.9055385...
#   cos(q,A) = 0.9 / 0.9055385 = 0.9938837...
#   cos(q,B) = 0.1 / 0.9055385 = 0.1104315...
#   cos(q,C) = 0.0
QUERY = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)
COS_QUERY_A = 0.9938837
COS_QUERY_B = 0.1104315


def make_record(name: str, **overrides: object) -> ToolRecord:
    fields: dict[str, object] = {
        "name": name,
        "task_id": "mbpp/11",
        "code": f"def {name}(x):\n    return x",
        "tests": f"def test_{name}():\n    assert {name}(1) == 1",
        "docstring": f"{name} does a thing",
        "mutation_score": 0.75,
        "created_at": "2026-07-13T00:00:00Z",
    }
    fields.update(overrides)
    return ToolRecord(**fields)  # type: ignore[arg-type]


@pytest.fixture
def registry(tmp_path: Path) -> Iterator[Registry]:
    reg = Registry(tmp_path / "registry.db")
    yield reg
    reg.close()


# --------------------------------------------------------------------------
# Round-trip
# --------------------------------------------------------------------------


def test_add_then_get_round_trips_every_field(registry: Registry) -> None:
    record = make_record("reverse_string")

    registry.add(record, VEC_A)

    assert registry.get("reverse_string") == record


def test_none_valued_fields_round_trip_as_none_not_zero(registry: Registry) -> None:
    """A tool that was never mutation-scored must not read back as scoring 0.0."""
    record = make_record("ungated", task_id=None, mutation_score=None)

    registry.add(record, VEC_A)
    loaded = registry.get("ungated")

    assert loaded is not None
    assert loaded.task_id is None
    assert loaded.mutation_score is None


def test_get_unknown_name_returns_none(registry: Registry) -> None:
    assert registry.get("never_added") is None


def test_all_on_an_empty_registry_returns_an_empty_list(registry: Registry) -> None:
    assert registry.all() == []


def test_all_returns_every_registered_tool(registry: Registry) -> None:
    registry.add(make_record("a"), VEC_A)
    registry.add(make_record("b"), VEC_B)

    assert {r.name for r in registry.all()} == {"a", "b"}


def test_records_survive_closing_and_reopening_the_database(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "registry.db"
    first = Registry(db_path)
    first.add(make_record("persisted"), VEC_A)
    first.close()

    second = Registry(db_path)
    try:
        loaded = second.get("persisted")
        assert loaded is not None
        assert loaded.code == "def persisted(x):\n    return x"
    finally:
        second.close()


def test_registry_can_be_used_as_a_context_manager(tmp_path: Path) -> None:
    with Registry(tmp_path / "registry.db") as reg:
        reg.add(make_record("scoped"), VEC_A)
        assert reg.get("scoped") is not None


# --------------------------------------------------------------------------
# Upsert
# --------------------------------------------------------------------------


def test_adding_a_duplicate_name_upserts_instead_of_exploding(
    registry: Registry,
) -> None:
    registry.add(make_record("tool", code="v1"), VEC_A)
    registry.add(make_record("tool", code="v2", mutation_score=0.9), VEC_B)

    assert len(registry.all()) == 1
    loaded = registry.get("tool")
    assert loaded is not None
    assert loaded.code == "v2"
    assert loaded.mutation_score == 0.9


def test_upsert_replaces_the_stored_embedding_too(registry: Registry) -> None:
    """Observable only through search — which is exactly the public seam."""
    registry.add(make_record("tool"), VEC_A)
    registry.add(make_record("tool"), VEC_C)

    [(_, score)] = registry.search(VEC_A, k=1)

    assert score == pytest.approx(0.0, abs=1e-6), "old embedding must be gone"


# --------------------------------------------------------------------------
# Cosine search
# --------------------------------------------------------------------------


def test_search_ranks_a_similar_vector_above_a_dissimilar_one(
    registry: Registry,
) -> None:
    registry.add(make_record("c_unrelated"), VEC_C)
    registry.add(make_record("b_somewhat"), VEC_B)
    registry.add(make_record("a_similar"), VEC_A)

    results = registry.search(QUERY, k=3)

    assert [record.name for record, _ in results] == [
        "a_similar",
        "b_somewhat",
        "c_unrelated",
    ]
    assert results[0][1] > results[1][1] > results[2][1]


def test_search_scores_match_the_cosine_definition(registry: Registry) -> None:
    registry.add(make_record("a"), VEC_A)
    registry.add(make_record("b"), VEC_B)

    scores = {record.name: score for record, score in registry.search(QUERY, k=2)}

    assert scores["a"] == pytest.approx(COS_QUERY_A, abs=1e-5)
    assert scores["b"] == pytest.approx(COS_QUERY_B, abs=1e-5)


def test_an_identical_vector_scores_one(registry: Registry) -> None:
    registry.add(make_record("a"), VEC_A)

    [(_, score)] = registry.search(VEC_A, k=1)

    assert score == pytest.approx(1.0, abs=1e-6)


def test_search_on_an_empty_registry_returns_an_empty_list(registry: Registry) -> None:
    """The predecessor raised KeyError here, on a cold start."""
    assert registry.search(QUERY, k=5) == []


def test_search_returns_at_most_k(registry: Registry) -> None:
    for name, vec in [("a", VEC_A), ("b", VEC_B), ("c", VEC_C)]:
        registry.add(make_record(name), vec)

    assert len(registry.search(QUERY, k=2)) == 2


def test_search_returns_everything_when_k_exceeds_the_library(
    registry: Registry,
) -> None:
    registry.add(make_record("a"), VEC_A)

    assert len(registry.search(QUERY, k=50)) == 1


def test_search_accepts_a_float64_query(registry: Registry) -> None:
    registry.add(make_record("a"), VEC_A)

    [(_, score)] = registry.search(np.array([1.0, 0.0, 0.0, 0.0]), k=1)

    assert score == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("k", [0, -1])
def test_search_rejects_a_non_positive_k(registry: Registry, k: int) -> None:
    registry.add(make_record("a"), VEC_A)

    with pytest.raises(RegistryError, match="k"):
        registry.search(QUERY, k=k)


# --------------------------------------------------------------------------
# Dimension safety — a silent mismatch would corrupt every retrieval number.
# --------------------------------------------------------------------------


def test_search_with_a_mismatched_query_dimension_raises(registry: Registry) -> None:
    registry.add(make_record("a"), VEC_A)  # 4-dim

    with pytest.raises(RegistryError, match="dimension"):
        registry.search(np.ones(3, dtype=np.float32), k=1)


def test_adding_a_second_embedding_dimension_raises(registry: Registry) -> None:
    registry.add(make_record("a"), VEC_A)  # 4-dim

    with pytest.raises(RegistryError, match="dimension"):
        registry.add(make_record("b"), np.ones(8, dtype=np.float32))


def test_add_rejects_a_non_1d_embedding(registry: Registry) -> None:
    with pytest.raises(RegistryError):
        registry.add(make_record("a"), np.ones((2, 2), dtype=np.float32))


def test_add_rejects_a_zero_vector_whose_cosine_is_undefined(
    registry: Registry,
) -> None:
    with pytest.raises(RegistryError):
        registry.add(make_record("a"), np.zeros(DIM, dtype=np.float32))


def test_add_rejects_a_non_finite_embedding(registry: Registry) -> None:
    with pytest.raises(RegistryError):
        registry.add(make_record("a"), np.array([1.0, np.nan, 0.0, 0.0]))


def test_search_rejects_a_zero_query_vector(registry: Registry) -> None:
    registry.add(make_record("a"), VEC_A)

    with pytest.raises(RegistryError):
        registry.search(np.zeros(DIM, dtype=np.float32), k=1)


# --------------------------------------------------------------------------
# Reuse accounting — report what happened, invent nothing.
# --------------------------------------------------------------------------


def test_reuse_stats_on_an_empty_registry_reports_zero_not_a_crash(
    registry: Registry,
) -> None:
    stats = registry.reuse_stats()

    assert stats["tools_registered"] == 0
    assert stats["total_retrievals"] == 0
    assert stats["unique_tools_retrieved"] == 0
    assert stats["unique_tasks_with_retrieval"] == 0
    assert stats["mean_retrieval_score"] is None
    assert stats["retrievals_per_tool"] == {}


def test_reuse_stats_counts_exactly_what_was_recorded(registry: Registry) -> None:
    registry.add(make_record("a"), VEC_A)
    registry.add(make_record("b"), VEC_B)
    registry.record_retrieval("a", "mbpp/2", 0.90)
    registry.record_retrieval("a", "mbpp/3", 0.80)
    registry.record_retrieval("b", "mbpp/3", 0.70)

    stats = registry.reuse_stats()

    assert stats["tools_registered"] == 2
    assert stats["total_retrievals"] == 3
    assert stats["unique_tools_retrieved"] == 2
    assert stats["unique_tasks_with_retrieval"] == 2  # mbpp/3 counted once
    assert stats["retrievals_per_tool"] == {"a": 2, "b": 1}
    assert stats["mean_retrieval_score"] == pytest.approx(0.80, abs=1e-6)


def test_a_registered_but_never_retrieved_tool_is_not_counted_as_reuse(
    registry: Registry,
) -> None:
    """Zero reuse must read as zero. No fabrication."""
    registry.add(make_record("never_used"), VEC_A)

    stats = registry.reuse_stats()

    assert stats["tools_registered"] == 1
    assert stats["total_retrievals"] == 0
    assert stats["retrievals_per_tool"] == {}


def test_reuse_stats_does_not_invent_a_reuse_rate(registry: Registry) -> None:
    """The registry cannot know the task denominator, so it must not report one."""
    assert "reuse_rate" not in registry.reuse_stats()


def test_recording_a_retrieval_of_an_unknown_tool_raises(registry: Registry) -> None:
    with pytest.raises(RegistryError, match="unknown"):
        registry.record_retrieval("ghost", "mbpp/1", 0.9)


def test_recording_a_non_finite_score_raises(registry: Registry) -> None:
    registry.add(make_record("a"), VEC_A)

    with pytest.raises(RegistryError):
        registry.record_retrieval("a", "mbpp/1", float("nan"))


def test_retrievals_survive_reopening_the_database(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.db"
    with Registry(db_path) as first:
        first.add(make_record("a"), VEC_A)
        first.record_retrieval("a", "mbpp/1", 0.95)

    with Registry(db_path) as second:
        assert second.reuse_stats()["total_retrievals"] == 1
