"""Process-local fault configuration for controlled single-process experiments."""

from dataclasses import asdict, dataclass
from threading import Lock
from time import sleep


@dataclass
class FaultConfig:
    """Configured deterministic delays and notification failures."""

    notification_delay_ms: int = 0
    task_delay_ms: int = 0
    fail_next_n_notifications: int = 0


class FaultState:
    """Thread-safe mutable fault state owned by the application process."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._config = FaultConfig()

    def get(self) -> FaultConfig:
        """Return a copy of current fault settings."""
        with self._lock:
            return FaultConfig(**asdict(self._config))

    def set(self, config: FaultConfig) -> FaultConfig:
        """Replace all fault settings."""
        with self._lock:
            self._config = FaultConfig(**asdict(config))
            return FaultConfig(**asdict(self._config))

    def reset(self) -> FaultConfig:
        """Disable all faults and return the resulting settings."""
        return self.set(FaultConfig())

    def task_delay(self) -> None:
        """Apply configured task-operation delay."""
        delay = self.get().task_delay_ms
        if delay:
            sleep(delay / 1000)

    def notification_delay(self) -> None:
        """Apply configured notification delay."""
        delay = self.get().notification_delay_ms
        if delay:
            sleep(delay / 1000)

    def consume_notification_failure(self) -> bool:
        """Consume one forced notification failure if configured."""
        with self._lock:
            if self._config.fail_next_n_notifications < 1:
                return False
            self._config.fail_next_n_notifications -= 1
            return True


fault_state = FaultState()
