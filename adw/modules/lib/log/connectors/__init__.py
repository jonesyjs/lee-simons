"""connectors — self-contained adapters connecting the logger to external systems.

Each connector is a Sink that owns its client and reads the run target from log
context, so no injection is needed. This is the coupling edge; the rest of
`lib.log` stays free of concrete clients. Not auto-imported by `lib.log` — import
a connector explicitly where you wire appenders (e.g. modules/log_setup.py).
"""

from modules.lib.log.connectors.github import GitHubConnector

__all__ = ["GitHubConnector"]
