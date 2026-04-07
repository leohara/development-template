# Development Template

## Tooling

- `pnpm run build`: run the template build check (`type-check` in this repository)
- `pnpm run lint`: run `oxlint`
- `pnpm run lint:fix`: run `oxlint --fix`
- `pnpm run fmt`: run `oxfmt`
- `pnpm run fmt:check`: run `oxfmt --check`
- `pnpm run type-check`: run `tsc` without emitting files
- `pnpm run test`: run unit tests with `Vitest`
- `pnpm run test:unit:watch`: run `Vitest` in watch mode
- `pnpm run test:e2e`: run end-to-end tests with `Playwright`
- `pnpm run test:e2e:headed`: run `Playwright` in headed mode
- `pnpm run verify:code-change`: run the Codex `code-change-verification` wrapper (`lint`, `type-check`, `test`, `build`)

## Commits

- `Husky` runs a `commit-msg` hook that enforces Conventional Commits via `commitlint`.
- The hook is activated automatically when `pnpm install` runs the `prepare` script in a cloned or generated repository.
- If dependencies were installed with `--ignore-scripts`, `HUSKY=0`, or a similar script-skipping setup, run `pnpm run prepare` once to enable the hook.
- Use messages like `feat: add login form` or `chore(repo): enforce conventional commits`.

## Testing

- `Vitest` is configured for unit tests in `tests/unit`.
- `Playwright` is configured for end-to-end tests in `tests/e2e`.
- Install Playwright browser binaries on each machine with `pnpm exec playwright install`.

## Skills

- `code-change-verification`: run the repository verification stack from the task worktree or checkout that contains the diff, then hand off fresh results to PR creation.
- `codex-custom-rules`: create or update Codex execpolicy rules in `.codex/rules/custom.rules` and validate them with `codex execpolicy check`.
- `create-pr`: review the current change scope, run required checks, commit intentionally, push the branch, and open a pull request.
- `remove-unused-git-worktrees`: inventory registered worktrees and safely classify them for keep, remove, prune, or inspect.
- `using-git-worktrees`: create a dedicated task worktree under `.worktrees/` before editing, then hand off final verification to `code-change-verification`.

## License

MIT. See `LICENSE`.
