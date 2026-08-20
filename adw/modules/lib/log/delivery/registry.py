"""The appender registry — which appenders are active for this run.

Module-level state: the list `log()` fans events to. Wired once at startup via
`set_appenders` (see modules/log_setup.py). Lives in `delivery/` because it holds
appenders; `logger.py` only reads it.

The default is a single console appender (accept-all) so logging works before
`configure_logging` runs.
"""

from modules.lib.log.delivery.appenders import Appender
from modules.lib.log.delivery.sinks import ConsoleSink

_appenders: list[Appender] = []


def appenders() -> list[Appender]:
    """The live registry — what `log()` iterates."""
    return _appenders


def set_appenders(new: list[Appender]) -> None:
    """Replace the registry (startup wiring; also used by tests)."""
    _appenders[:] = new


def add_appender(appender: Appender) -> None:
    _appenders.append(appender)


def clear_appenders() -> None:
    _appenders.clear()


def reset_appenders() -> None:
    """Restore the default: everything to the console."""
    _appenders[:] = [Appender(ConsoleSink())]


reset_appenders()
