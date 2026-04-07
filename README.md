# Development Template

## Tooling

- `pnpm run lint`: run `oxlint`
- `pnpm run lint:fix`: run `oxlint --fix`
- `pnpm run fmt`: run `oxfmt`
- `pnpm run fmt:check`: run `oxfmt --check`
- `pnpm run test`: run unit tests with `Vitest`
- `pnpm run test:unit:watch`: run `Vitest` in watch mode
- `pnpm run test:e2e`: run end-to-end tests with `Playwright`
- `pnpm run test:e2e:headed`: run `Playwright` in headed mode

## Testing

- `Vitest` is configured for unit tests in `tests/unit`.
- `Playwright` is configured for end-to-end tests in `tests/e2e`.
- Install Playwright browser binaries on each machine with `pnpm exec playwright install`.
