---
name: using-git-worktrees
description: Create a task-specific git worktree under `.worktrees/` at the repository root before making code changes. Treat the primary workspace as investigation-only, and create each new worktree from the default base branch using `<type>/<short-kebab-slug>`.
---

# Using Git Worktrees

## When To Apply

- Use this when you may touch files under Git control, such as implementation, refactoring, configuration changes, documentation updates, or edits under `.codex/`
- If you are already in the correct task worktree, continue there

## Required Rules

1. At the start, explicitly say `I'm using the using-git-worktrees skill to set up an isolated workspace.`
2. Use the primary workspace only for light investigation and adjustments. Do not perform editing work there.
3. Always create a new task worktree from the default base branch. Do not use the currently checked out feature branch or a temporary branch as the base.
4. For the base branch, prefer any explicit workflow rule defined by the repository. If none exists, determine it in this order: `origin/HEAD`, `main`, `develop`, `master`. If it still cannot be determined, specify it explicitly before continuing.
5. Create worktrees under `.worktrees/` at the repository root.
6. If `.worktrees/` is not ignored, update `.gitignore` before continuing.
7. If the repository has a wrapper command for worktree creation, use it first. Otherwise use this skill's `scripts/worktree-add.sh`.
8. If worktree creation, removal, or branch operations fail because of permissions, request escalation immediately and continue the process.

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
ls -d .worktrees 2>/dev/null || mkdir -p .worktrees
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

SKILL_SCRIPT="$(git rev-parse --show-toplevel)/.codex/skills/using-git-worktrees/scripts/worktree-add.sh"

# Prefer the repository's wrapper command if one exists
# Example: pnpm worktree:add -- --base "$BASE_BRANCH" "$BRANCH_NAME"

sh "$SKILL_SCRIPT" --base "$BASE_BRANCH" "$BRANCH_NAME"

cd ".worktrees/$WORKTREE_NAME"
```

### 5. Set Up The Worktree

- Run only the setup that is required, following the repository's standard procedure
- Examples: `pnpm install`, `npm install`, `bun install`, `cargo fetch`
- If it fails because of network restrictions, request escalation and rerun it

### 6. baseline verification

- Run one or more standard non-mutating checks for that repository
- Examples: `pnpm lint`, `pnpm test`, `pnpm typecheck`, `cargo test`, `go test ./...`
- Do not use mutating or long-running commands such as `format`, `db:migrate`, `seed`, or `dev` as baseline checks
- If a check fails because required environment variables or credentials are missing, state exactly which prerequisite is missing and decide whether to continue
- If you cannot find any executable baseline check, report that fact before proceeding

### 7. Report That The Setup Is Ready

```text
Worktree ready at <full-path>
Based on <base-branch>: <commit>
Verification: <commands or skipped with reason>
Ready to implement <task>
```

## If You Used The Wrong Base Branch

Confirm that the worktree is clean, then remove it and recreate it from the correct base branch.

```bash
BASE_BRANCH=main
SKILL_SCRIPT="$(git rev-parse --show-toplevel)/.codex/skills/using-git-worktrees/scripts/worktree-add.sh"

git -C ".worktrees/$WORKTREE_NAME" status --short
git worktree remove ".worktrees/$WORKTREE_NAME"
git branch -D "$BRANCH_NAME"
sh "$SKILL_SCRIPT" --base "$BASE_BRANCH" "$BRANCH_NAME"
```

## What Not To Do

- Create a task worktree from the currently checked out feature branch
- Edit directly in the primary workspace
- Skip checking whether `.worktrees/` is ignored
- Silently ignore a baseline failure
