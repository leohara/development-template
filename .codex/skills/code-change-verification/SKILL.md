---
name: code-change-verification
description: Run the mandatory verification stack when changes affect runtime code, tests, or build/test behavior in this repository.
---

# Code Change Verification

## Overview

Ensure work is only marked complete after the repository verification stack passes, or after a concrete environment blocker is reported. Use this skill when changes affect runtime code, tests, build behavior, lint/type-check behavior, or shared packages/modules consumed by the changed surface.

When a task changes user-facing UI behavior, verification also includes exercising the affected surface interactively before PR creation. Verify on the relevant target for the change, such as a local browser, simulator, device, or desktop runtime. Fresh verification evidence is required before claiming success.

Do not say work is complete, fixed, or passing based on expectation, stale output, or partial checks.

## Quick start

1. Keep this skill at `./.codex/skills/code-change-verification` so it loads automatically for this repository.
2. macOS/Linux: `bash .codex/skills/code-change-verification/scripts/run.sh`.
3. Windows: `powershell -ExecutionPolicy Bypass -File .codex/skills/code-change-verification/scripts/run.ps1`.
4. If the current checkout is missing dependencies, run the repository install command before verification, for example `pnpm install`.
5. If any command fails, fix the issue, rerun the script, and report the failing output.
6. Confirm completion only when all required commands succeed or when you have explicitly identified an environment blocker that is unrelated to the diff.

## Completion Gate

Before claiming the work is complete, fixed, or ready for merge/PR:

1. Run the full verification stack again from the current state.
2. Read the output and check the exit status of each command.
3. If the change affects user-facing UI, verify the changed flow manually on the affected platform and record what was exercised.
4. Report the result based on that fresh run, not on earlier confidence or partial checks.

Rules:

- `pnpm run lint` passing does not imply `pnpm run type-check`, `pnpm run test`, or `pnpm run build` pass.
- A subagent or prior tool report is not verification evidence by itself.
- If the task is a bug fix, also verify the original symptom is gone, ideally with a reproducing or regression test.
- For UI-related changes, automated checks alone are insufficient. Verify the changed surface on the relevant target/runtime unless the user explicitly waives that check or the environment blocks it.
- If you intentionally skip part of the stack for a narrow non-runtime change, say exactly what was skipped and why.
- `pnpm run build` can fail when required environment variables or setup are missing. Treat that as an environment blocker only when the failure is unrelated to the diff, and report the concrete missing variable, missing dependency, or error message.
- This skill only covers verification. After the final pass, continue with the repository's normal branch-finishing and PR workflow.
- Do not send the final completion message after verification alone when repository files changed if a required follow-up publish step is still pending.

## Manual workflow

- Run from the repository root in this order: `pnpm run lint`, `pnpm run type-check`, `pnpm run test`, and `pnpm run build`.
- Treat the stack as fail-fast and sequential.
- Do not skip steps; stop and fix issues immediately when any step fails.
- `pnpm run build` is required because it catches production build, bundling, prerender, and compile regressions that lint/type-check alone do not catch.
- If the diff affects visible UI behavior, run an interactive check after the command stack passes. Record the target and route/screen/flow you checked.
- Re-run the full stack after applying fixes so the commands execute against the same tree you report.
- Do not rely on earlier successful runs if the code changed afterward; rerun the stack from the latest tree before reporting success.

## Repository notes

- Each checkout or worktree may require its own installed dependencies before the first verification run.
- Keep mutating commands such as formatters or autofixers out of the read-only verification stack.
- If this repository uses different script names, update `scripts/run.mjs` so the default plan matches the actual verification commands before relying on the wrapper.
- If `build` fails because environment variables or local setup are incomplete, use the repository's setup docs or example env files as the reference for expected inputs.

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
