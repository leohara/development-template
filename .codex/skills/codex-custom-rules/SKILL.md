---
name: codex-custom-rules
description: "Create or update Codex execpolicy rules in `.codex/rules/custom.rules` for the current repository. Use this when you need to add `prefix_rule()` entries, adjust allow/prompt/forbidden policies, or validate the rules with `codex execpolicy check`."
---

# Codex Custom Rules

Use this skill when you need to add or update Codex command rules in `.codex/rules/custom.rules` for a repository.

Source of truth: https://developers.openai.com/codex/rules

## Workflow

1. Work in `.codex/rules/custom.rules`. If it does not exist, create both `.codex/rules/` and the file.
2. Write rules using Starlark `prefix_rule(...)`.
3. Make `pattern` match the exact argv prefix Codex will evaluate. Do not make patterns broader than necessary.
4. Every new or modified rule must include `pattern`, `decision`, `justification`, `match`, and `not_match`.
5. Treat `match` and `not_match` as inline tests. Include realistic examples that show both intended matches and close misses.
6. When `decision = "forbidden"`, include a safer alternative in `justification` when possible.
7. Unless the user explicitly asks for a full rewrite, preserve the existing repository-specific rules.
8. After validation, tell the user that Codex must be restarted for the updated rules to take effect.

## Pattern Rules

- `pattern` must be a non-empty list of argv tokens.
- Each position may be a literal string or a union list such as `["view", "list"]`.
- Prefix matching is exact. `["gh", "pr", "view"]` does not match `gh pr --repo openai/codex view 1`.
- If multiple rules match, the stricter decision wins: `forbidden` > `prompt` > `allow`.

## Shell Wrapper Caution

- Simple linear shell scripts joined with `&&`, `||`, `;`, or `|` may be split into multiple commands before rule evaluation.
- Do not assume splitting when the script includes redirection, substitution, environment variable assignment, wildcard expansion, or control flow.
- For more complex shell scripts, treat the full wrapper such as `["bash", "-lc", "<script>"]` as the match target.

## Mandatory Validation

Validation is mandatory. If you edit `.codex/rules/custom.rules`, do not consider the task complete until validation passes.

Run at least one parse check:

```sh
codex execpolicy check --pretty \
  --rules .codex/rules/custom.rules \
  -- git status
```

Then run focused checks for each changed rule using the `match` and `not_match` examples. For example:

```sh
codex execpolicy check --pretty \
  --rules .codex/rules/custom.rules \
  -- git worktree add .worktrees/test -b codex/test main

codex execpolicy check --pretty \
  --rules .codex/rules/custom.rules \
  -- git worktree remove --force .worktrees/test
```

If the rule file does not parse, or the result does not match the intended decision, fix it and run the checks again.

If you cannot run validation, explicitly report that the task is incomplete and explain why.

## Editing Guidance

- Prefer one rule block per permission concept.
- Prefer narrower prefixes or union lists over many nearly identical rules.
- Write `justification` as a human-readable sentence because Codex may show it in prompts or rejection messages.
- Do not add destructive `allow` rules unless the user explicitly requests them.
