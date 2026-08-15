import time
from abc import ABC, abstractmethod


class ClientError(RuntimeError):
    def __init__(self, message: str, *, transient: bool, code: int | None = None):
        super().__init__(message)
        self.transient = transient
        self.code = code


class BaseClient(ABC):
    max_attempts: int = 3
    backoff_base: float = 0.1

    def call(self, request, **kwargs):
        # kwargs are transport-specific options (e.g. cwd for subprocess),
        # forwarded to _invoke; the base itself stays agnostic of them.
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._invoke(request, **kwargs)
            except ClientError as err:
                if not err.transient or attempt == self.max_attempts:
                    raise
                # exponential backoff
                time.sleep(self.backoff_base * (2 ** (attempt - 1)))
        raise AssertionError("retry loop exited without result")

    @abstractmethod
    def _invoke(self, request, **kwargs):
        ...
