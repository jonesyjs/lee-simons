"""Trigger core — shared logic turning a GitHub issue into a launched run.

Both triggers (webhook, cron) call `handle_issue`. Pure deterministic control
flow: loop guard, routing-token parse, mint id, launch the slice detached. No
agent calls — this is the code side of the Core-4 split.
"""

import os
import re
import subprocess
import uuid
from datetime import datetime, timezone

from modules import git_ops
from modules.git_ops import BOT_IDENTIFIER

# Dependent slices need an existing adw id (they resume a run — can't cold-start).
DEPENDENT_SLICES = {"review_document"}


def handle_issue(issue_id: str, body: str) -> str | None:
    """The single entry both triggers call. Returns the launched adw_id, or None."""
    if not _should_run(body):
        return None
    slice_name, provided_id = _parse_trigger(body)
    if slice_name is None:
        return None
    if slice_name in DEPENDENT_SLICES and not provided_id:
        git_ops.comment(
            issue_id,
            f"`{slice_name}` is a dependent slice — provide an existing adw id, "
            f"e.g. `{slice_name} adw-...`.",
        )
        return None
    adw_id = provided_id or _mint_adw_id()
    git_ops.comment(issue_id, f"Starting `{slice_name}` with id `{adw_id}`.")
    _launch(slice_name, issue_id, adw_id)
    return adw_id


# --- internals ------------------------------------------------------------


def _should_run(body: str) -> bool:
    """Loop guard (not our own comment) + a routing token is present."""
    if not body or BOT_IDENTIFIER in body:
        return False
    return "adw_" in body.lower()


def _parse_trigger(body: str) -> tuple[str | None, str | None]:
    """Extract (slice, adw_id) from a body like 'adw_plan_build adw-123'."""
    slice_match = re.search(r"adw_([a-z_]+)", body.lower())
    if not slice_match:
        return None, None
    id_match = re.search(r"\b(adw-[a-z0-9-]+)\b", body.lower())
    return slice_match.group(1), (id_match.group(1) if id_match else None)


def _mint_adw_id() -> str:
    return f"adw-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8]}"


def _launch(slice_name: str, issue_id: str, adw_id: str) -> None:
    """Launch the slice script detached (per the workflow design)."""
    script = os.path.join(_adw_root(), f"{slice_name}.py")
    subprocess.Popen(
        ["uv", "run", script, str(issue_id), adw_id],
        cwd=_adw_root(),
        start_new_session=True,
    )


def _adw_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
