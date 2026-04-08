#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f package.json ]]; then
  echo "package.json was not found in $ROOT_DIR"
  exit 1
fi

choose_script() {
  node - "$@" <<'NODE'
const fs = require('fs');

const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const scripts = pkg.scripts ?? {};
const candidates = process.argv.slice(2);

const match = candidates.find((name) =>
  Object.prototype.hasOwnProperty.call(scripts, name),
);

if (match) {
  process.stdout.write(match);
  process.exit(0);
}

process.exit(1);
NODE
}

run_check() {
  local label="$1"
  shift

  local selected_script
  if selected_script="$(choose_script "$@")"; then
    echo "::group::${label} (${selected_script})"
    pnpm run "$selected_script"
    echo "::endgroup::"
    return 0
  fi

  echo "Skipping ${label}: no matching package.json script found (${*})"
}

run_check "Lint" "lint:ci" "lint"
run_check "Format" "fmt:check" "format:check" "prettier:check" "check-format"
run_check "Type check" "type-check" "typecheck" "check-types" "type-check:ci"
run_check "Test" "test:ci" "test"
run_check "Build" "build:ci" "build"
