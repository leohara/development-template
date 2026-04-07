---
name: code-change-verification
description: Run the mandatory verification stack for code changes from the task worktree or checkout that contains the diff, then hand off fresh results to `create-pr`.
---

# Code Change Verification

## Overview

Ensure work is only marked complete after the repository verification stack passes, or after a concrete environment blocker is reported. Use this skill when changes affect runtime code, tests, build behavior, lint/type-check behavior, or shared packages/modules consumed by the changed surface.

When a task changes user-facing UI behavior, verification also includes exercising the affected surface interactively before PR creation. Verify on the relevant target for the change, such as a local browser, simulator, device, or desktop runtime. Fresh verification evidence is required before claiming success.

Do not say work is complete, fixed, or passing based on expectation, stale output, or partial checks.

In repositories that use `using-git-worktrees`, this skill is normally the downstream completion gate. The expected input is a dedicated task worktree with dependencies installed and the intended diff already present.

When the repository also uses `create-pr`, this skill is the preferred upstream verification gate before commit, push, and PR creation.

## Relationship To using-git-worktrees

- Use `using-git-worktrees` first when the task should be isolated in its own checkout.
- The expected handoff from that skill is: worktree path, base branch, setup status, baseline verification results, and any setup blockers.
- Baseline verification from `using-git-worktrees` is setup evidence only. It does not replace the final pass from this skill after the code changes.

## Relationship To create-pr

- Use `create-pr` after this skill when the task is ready to be committed and opened for review.
- The expected handoff to `create-pr` is: the exact commands run, pass/fail outcomes, any skipped checks with reasons, any environment blockers, and any manual verification evidence.
- `create-pr` should rely on fresh results from this skill, not on assumptions that checks probably pass.

## Quick start

1. Keep this skill at `./.codex/skills/code-change-verification` so it loads automatically for this repository.
2. If this repository uses `using-git-worktrees`, change into the dedicated task worktree before running final verification. Do not run the final pass from the primary workspace when the diff lives in another checkout.
3. macOS/Linux: `bash .codex/skills/code-change-verification/scripts/run.sh`.
4. Windows: `powershell -ExecutionPolicy Bypass -File .codex/skills/code-change-verification/scripts/run.ps1`.
5. If the current checkout is missing dependencies, run the repository install command before verification, for example `pnpm install`.
6. If any command fails, fix the issue, rerun the script, and report the failing output.
7. Confirm completion only when all required commands succeed or when you have explicitly identified an environment blocker that is unrelated to the diff.

## Completion Gate

Before claiming the work is complete, fixed, or ready for merge/PR:

1. Run the full verification stack again from the current state.
2. Read the output and check the exit status of each command.
3. If the change affects user-facing UI, verify the changed flow manually on the affected platform and record what was exercised.
4. Report the result based on that fresh run, not on earlier confidence or partial checks.

Rules:

- `pnpm run lint` passing does not imply `pnpm run type-check`, `pnpm run test`, or `pnpm run build` pass.
- If the repository uses `using-git-worktrees`, run this skill from the dedicated task worktree that contains the diff.
- If you realize the task should have been isolated but you are still in the primary workspace before editing, stop and invoke `using-git-worktrees` first.
- Do not treat baseline checks from `using-git-worktrees` as final verification evidence after the code changed.
- A subagent or prior tool report is not verification evidence by itself.
- If the task is a bug fix, also verify the original symptom is gone, ideally with a reproducing or regression test.
- For UI-related changes, automated checks alone are insufficient. Verify the changed surface on the relevant target/runtime unless the user explicitly waives that check or the environment blocks it.
- If you intentionally skip part of the stack for a narrow non-runtime change, say exactly what was skipped and why.
- `pnpm run build` can fail when required environment variables or setup are missing. Treat that as an environment blocker only when the failure is unrelated to the diff, and report the concrete missing variable, missing dependency, or error message.
- This skill only covers verification. After the final pass, continue with the repository's normal branch-finishing and PR workflow.
- If the repository uses `create-pr`, pass the final verification summary forward so the PR body can report how the change was verified.
- Do not send the final completion message after verification alone when repository files changed if a required follow-up publish step is still pending.

## Manual workflow

- Run from the repository root of the task worktree or checkout that contains the diff in this order: `pnpm run lint`, `pnpm run type-check`, `pnpm run test`, and `pnpm run build`.
- Treat the stack as fail-fast and sequential.
- Do not skip steps; stop and fix issues immediately when any step fails.
- `pnpm run build` is required because it catches production build, bundling, prerender, and compile regressions that lint/type-check alone do not catch.
- If the diff affects visible UI behavior, run an interactive check after the command stack passes. Record the target and route/screen/flow you checked.
- Re-run the full stack after applying fixes so the commands execute against the same tree you report.
- Do not rely on earlier successful runs if the code changed afterward; rerun the stack from the latest tree before reporting success.
- If the next step is PR creation, prepare a concise verification summary that `create-pr` can reuse directly.

## Repository notes

- Each checkout or worktree may require its own installed dependencies before the first verification run.
- If `using-git-worktrees` was used earlier, its baseline checks are only a preflight for the new checkout. Re-run the full stack here after implementation.
- Keep mutating commands such as formatters or autofixers out of the read-only verification stack.
- If this repository uses different script names, update `scripts/run.mjs` so the default plan matches the actual verification commands before relying on the wrapper.
- If `build` fails because environment variables or local setup are incomplete, use the repository's setup docs or example env files as the reference for expected inputs.

## Handoff Output

Report the final verification state in a form that downstream PR creation can reuse.

```text
Verification checkout: <path>
Commands: <each command in order>
Result: <pass or fail>
Skipped: <none or exact skipped checks with reasons>
Manual verification: <none or exact target/flow checked>
Blockers: <none or exact blocker>
Next step: use `create-pr` with this verification summary
```

## Resources

### scripts/run.mjs

- Defines the default verification plan and fail-fast runner for this repository.
- The template default plan is `lint`, `type-check`, `test`, and `build`; customize it to match the repository's actual scripts when bootstrapping a new project.
- Uses the Node runner so macOS/Linux execution stays aligned with the Windows wrapper.
- Prefer this entry point to ensure the commands always run from the repo root with the expected order.

### scripts/run.sh

- macOS/Linux wrapper for the Node-based verification runner.
- Use this entry point to execute the configured verification plan from the repository root.

### scripts/run.ps1

- Windows-friendly wrapper that runs the same verification sequence with fail-fast semantics.
- Use from PowerShell with execution policy bypass if required by your environment.
