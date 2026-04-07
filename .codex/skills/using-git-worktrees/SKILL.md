---
name: using-git-worktrees
description: Create a task-specific git worktree under `.worktrees/` at the repository root before making code changes. Treat the primary workspace as investigation-only, create each new worktree from the default base branch using `<type>/<short-kebab-slug>`, and hand off final verification to `code-change-verification`.
---

# Using Git Worktrees

## When To Apply

- Use this when you may touch files under Git control, such as implementation, refactoring, configuration changes, documentation updates, or edits under `.codex/`
- Use this before `code-change-verification` when the task should run in its own isolated checkout
- If you are already in the correct task worktree, continue there

## Required Rules

1. At the start, explicitly say `I'm using the using-git-worktrees skill to set up an isolated workspace.`
2. Use the primary workspace only for light investigation and adjustments. Do not perform editing work there.
3. Always create a new task worktree from the default base branch. Do not use the currently checked out feature branch or a temporary branch as the base.
4. For the base branch, prefer any explicit workflow rule defined by the repository. If none exists, determine it in this order: `origin/HEAD`, `main`, `develop`, `master`. If it still cannot be determined, specify it explicitly before continuing.
5. Create worktrees under `.worktrees/` at the repository root.
6. If `.worktrees/` is not ignored, update `.gitignore` before continuing.
7. If the repository has a wrapper command for worktree creation, use it first. Otherwise use this skill's `scripts/worktree-add.sh`.
8. If this repository also uses `code-change-verification`, treat this skill as the setup phase and `code-change-verification` as the final verification gate for runtime, test, build, or UI-related changes.
9. Baseline verification in this skill only proves the new worktree is usable. It does not replace the final verification pass after implementation.
10. If worktree creation, removal, or branch operations fail because of permissions, request escalation immediately and continue the process.

## Relationship To code-change-verification

- This skill prepares the isolated checkout that downstream work should use.
- The expected handoff to `code-change-verification` is: worktree path, base branch, setup status, baseline verification results, and any environment blockers discovered during setup.
- After code changes exist in the task worktree, run `code-change-verification` there instead of returning to the primary workspace.

## Steps

### 1. Check Your Current Location

```bash
pwd
git branch --show-current
git worktree list
git status --short
```

### 2. Check That `.worktrees/` Exists And Is Ignored

```bash
# Run this from the repository root
mkdir -p .worktrees
git check-ignore -v .worktrees
```

### 3. Decide The Base Branch And Task Branch Name

- Check the repository workflow for the base branch. If no rule exists, determine it in this order: `origin/HEAD`, `main`, `develop`, `master`
- Use the format `<type>/<short-kebab-slug>`
- Valid `type` values are `feature`, `fix`, `refactor`, `chore`, `docs`, `test`
- Create the worktree directory name by replacing `/` in the branch name with `-`

### 4. Create The Worktree From The Base Branch

```bash
BASE_BRANCH=main
BRANCH_NAME=feature/example-task
WORKTREE_NAME="${BRANCH_NAME//\//-}"

# Prefer the repository's wrapper command if one exists
# Example: pnpm worktree:add -- --base "$BASE_BRANCH" "$BRANCH_NAME"

# Run this from the repository root
sh .codex/skills/using-git-worktrees/scripts/worktree-add.sh --base "$BASE_BRANCH" "$BRANCH_NAME"

cd ".worktrees/$WORKTREE_NAME"
```

### 5. Set Up The Worktree

- Run only the setup that is required, following the repository's standard procedure
- Examples: `pnpm install`, `npm install`, `bun install`, `cargo fetch`
- If it fails because of network restrictions, request escalation and rerun it

### 6. Baseline Verification

- Run one or more standard non-mutating checks for that repository
- Examples: `pnpm lint`, `pnpm test`, `pnpm typecheck`, `cargo test`, `go test ./...`
- Do not use mutating or long-running commands such as `format`, `db:migrate`, `seed`, or `dev` as baseline checks
- If a check fails because required environment variables or credentials are missing, state exactly which prerequisite is missing and decide whether to continue
- If you cannot find any executable baseline check, report that fact before proceeding
- If the task will continue into runtime, test, build, or UI changes, plan to rerun the final verification stack later with `code-change-verification` from this worktree

### 7. Report That The Setup Is Ready

```text
Worktree ready at <full-path>
Based on <base-branch>: <commit>
Verification: <commands or skipped with reason>
Final verification: run `code-change-verification` from this worktree before claiming completion
Ready to implement <task>
```

### 8. Hand Off To code-change-verification

- Keep implementation and final verification inside the same task worktree whenever possible.
- Use the baseline verification output from this skill only as setup evidence.
- Once the diff exists, invoke `code-change-verification` from the task worktree and report fresh results from that pass.

## If You Used The Wrong Base Branch

Confirm that the worktree is clean, then remove it and recreate it from the correct base branch with a fresh branch name. If you need to reuse the old branch name, handle that branch cleanup separately and explicitly.

For Codex command execution, do not use `git -C ...`. Set `workdir` to the target worktree and run plain `git` commands so the repository rules apply cleanly.

```bash
BASE_BRANCH=main
OLD_BRANCH_NAME=feature/example-task
OLD_WORKTREE_NAME="${OLD_BRANCH_NAME//\//-}"
NEW_BRANCH_NAME=feature/example-task-v2

# Run this with workdir set to ".worktrees/$OLD_WORKTREE_NAME"
git status --short
git worktree remove ".worktrees/$OLD_WORKTREE_NAME"

# Run this from the repository root
sh .codex/skills/using-git-worktrees/scripts/worktree-add.sh --base "$BASE_BRANCH" "$NEW_BRANCH_NAME"
```

## What Not To Do

- Create a task worktree from the currently checked out feature branch
- Edit directly in the primary workspace
- Skip checking whether `.worktrees/` is ignored
- Silently ignore a baseline failure
- Treat baseline verification as a replacement for `code-change-verification`
