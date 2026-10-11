"""Domain-specific failures for DA01 execution preparation."""


class ProtocolError(ValueError):
    """Raised when an execution artifact violates a frozen protocol rule."""


class ContractValidationError(ProtocolError):
    """Raised when a payload does not match its versioned JSON contract."""


class IsolationError(ProtocolError):
    """Raised when a method cannot be run under the required isolation boundary."""


class SealedArtifactError(ProtocolError):
    """Raised when a write-once artifact is missing, changed, or already exists."""


class MethodNotReadyError(ProtocolError):
    """Raised when a method interface exists but its scientific method is incomplete."""
