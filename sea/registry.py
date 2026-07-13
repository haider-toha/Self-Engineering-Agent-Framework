"""The tool library: SQLite storage + brute-force numpy cosine retrieval.

Replaces the deleted Supabase/pgvector layer (ADR-001).  The committed
migration for that layer could not work — ``embedding BYTEA`` with no pgvector,
no indexes, and zero SQL functions behind six Python RPC calls — so retrieval
was provably broken.  This module is hermetic, offline, and needs no setup:
a reviewer clones the repo and re-runs the experiment.

Retrieval is an exact brute-force cosine scan.  At our scale (hundreds of tools
× 1536 dimensions) that is a microsecond-class matmul; an ANN index below ~10⁵
vectors buys nothing and costs a dependency and an approximation error.

Two invariants exist because violating them would corrupt a *research number*
rather than merely crash:

* **Dimensions are homogeneous.**  A query or a stored vector of the wrong width
  raises, rather than silently ranking garbage.
* **Reuse is counted, never inferred.**  :meth:`Registry.reuse_stats` reports
  only what was actually recorded, and deliberately refuses to divide by a task
  count it does not know.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

import numpy as np

__all__ = ["Registry", "RegistryError", "ToolRecord"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tools (
    name           TEXT    PRIMARY KEY,
    task_id        TEXT,
    code           TEXT    NOT NULL,
    tests          TEXT    NOT NULL,
    docstring      TEXT    NOT NULL,
    mutation_score REAL,
    created_at     TEXT    NOT NULL,
    embedding      BLOB    NOT NULL,
    embedding_dim  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS retrievals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name    TEXT    NOT NULL,
    task_id      TEXT    NOT NULL,
    score        REAL    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_retrievals_tool ON retrievals(tool_name);
"""


class RegistryError(RuntimeError):
    """The registry was asked to do something that would corrupt its contents."""


@dataclass(frozen=True)
class ToolRecord:
    """One synthesized tool, exactly as it was admitted to the library."""

    name: str
    task_id: str | None
    code: str
    tests: str
    docstring: str
    mutation_score: float | None
    created_at: str


