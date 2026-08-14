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

    def generate(self, prompt: str, model: str | None = None) -> str:
        argv = ["claude", "-p", prompt]
        if model:
            argv += ["--model", model]
        return self.call(argv)
