"""RunState — the typed, write-once metadata contract for a pipeline run.

Holds only identifiers (not artifacts — those live in the git branch). Every
field is immutable; `branch_name` is the one set late (after branch generation)
via `dataclasses.replace`, producing a new frozen instance rather than mutating.

Artifact locations are NOT stored — they are computed on demand from these ids +
branch + a pipeline-supplied step name (see the SA doc).
"""

from dataclasses import dataclass
from enum import StrEnum


class PlanType(StrEnum):
    """Classifies a run; determines which workflow steps execute."""

    FEATURE = "feature"
    PATCH = "patch"


@dataclass(frozen=True)
class RunState:
    adw_id: str          # unique run id (guaranteed unique upstream)
    issue_id: str        # the git issue the run stems from
    plan_type: PlanType  # feature | patch
    branch_name: str | None = None  # set last, after branch generation, then frozen