class Registry:
    """A persistent, searchable library of synthesized tools.

    Args:
        db_path: SQLite file.  Parent directories are created.  ``":memory:"``
            works for throwaway use.

    Note:
        The connection is single-threaded (SQLite's default).  Sharing one
        ``Registry`` across threads raises rather than corrupting the file.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- lifecycle --------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Registry":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # -- writes -----------------------------------------------------------

    def add(self, rec: ToolRecord, embedding: np.ndarray) -> None:
        """Register a tool, replacing any tool of the same name.

        Idempotent: re-running a sweep upserts rather than exploding on a
        duplicate name.  The new record wins outright — code, tests, score, and
        embedding are all replaced.

        Raises:
            RegistryError: The embedding is not a usable 1-D finite non-zero
                vector, or its width disagrees with what is already stored.
        """
        vector = self._validate_embedding(embedding)
        dim = int(vector.shape[0])

        stored_dim = self._stored_dim()
        if stored_dim is not None and stored_dim != dim:
            raise RegistryError(
                f"Cannot add {rec.name!r}: its embedding has dimension {dim} but "
                f"the registry already stores {stored_dim}-dimensional embeddings. "
                "Mixing embedding models in one registry makes every cosine score "
                "meaningless — use a fresh db_path for a new embedding model."
            )

        self._conn.execute(
            """
            INSERT INTO tools
                (name, task_id, code, tests, docstring, mutation_score,
                 created_at, embedding, embedding_dim)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                task_id        = excluded.task_id,
                code           = excluded.code,
                tests          = excluded.tests,
                docstring      = excluded.docstring,
                mutation_score = excluded.mutation_score,
                created_at     = excluded.created_at,
                embedding      = excluded.embedding,
                embedding_dim  = excluded.embedding_dim
            """,
            (
                rec.name,
                rec.task_id,
                rec.code,
                rec.tests,
                rec.docstring,
                rec.mutation_score,
                rec.created_at,
                vector.tobytes(),
                dim,
            ),
        )
        self._conn.commit()

    def record_retrieval(self, tool_name: str, task_id: str, score: float) -> None:
        """Log that ``tool_name`` was retrieved for ``task_id`` at ``score``.

        This is the raw material for the observed reuse rate.  Phase 4 reports
        that number honestly even if it turns out to be ~0, so nothing may be
        written here that did not actually happen.

        Raises:
            RegistryError: The tool is not registered, or the score is not a
                finite number.
        """
        value = float(score)
        if not np.isfinite(value):
            raise RegistryError(
                f"Retrieval score for {tool_name!r} must be finite, got {score!r}."
            )
        if self.get(tool_name) is None:
            raise RegistryError(
                f"Cannot record a retrieval of unknown tool {tool_name!r}. "
                "Reuse is only ever counted for tools that are actually in the library."
            )
        self._conn.execute(
            "INSERT INTO retrievals (tool_name, task_id, score) VALUES (?, ?, ?)",
            (tool_name, task_id, value),
        )
        self._conn.commit()

    # -- reads ------------------------------------------------------------

    def get(self, name: str) -> ToolRecord | None:
        """Return the tool called ``name``, or ``None`` if it is not registered."""
        row = self._conn.execute(
            "SELECT * FROM tools WHERE name = ?", (name,)
        ).fetchone()
        return _to_record(row) if row is not None else None

    def all(self) -> list[ToolRecord]:
        """Every registered tool, oldest first.  Empty registry gives ``[]``."""
        rows = self._conn.execute(
            "SELECT * FROM tools ORDER BY created_at, name"
        ).fetchall()
        return [_to_record(row) for row in rows]

    def search(
        self, query_embedding: np.ndarray, *, k: int = 5
    ) -> list[tuple[ToolRecord, float]]:
        """Return the ``k`` most cosine-similar tools, most similar first.

        Returns ``[]`` on an empty registry — a cold start is normal, not an
        error.

        Raises:
            RegistryError: ``k`` is not positive, or the query vector is
                unusable or the wrong width for the stored embeddings.
        """
        if k <= 0:
            raise RegistryError(f"k must be positive, got {k}.")

        query = self._validate_embedding(query_embedding, what="query embedding")

        rows = self._conn.execute(
            "SELECT * FROM tools ORDER BY created_at, name"
        ).fetchall()
        if not rows:
            return []

        stored_dim = int(rows[0]["embedding_dim"])
        if stored_dim != int(query.shape[0]):
            raise RegistryError(
                f"Query embedding has dimension {int(query.shape[0])} but the "
                f"registry stores {stored_dim}-dimensional embeddings. Refusing "
                "to rank on incompatible vectors."
            )

        matrix = np.vstack(
            [np.frombuffer(row["embedding"], dtype=np.float32) for row in rows]
        )
        # Every stored vector is validated non-zero on the way in, so no
        # division-by-zero is reachable here.
        norms = np.linalg.norm(matrix, axis=1)
        scores = (matrix @ query) / (norms * float(np.linalg.norm(query)))

        order = np.argsort(-scores, kind="stable")[:k]
        return [(_to_record(rows[i]), float(scores[i])) for i in order]

    def reuse_stats(self) -> dict[str, Any]:
        """What the library was *observed* to reuse.

        Reports counts only.  It deliberately does **not** report a "reuse
        rate": the registry does not know how many tasks the sweep attempted,
        and inventing a denominator is how a reuse number gets fabricated.
        The caller that owns the task list computes the rate.

        Returns:
            ``tools_registered``, ``total_retrievals``, ``unique_tools_retrieved``,
            ``unique_tasks_with_retrieval``, ``mean_retrieval_score`` (``None``
            when nothing was retrieved), and ``retrievals_per_tool``.
        """
        tools = self._conn.execute("SELECT COUNT(*) AS n FROM tools").fetchone()["n"]
        summary = self._conn.execute(
            """
            SELECT COUNT(*)                  AS total,
                   COUNT(DISTINCT tool_name) AS tools,
                   COUNT(DISTINCT task_id)   AS tasks,
                   AVG(score)                AS mean_score
            FROM retrievals
            """
        ).fetchone()
        per_tool = self._conn.execute(
            """
            SELECT tool_name, COUNT(*) AS n
            FROM retrievals
            GROUP BY tool_name
            ORDER BY tool_name
            """
        ).fetchall()

        mean = summary["mean_score"]
        return {
            "tools_registered": int(tools),
            "total_retrievals": int(summary["total"]),
            "unique_tools_retrieved": int(summary["tools"]),
            "unique_tasks_with_retrieval": int(summary["tasks"]),
            "mean_retrieval_score": None if mean is None else float(mean),
            "retrievals_per_tool": {r["tool_name"]: int(r["n"]) for r in per_tool},
        }

    # -- internals --------------------------------------------------------

    def _stored_dim(self) -> int | None:
        row = self._conn.execute("SELECT embedding_dim FROM tools LIMIT 1").fetchone()
        return None if row is None else int(row["embedding_dim"])

    @staticmethod
    def _validate_embedding(
        embedding: np.ndarray, *, what: str = "embedding"
    ) -> np.ndarray:
        vector = np.asarray(embedding, dtype=np.float32)
        if vector.ndim != 1:
            raise RegistryError(
                f"The {what} must be 1-D, got shape {vector.shape}."
            )
        if vector.size == 0:
            raise RegistryError(f"The {what} is empty.")
        if not bool(np.all(np.isfinite(vector))):
            raise RegistryError(f"The {what} contains NaN or inf.")
        if float(np.linalg.norm(vector)) == 0.0:
            raise RegistryError(
                f"The {what} is the zero vector, whose cosine similarity is undefined."
            )
        return vector


def _to_record(row: sqlite3.Row) -> ToolRecord:
    return ToolRecord(
        name=row["name"],
        task_id=row["task_id"],
        code=row["code"],
        tests=row["tests"],
        docstring=row["docstring"],
        mutation_score=(
            None if row["mutation_score"] is None else float(row["mutation_score"])
        ),
        created_at=row["created_at"],
    )
