"""lib — internal infrastructure for the ADW pipeline.

Two subsystems, each in its own subpackage:
- `lib.client` — the transport-agnostic Client Layer (retry/backoff + subprocess).
- `lib.log`    — the event logger (envelope, sinks, appenders).
"""
