from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).with_name("worktree_inventory.py")
SPEC = importlib.util.spec_from_file_location("worktree_inventory", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def completed(*args: str, returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(list(args), returncode, stdout=stdout, stderr=stderr)


class BaseBranchSelectionTests(unittest.TestCase):
    def test_prefers_origin_head_when_available(self) -> None:
        repo = Path("/tmp/repo")

        def fake_run_git(repo: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            if args == ("symbolic-ref", "refs/remotes/origin/HEAD"):
                return completed(*args, returncode=0, stdout="refs/remotes/origin/main\n")
            self.fail(f"Unexpected git invocation: {args}")

        with patch.object(MODULE, "run_git", side_effect=fake_run_git):
            branch, source = MODULE.select_base_branch(repo)

        self.assertEqual(branch, "main")
        self.assertEqual(source, "origin/HEAD")


class ClassifyEntryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        self.current_root = self.repo
        self.primary_root = self.repo
        self.policy_worktree_root = self.repo / ".worktrees"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def make_worktree(self, name: str, *, policy_path: bool = True) -> Path:
        root = self.policy_worktree_root if policy_path else self.repo / "legacy-worktrees"
        worktree = (root / name).resolve()
        worktree.mkdir(parents=True)
        (worktree / ".git").write_text("gitdir: mock\n")
        return worktree

    def test_clean_branch_with_same_tree_as_base_is_removable(self) -> None:
        branch = "chore/tree-equal"
        base_branch = "main"
        worktree = self.make_worktree("tree-equal")

        def fake_run_git(repo: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            if args == ("-C", str(worktree), "status", "--short", "--branch"):
                return completed(*args, returncode=0, stdout=f"## {branch}...origin/{branch}\n")
            if args == ("merge-base", "--is-ancestor", branch, base_branch):
                return completed(*args, returncode=1)
            if args == ("diff", "--quiet", base_branch, branch):
                return completed(*args, returncode=0)
            self.fail(f"Unexpected git invocation: {args}")

        with patch.object(MODULE, "run_git", side_effect=fake_run_git):
            row = MODULE.classify_entry(
                self.repo,
                self.current_root,
                self.primary_root,
                self.policy_worktree_root,
                base_branch,
                {"worktree": str(worktree), "branch": f"refs/heads/{branch}"},
            )

        self.assertEqual(row["action"], "remove")
        self.assertIn(f"tree matches {base_branch}", row["notes"])

    def test_clean_branch_with_patch_equivalent_commits_is_removable(self) -> None:
        branch = "fix/patch-equivalent"
        base_branch = "main"
        worktree = self.make_worktree("patch-equivalent")

        def fake_run_git(repo: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            if args == ("-C", str(worktree), "status", "--short", "--branch"):
                return completed(*args, returncode=0, stdout=f"## {branch}...origin/{branch}\n")
            if args == ("merge-base", "--is-ancestor", branch, base_branch):
                return completed(*args, returncode=1)
            if args == ("diff", "--quiet", base_branch, branch):
                return completed(*args, returncode=1)
            if args == ("cherry", "-v", base_branch, branch):
                return completed(
                    *args,
                    returncode=0,
                    stdout="- deadbeef patch equivalent change\n",
                )
            self.fail(f"Unexpected git invocation: {args}")

        with patch.object(MODULE, "run_git", side_effect=fake_run_git):
            row = MODULE.classify_entry(
                self.repo,
                self.current_root,
                self.primary_root,
                self.policy_worktree_root,
                base_branch,
                {"worktree": str(worktree), "branch": f"refs/heads/{branch}"},
            )

        self.assertEqual(row["action"], "remove")
        self.assertIn(f"patch-equivalent to {base_branch}", row["notes"])

    def test_clean_branch_with_changed_paths_matching_base_is_removable(self) -> None:
        branch = "chore/squash-equivalent"
        base_branch = "main"
        worktree = self.make_worktree("squash-equivalent")
        merge_base = "abc1234"

        def fake_run_git(repo: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            if args == ("-C", str(worktree), "status", "--short", "--branch"):
                return completed(*args, returncode=0, stdout=f"## {branch}...origin/{branch}\n")
            if args == ("merge-base", "--is-ancestor", branch, base_branch):
                return completed(*args, returncode=1)
            if args == ("diff", "--quiet", base_branch, branch):
                return completed(*args, returncode=1)
            if args == ("cherry", "-v", base_branch, branch):
                return completed(
                    *args,
                    returncode=0,
                    stdout=(
                        "+ deadbeef add inventory helper\n"
                        "+ feedface expand docs\n"
                    ),
                )
            if args == ("merge-base", branch, base_branch):
                return completed(*args, returncode=0, stdout=f"{merge_base}\n")
            if args == ("diff", "--name-only", f"{merge_base}..{branch}"):
                return completed(*args, returncode=0, stdout=".codex/config.toml\n")
            if args == ("diff", "--quiet", branch, base_branch, "--", ".codex/config.toml"):
                return completed(*args, returncode=0)
            self.fail(f"Unexpected git invocation: {args}")

        with patch.object(MODULE, "run_git", side_effect=fake_run_git):
            row = MODULE.classify_entry(
                self.repo,
                self.current_root,
                self.primary_root,
                self.policy_worktree_root,
                base_branch,
                {"worktree": str(worktree), "branch": f"refs/heads/{branch}"},
            )

        self.assertEqual(row["action"], "remove")
        self.assertIn(f"changed paths match {base_branch}", row["notes"])

    def test_marks_worktree_outside_policy_path_as_nonstandard(self) -> None:
        branch = "fix/legacy-location"
        base_branch = "main"
        worktree = self.make_worktree("legacy-location", policy_path=False)

        def fake_run_git(repo: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            if args == ("-C", str(worktree), "status", "--short", "--branch"):
                return completed(*args, returncode=0, stdout=f"## {branch}...origin/{branch}\n")
            if args == ("merge-base", "--is-ancestor", branch, base_branch):
                return completed(*args, returncode=0)
            self.fail(f"Unexpected git invocation: {args}")

        with patch.object(MODULE, "run_git", side_effect=fake_run_git):
            row = MODULE.classify_entry(
                self.repo,
                self.current_root,
                self.primary_root,
                self.policy_worktree_root,
                base_branch,
                {"worktree": str(worktree), "branch": f"refs/heads/{branch}"},
            )

        self.assertEqual(row["action"], "remove")
        self.assertIn("nonstandard-path", row["notes"])

    def test_keeps_protected_main_branch_even_when_clean(self) -> None:
        base_branch = "main"
        worktree = self.make_worktree("main")

        def fake_run_git(repo: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            if args == ("-C", str(worktree), "status", "--short", "--branch"):
                return completed(*args, returncode=0, stdout="## main...origin/main\n")
            if args == ("merge-base", "--is-ancestor", "main", base_branch):
                return completed(*args, returncode=0)
            self.fail(f"Unexpected git invocation: {args}")

        with patch.object(MODULE, "run_git", side_effect=fake_run_git):
            row = MODULE.classify_entry(
                self.repo,
                self.current_root,
                self.primary_root,
                self.policy_worktree_root,
                base_branch,
                {"worktree": str(worktree), "branch": "refs/heads/main"},
            )

        self.assertEqual(row["action"], "keep")
        self.assertIn("protected-branch", row["notes"])


if __name__ == "__main__":
    unittest.main()
