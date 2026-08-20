"""lib.client — transport-agnostic Client Layer infrastructure.

Generic and blind to the app: the retry/backoff base and the subprocess
transport. App-specific command clients (claude_client, git_client) live in
`modules/` and build on these.
"""

from modules.lib.client.base_client import BaseClient, ClientError
from modules.lib.client.subprocess_client import SubprocessClient

__all__ = ["BaseClient", "ClientError", "SubprocessClient"]
