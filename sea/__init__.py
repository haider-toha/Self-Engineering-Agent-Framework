"""SEA — Self-Engineering Agent research harness.

Measures the **False Admission Rate** of a self-verified tool library:
the probability that a tool fails an independent held-out oracle *given*
that it passed its own LLM-generated test suite and was admitted.

This package deliberately performs **no work at import time**.  Every module
is importable without an API key, without a database, and without network
access; validation happens when you call something, never when you import it.
Import submodules directly:

    from sea.config import Config
    from sea.llm import OpenAIClient
    from sea.registry import Registry
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
