"""Technology-agnostic P method contract; no scientific algorithm is supplied."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from experiments.execution.tooling.errors import MethodNotReadyError

P_INTERFACE_VERSION = "P_GOVERNED_ADAPTATION_INTERFACE_V1"
P_ALGORITHM_STATUS = "NOT_READY"


class ProposedAdaptationMethod(Protocol):
    """Interface for a separately specified, versioned governed method."""

    @property
    def version(self) -> str:
        """Return the immutable method/algorithm version."""

    def propose(self, method_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return a prediction and proposed operations without oracle access."""


def require_p_algorithm() -> None:
    """Stop measured P execution until a reviewed general algorithm is supplied."""
    raise MethodNotReadyError(
        "P interface exists, but Impact, activation, candidate, and governance rules are not frozen"
    )


__all__ = [
    "P_ALGORITHM_STATUS",
    "P_INTERFACE_VERSION",
    "ProposedAdaptationMethod",
    "require_p_algorithm",
]
