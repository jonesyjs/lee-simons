"""RunStateModel — the typed metadata contract for a pipeline run.

Holds run identifiers plus the current pipeline stage (so an external reader can
see where a run is without parsing the logs). `branch_name` and `stage` are set
after start via `dataclasses.replace`, producing a new frozen instance each time.

Artifact locations are NOT stored — they are computed on demand from these ids +
branch + a pipeline-supplied step name (see the SA doc).

Naming: model classes carry the `Model` suffix so they can live flat alongside
behaviour files, without a separate models/ subpackage.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RunStateModel:
    adw_id: str          # unique run id (guaranteed unique upstream)
    issue_id: str        # the git issue the run stems from
    branch_name: str | None = None  # set after branch generation
    stage: str | None = None         # current pipeline stage (plan/build/review/document)
