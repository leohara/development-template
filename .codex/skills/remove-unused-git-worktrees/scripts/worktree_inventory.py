#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_git(repo: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd or repo),
        text=True,
        capture_output=True,
        check=False,
    )


def git_output(repo: Path, *args: str, cwd: Path | None = None) -> str:
    result = run_git(repo, *args, cwd=cwd)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def resolve_current_worktree_root() -> Path:
    output = git_output(Path.cwd(), "rev-parse", "--path-format=absolute", "--show-toplevel").strip()
    return Path(output).resolve()


def resolve_primary_workspace_root(current_root: Path) -> Path:
    common_dir_raw = git_output(current_root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    common_dir = Path(common_dir_raw)
    if not common_dir.is_absolute():
        common_dir = (current_root / common_dir).resolve()
    return common_dir.parent.resolve()


def parse_worktrees(raw: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in raw.splitlines():
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value

    if current:
        entries.append(current)

    return entries


def path_contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def git_ref_exists(repo: Path, ref: str) -> bool:
    return run_git(repo, "show-ref", "--verify", "--quiet", ref).returncode == 0


def select_base_branch(repo: Path, explicit_branch: str | None = None) -> tuple[str, str]:
    if explicit_branch:
        return explicit_branch, "explicit"

    origin_head = run_git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    if origin_head.returncode == 0:
        ref = origin_head.stdout.strip()
        prefix = "refs/remotes/origin/"
        if ref.startswith(prefix):
            return ref.removeprefix(prefix), "origin/HEAD"

    for branch in ("main", "develop", "master"):
        if git_ref_exists(repo, f"refs/heads/{branch}") or git_ref_exists(repo, f"refs/remotes/origin/{branch}"):
            return branch, "fallback"

    current_branch = git_output(repo, "branch", "--show-current").strip()
    if current_branch:
        return current_branch, "current branch fallback"

    raise RuntimeError("Unable to determine a base branch. Pass --base-branch explicitly.")


def protected_branches(base_branch: str) -> set[str]:
    return {base_branch, "develop", "main", "master"}


def branch_base_status(repo: Path, branch: str, base_branch: str) -> tuple[str, list[str]]:
    notes: list[str] = []

    if branch == base_branch:
        return "base", notes

    merged_check = run_git(repo, "merge-base", "--is-ancestor", branch, base_branch)
    if merged_check.returncode == 0:
        return "merged", notes
    if merged_check.returncode != 1:
        notes.append("merge-check failed")
        return "?", notes

    tree_match = run_git(repo, "diff", "--quiet", base_branch, branch)
    if tree_match.returncode == 0:
        notes.append(f"tree matches {base_branch}")
        return "equivalent", notes
    if tree_match.returncode != 1:
        notes.append("tree-diff failed")
        return "?", notes

    cherry = run_git(repo, "cherry", "-v", base_branch, branch)
    if cherry.returncode != 0:
        notes.append("cherry-check failed")
        return "?", notes

    cherry_lines = [line for line in cherry.stdout.splitlines() if line.strip()]
    if cherry_lines and all(line.startswith("-") for line in cherry_lines):
        notes.append(f"patch-equivalent to {base_branch}")
        return "equivalent", notes
    if cherry_lines and all(line.startswith("+") for line in cherry_lines):
        changed_paths_match_base, path_notes = branch_changed_paths_match_base(repo, branch, base_branch)
        notes.extend(path_notes)
        if changed_paths_match_base:
            return "equivalent", notes
    if any(line.startswith("+") for line in cherry_lines):
        return "ahead", notes
    if not cherry_lines:
        notes.append("no unique commits")
        return "merged", notes

    notes.append("unexpected cherry output")
    return "?", notes


def branch_changed_paths_match_base(repo: Path, branch: str, base_branch: str) -> tuple[bool, list[str]]:
    notes: list[str] = []

    merge_base = run_git(repo, "merge-base", branch, base_branch)
    if merge_base.returncode != 0:
        notes.append("merge-base lookup failed")
        return False, notes

    merge_base_sha = merge_base.stdout.strip()
    changed_paths = run_git(repo, "diff", "--name-only", f"{merge_base_sha}..{branch}")
    if changed_paths.returncode != 0:
        notes.append("changed-path lookup failed")
        return False, notes

    path_list = [line for line in changed_paths.stdout.splitlines() if line.strip()]
    if not path_list:
        notes.append("no changed paths")
        return True, notes

    for path in path_list:
        path_diff = run_git(repo, "diff", "--quiet", branch, base_branch, "--", path)
        if path_diff.returncode == 0:
            continue
        if path_diff.returncode == 1:
            return False, notes
        notes.append(f"path-diff failed for {path}")
        return False, notes

    notes.append(f"changed paths match {base_branch}")
    return True, notes


def classify_entry(
    repo: Path,
    current_root: Path,
    primary_root: Path,
    policy_worktree_root: Path,
    base_branch: str,
    entry: dict[str, str],
) -> dict[str, str]:
    worktree_path = Path(entry["worktree"]).resolve()
    branch_ref = entry.get("branch", "")
    branch = branch_ref.removeprefix("refs/heads/") if branch_ref else "-"
    exists = worktree_path.exists()
    is_primary = worktree_path == primary_root
    is_current = worktree_path == current_root or path_contains(worktree_path, current_root)
    is_prunable = "prunable" in entry
    is_locked = "locked" in entry
    is_policy_path = worktree_path == primary_root or path_contains(policy_worktree_root, worktree_path)

    dirty = "?"
    base_status = "-"
    action = "inspect"
    notes: list[str] = []

    if not is_policy_path:
        notes.append("nonstandard-path")

    if is_primary:
        action = "keep"
        notes.append("primary")

    if is_current and action != "keep":
        action = "keep"
        notes.append("current")

    if is_prunable:
        action = "prune"
        dirty = "-"
        base_status = "-"
        details = entry["prunable"].strip()
        notes.append(details or "prunable")
        return build_row(worktree_path, branch, exists, dirty, base_status, action, notes)

    if not exists:
        notes.append("missing path")
        return build_row(worktree_path, branch, exists, dirty, base_status, action, notes)

    status = run_git(repo, "-C", str(worktree_path), "status", "--short", "--branch")
    if status.returncode != 0:
        notes.append("status failed")
        return build_row(worktree_path, branch, exists, dirty, base_status, action, notes)

    status_lines = [line for line in status.stdout.splitlines() if line.strip()]
    dirty = "yes" if len(status_lines) > 1 else "no"

    if dirty == "yes":
        notes.append("dirty")

    if branch == "-":
        base_status = "-"
        notes.append("detached")
    else:
        base_status, branch_notes = branch_base_status(repo, branch, base_branch)
        notes.extend(branch_notes)

    if is_locked:
        notes.append("locked")

    if action != "keep":
        if dirty == "yes":
            action = "keep"
        elif branch in protected_branches(base_branch):
            action = "keep"
            notes.append("protected-branch")
        elif is_locked or branch == "-" or base_status in {"ahead", "?"}:
            action = "keep"
        elif base_status in {"merged", "equivalent"}:
            action = "remove"

    if action == "remove":
        notes.append(f"clean branch already incorporated into {base_branch}")

    return build_row(worktree_path, branch, exists, dirty, base_status, action, notes)


def build_row(
    path: Path,
    branch: str,
    exists: bool,
    dirty: str,
    base_status: str,
    action: str,
    notes: list[str],
) -> dict[str, str]:
    return {
        "path": str(path),
        "branch": branch,
        "exists": "yes" if exists else "no",
        "dirty": dirty,
        "base_status": base_status,
        "action": action,
        "notes": ", ".join(dict.fromkeys(note for note in notes if note)) or "-",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory git worktrees and flag safe cleanup candidates.")
    parser.add_argument(
        "--base-branch",
        help="Override the branch used to decide whether worktree branches are already incorporated.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    current_root = resolve_current_worktree_root()
    primary_root = resolve_primary_workspace_root(current_root)
    policy_worktree_root = primary_root / ".worktrees"
    base_branch, base_source = select_base_branch(current_root, args.base_branch)

    raw = git_output(current_root, "worktree", "list", "--porcelain")
    entries = parse_worktrees(raw)
    rows = [
        classify_entry(
            current_root,
            current_root,
            primary_root,
            policy_worktree_root,
            base_branch,
            entry,
        )
        for entry in entries
    ]

    headers = ["ACTION", "DIRTY", "BASE_STATUS", "BRANCH", "PATH", "NOTES"]
    widths = {header: len(header) for header in headers}
    for row in rows:
        widths["ACTION"] = max(widths["ACTION"], len(row["action"]))
        widths["DIRTY"] = max(widths["DIRTY"], len(row["dirty"]))
        widths["BASE_STATUS"] = max(widths["BASE_STATUS"], len(row["base_status"]))
        widths["BRANCH"] = max(widths["BRANCH"], len(row["branch"]))
        widths["PATH"] = max(widths["PATH"], len(row["path"]))
        widths["NOTES"] = max(widths["NOTES"], len(row["notes"]))

    print(f"current_worktree: {current_root}")
    print(f"primary_workspace: {primary_root}")
    print(f"policy_worktree_root: {policy_worktree_root}")
    print(f"base_branch: {base_branch} ({base_source})")
    print()
    print(
        f"{headers[0]:<{widths['ACTION']}}  "
        f"{headers[1]:<{widths['DIRTY']}}  "
        f"{headers[2]:<{widths['BASE_STATUS']}}  "
        f"{headers[3]:<{widths['BRANCH']}}  "
        f"{headers[4]:<{widths['PATH']}}  "
        f"{headers[5]:<{widths['NOTES']}}"
    )
    for row in rows:
        print(
            f"{row['action']:<{widths['ACTION']}}  "
            f"{row['dirty']:<{widths['DIRTY']}}  "
            f"{row['base_status']:<{widths['BASE_STATUS']}}  "
            f"{row['branch']:<{widths['BRANCH']}}  "
            f"{row['path']:<{widths['PATH']}}  "
            f"{row['notes']:<{widths['NOTES']}}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
