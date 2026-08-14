"""models — the state data model.

- run_state.py — RunState (frozen dataclass) + PlanType. The typed data
  contract; the DAL and paths (behaviour) live one level up.
"""

from modules.lib.state.models.run_state import PlanType, RunState

__all__ = ["RunState", "PlanType"]
