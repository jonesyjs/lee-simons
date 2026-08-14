import subprocess

from modules.lib.client.base_client import BaseClient, ClientError


class SubprocessClient(BaseClient):
    timeout: float = 120.0
    transient_signatures: tuple[str, ...] = ()

    def _invoke(self, argv: list[str]) -> str:
        """One raw subprocess call. Classifies the outcome for the base."""
        try:
            result = subprocess.run(
                argv, capture_output=True, text=True, timeout=self.timeout
            )
        except subprocess.TimeoutExpired as exc:
            raise ClientError("subprocess timed out", transient=True) from exc

        if result.returncode == 0:
            return result.stdout

        raise ClientError(
            f"exit {result.returncode}: {result.stderr.strip()}",
            transient=self._is_transient(result.stderr),
            code=result.returncode,
        )

    def _is_transient(self, stderr: str) -> bool:
        lowered = stderr.lower()
        return any(sig in lowered for sig in self.transient_signatures)
