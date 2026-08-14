from modules.lib.client import SubprocessClient


class GitClient(SubprocessClient):
    transient_signatures = (
        "index.lock",
        "could not lock",
        "unable to create",
    )

    # --- worktree commands ---

    def worktree_add(self, path: str, branch: str) -> str:
        return self.call(["git", "worktree", "add", "-b", branch, path])

    def worktree_list(self) -> str:
        return self.call(["git", "worktree", "list"])

    def worktree_remove(self, path: str) -> str:
        return self.call(["git", "worktree", "remove", path])

    # --- work commands (run inside a worktree via -C) ---

    def diff(self, path: str) -> str:
        return self.call(["git", "-C", path, "diff"])

    def stage_all(self, path: str) -> str:
        return self.call(["git", "-C", path, "add", "-A"])

    def commit(self, path: str, message: str) -> str:
        return self.call(["git", "-C", path, "commit", "-m", message])
