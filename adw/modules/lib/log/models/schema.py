"""Schema evolution (Phase 5).

The envelope is versioned as a unit (`schema_version`); the payload inside it
evolves freely. Policy:

- Additive by default — new optional fields need no version bump; old readers
  ignore what they don't know.
- Breaking change — bump the version and register an upcaster so historical
  events (log files, archives) can still be read as the current shape.
- True restructuring — express it as an upcaster too; that is what upcasting is
  for.

Emission always writes `CURRENT_VERSION`. Upcasting only matters when *reading*
older events back. At 1.0 there are no upcasters yet — the machinery is here so
the first breaking change is a registration, not a rewrite.
"""

from collections.abc import Callable

from modules.lib.log.models.events import SCHEMA_VERSION

CURRENT_VERSION = SCHEMA_VERSION

# from_version -> function that upgrades a raw event dict by exactly one step,
# returning a dict whose schema_version is the next version.
_UPCASTERS: dict[str, Callable[[dict], dict]] = {}


def register_upcaster(from_version: str, fn: Callable[[dict], dict]) -> None:
    _UPCASTERS[from_version] = fn


def upcast(raw: dict, target: str | None = None) -> dict:
    """Migrate a raw event dict up to `target` (default: current), one
    registered step at a time. Raises if a step is missing or doesn't advance."""
    target = target or CURRENT_VERSION
    version = raw.get("schema_version", "1.0")
    while version != target:
        fn = _UPCASTERS.get(version)
        if fn is None:
            raise ValueError(f"no upcaster registered from schema {version!r}")
        raw = fn(raw)
        nxt = raw.get("schema_version")
        if nxt == version:
            raise ValueError(f"upcaster from {version!r} did not bump schema_version")
        version = nxt
    return raw
