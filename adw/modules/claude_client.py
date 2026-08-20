from modules.lib.client import SubprocessClient


class ClaudeClient(SubprocessClient):
    transient_signatures = (
        "rate limit",
        "overloaded",
        "429",
        "503",
        "502",
        "connection reset",
        "temporarily unavailable",
    )

    def generate(self, prompt: str, cwd: str | None = None, model: str | None = None) -> str:
        argv = ["claude", "-p", prompt, "--dangerously-skip-permissions"]
        if model:
            argv += ["--model", model]
        return self.call(argv, cwd=cwd)
