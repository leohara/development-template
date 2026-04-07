---
name: remove-unused-git-worktrees
description: Safely inventory registered git worktrees, distinguish removal candidates from prune candidates, auto-detect the base branch, and audit worktrees outside the standard layout without missing them.
---

# Remove Unused Git Worktrees

## Overview

Inventory all registered worktrees and classify them as `keep` / `remove` / `prune` / `inspect` according to the repo's safety rules.

The script auto-detects the base branch. The detection order is `origin/HEAD`, `main`, `develop`, `master`, then the current branch; if needed, specify it explicitly with `--base-branch`.

Include worktrees outside the standard `.worktrees/` layout in the inventory as well. However, even if the location is nonstandard, do not remove it unless it satisfies the automatic removal conditions.

Always state the following at the start.

`I'm using the remove-unused-git-worktrees skill to inspect and safely clean worktrees.`

## Safe Defaults

- Treat a worktree as `unused` only if all of the following are true:
  - the path exists
  - clean
  - it is not the primary workspace
  - it is not the worktree currently in use
  - it has already been incorporated into the base branch
- Consider a worktree already incorporated into the base branch if any of the following is true:
  - the branch tip is an ancestor of the base branch
  - the tree matches the base branch
  - it is patch-equivalent even if the history diverged because of a squash merge or similar
- Treat `prunable` entries and missing paths as targets for `git worktree prune`, and do not use `git worktree remove --force`
- Default dirty / detached / locked / unincorporated worktrees to keep
- Delete branches only when the user explicitly asks for it

## Workflow

### 1. Run From A Safe Workspace

- Do not remove the worktree currently in use
- If you are inside a candidate worktree, move back to the primary workspace or a worktree that will be kept before continuing

### 2. Take Inventory

Use the bundled script.

```bash
python3 .codex/skills/remove-unused-git-worktrees/scripts/worktree_inventory.py
```

If needed, you can specify the base branch explicitly.

```bash
python3 .codex/skills/remove-unused-git-worktrees/scripts/worktree_inventory.py --base-branch <branch-name>
```

The script outputs the following.

- current worktree
- primary workspace
- policy worktree root (`.worktrees/`)
- base branch used for incorporation checks
- `action`, `dirty`, `base_status`, `branch`, `path`, and `notes` for each worktree

`notes` also includes `nonstandard-path` for worktrees outside `.worktrees/`. Use it when auditing worktrees outside the standard layout.

### 3. Classification Rules

1. primary workspace: keep
2. current worktree: keep
3. `prunable`: prune
4. missing path / failed status lookup: inspect
5. dirty: keep
6. the base branch and long-lived branches such as `main` / `develop` / `master`: keep
7. clean and already incorporated into the base branch: remove
8. detached / locked / unincorporated: keep

### 4. Summarize Before Removing

Before removing anything, always organize the results into the following 4 groups.

- `remove`: clean and incorporated into the base branch
- `prune`: stale metadata
- `keep`: primary / current / dirty / protected / unincorporated
- `inspect`: requires human judgment

If the request is "clean up unused worktrees," you may show the summary and then proceed with only `remove` and `prune`. Otherwise, get explicit confirmation.

### 5. Remove Only Safe Candidates

```bash
git worktree remove <worktree-path>
```

- Do not use `--force` / `-f`
- Even if there are multiple candidates, remove them one at a time
- If removal is rejected because the worktree is dirty or locked, stop and report the reason

### 6. Prune Stale Metadata

```bash
git worktree prune
git worktree list
```

## Optional Branch Cleanup

Run this only if the request includes cleaning up branches as well.

```bash
git branch -d <branch>
```

- Use `git branch -D` only when there is explicit approval to discard unincorporated work

## Red Flags

**Never**

- Remove the primary workspace
- Remove the current worktree from inside itself
- `git worktree remove --force`
- Remove a dirty worktree without confirmation
- Treat an unincorporated worktree as unused just because the branch is old

**Always**

- Work from a workspace that will be kept
- Check `git status` for each candidate
- Report `remove` / `prune` / `keep` / `inspect` separately
- Re-run `git worktree list` after cleanup and show the remaining entries
