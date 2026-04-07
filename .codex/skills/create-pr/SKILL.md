---
name: create-pr
description: A skill for driving GitHub pull request creation. Handles change review, required checks, commit, push, and PR creation in one flow, and expects fresh verification evidence from `code-change-verification` when repository code changed.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
user-invocable: true
---

# Create PR

Handle the full sequence needed to create a GitHub pull request, from reviewing changes through creating the PR.

When the repository uses `code-change-verification`, treat that skill as the upstream verification gate for runtime, test, build, or UI-related changes.

## Relationship To code-change-verification

- Use `code-change-verification` before this skill when repository code, tests, build behavior, or visible UI changed.
- The expected input from that skill is: commands run, pass/fail outcomes, skipped checks with reasons, environment blockers, and manual verification evidence.
- Do not create a PR based on stale or assumed verification state.

## Workflow

### 1. Confirm scope

Start by checking the scope of the changes.

```bash
git status
git diff
```

If the change set is too broad, includes unintended diffs, or has unresolved conflicts, clean that up first.

### 2. Run required checks

Before committing, determine and run the checks required by this repository. Typical examples are format, lint, typecheck, and test.

- If there are project-specific steps, follow those first
- If this repository uses `code-change-verification`, prefer that skill's final pass and reuse its fresh verification summary here instead of inventing a new checklist ad hoc
- If any check fails, fix it before moving on
- Tell the user what you ran and what the outcome was
- If required verification has not been run yet for a code change, stop and run `code-change-verification` before committing or opening the PR

### 3. Stage and commit intentionally

Stage changes in a way that keeps the scope clear. Prefer explicit paths, and confirm the intended commit scope before proceeding when the change set is broad.

```bash
git add path/to/file1 path/to/file2
git commit -m "type(scope): short summary"
```

Choose the commit message using this priority order.

1. Explicit user instruction
2. Existing repository convention
3. Conventional Commits if there is no explicit convention

### 4. Push the branch

Check the current working branch name, then push that branch explicitly.

```bash
git branch --show-current
git push -u origin <branch-name>
```

Avoid ambiguous forms such as `git push`; always include the branch name.

### 5. Create the pull request

Before creating the PR, confirm the following.

- Whether the user specified a base branch
- Whether the repository has project-specific workflow rules
- Otherwise, what the repository default branch is
- If `.github/pull_request_template.md` exists, read it and reflect it in the body

Do not hardcode the base branch. If the user did not specify one, use the repository default branch. Only ask when the default branch cannot be determined, and explain why.

Do not embed a long PR body directly in CLI arguments; pass it through a temporary file.

```bash
cat <<'EOF' > /tmp/pr_body.md
<pull request body>
EOF

gh pr create --base <base-branch> --title "<pr-title>" --body-file /tmp/pr_body.md
```

Add `--draft` when needed. If there is no explicit instruction, decide whether draft is appropriate based on the readiness of the change.

After creation, return the PR URL, and include the title, base branch, and check results if useful.

## PR body guidance

If there is no template, the body should include at least the following.

- What changed
- Why it changed
- How it was verified, using the fresh summary from `code-change-verification` when applicable
- Any extra context reviewers should pay attention to

## Important notes

1. Do not skip the preparation steps
2. Do not ignore failing checks and continue to commit or PR creation
3. Always keep track of the staged scope and commit scope
4. Do not choose the base branch from a fixed value; follow user instruction or repository workflow
5. Prefer `--body-file` when passing the PR body
6. If something is unclear, ask the user and include the reasoning
7. When code changed, do not proceed on stale verification. Reuse the latest `code-change-verification` output or rerun it

## Error handling

- If a command fails, explain the cause and the next step concisely
- Use a sufficient timeout for long-running checks
- Use a body file so content containing characters such as `[]` does not break
- Before pushing or creating the PR, confirm that no unresolved problems remain
- If verification evidence is missing for a code change, the next step is to run `code-change-verification`, not to continue with the PR
