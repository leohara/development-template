#!/bin/sh

# Sync local .env files from the current workspace into the target worktree.
# Re-running this script against an existing worktree copies only missing files:
# identical files are left unchanged and divergent target files are skipped.

set -eu

usage() {
  echo "Usage: sh $0 [--base <base-branch>] [--] <branch-name>" >&2
  exit 1
}

resolve_base_branch() {
  requested_base="$1"
  remote_head=""

  if [ -n "$requested_base" ]; then
    if git show-ref --verify --quiet "refs/heads/$requested_base" ||
      git show-ref --verify --quiet "refs/remotes/origin/$requested_base"; then
      printf '%s\n' "$requested_base"
      return 0
    fi

    echo "Error: base branch $requested_base does not exist locally or on origin." >&2
    exit 1
  fi

  remote_head="$(git symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [ -n "$remote_head" ]; then
    remote_head=${remote_head#refs/remotes/origin/}
    if git show-ref --verify --quiet "refs/heads/$remote_head" ||
      git show-ref --verify --quiet "refs/remotes/origin/$remote_head"; then
      printf '%s\n' "$remote_head"
      return 0
    fi
  fi

  for candidate in main develop master; do
    if git show-ref --verify --quiet "refs/heads/$candidate" ||
      git show-ref --verify --quiet "refs/remotes/origin/$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  echo "Error: could not determine a base branch. Pass --base <branch-name> or set CODEX_WORKTREE_BASE_BRANCH." >&2
  exit 1
}

sync_local_env_files() {
  src_root="$1"
  dst_root="$2"
  sync_list_file="$(mktemp "${TMPDIR:-/tmp}/worktree-env-sync.XXXXXX")"

  if ! find "$src_root" \
    \( -name .git -o -name .worktrees -o -name node_modules -o -name .next -o -name .expo -o -name .turbo -o -name dist -o -name coverage \) -prune -o \
    -type f \( -name '.env' -o -name '.env.*' \) \
    ! -name '.env.example' \
    ! -name '.env.*.example' \
    -print > "$sync_list_file"; then
    rm -f "$sync_list_file"
    echo "failed to enumerate local env files under $src_root" >&2
    exit 1
  fi

  while IFS= read -r src_path || [ -n "$src_path" ]; do
    [ -n "$src_path" ] || continue

    rel_path=${src_path#"$src_root"/}
    dst_path="$dst_root/$rel_path"

    if [ -f "$dst_path" ]; then
      if cmp -s "$src_path" "$dst_path"; then
        printf 'unchanged: %s\n' "$rel_path" >&2
        continue
      fi

      printf 'skipped: %s differs in %s; keeping existing file\n' "$rel_path" "$dst_root" >&2
      continue
    fi

    mkdir -p "$(dirname "$dst_path")"

    if ! cp "$src_path" "$dst_path"; then
      rm -f "$sync_list_file"
      printf 'copy failed: %s\n' "$src_path" >&2
      exit 1
    fi

    printf 'copied: %s to %s\n' "$rel_path" "$dst_path" >&2
  done < "$sync_list_file"

  rm -f "$sync_list_file"
}

validate_registered_worktree() {
  target_path="$1"
  expected_common_dir="$2"
  resolved_common_dir=""

  if [ ! -d "$target_path" ]; then
    echo "Error: $target_path is registered as a git worktree but the directory is missing." >&2
    exit 1
  fi

  if [ ! -f "$target_path/.git" ]; then
    echo "Error: $target_path is registered as a git worktree but its .git file is missing." >&2
    exit 1
  fi

  if ! grep -Eq '^gitdir: ' "$target_path/.git"; then
    echo "Error: $target_path is registered as a git worktree but its .git file is malformed." >&2
    exit 1
  fi

  if ! (
    cd "$target_path" &&
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 &&
    git rev-parse --git-dir >/dev/null 2>&1
  ); then
    echo "Error: $target_path is registered as a git worktree but is not usable. Remove or prune the broken worktree before retrying." >&2
    exit 1
  fi

  resolved_common_dir="$(git -C "$target_path" rev-parse --git-common-dir 2>/dev/null || true)"
  case "$resolved_common_dir" in
    "")
      echo "Error: $target_path is registered as a git worktree but its common git dir cannot be resolved." >&2
      exit 1
      ;;
    /*) ;;
    *) resolved_common_dir="$target_path/$resolved_common_dir" ;;
  esac

  if ! resolved_common_dir="$(cd "$resolved_common_dir" && pwd)"; then
    echo "Error: $target_path is registered as a git worktree but its common git dir cannot be resolved." >&2
    exit 1
  fi

  if [ "$resolved_common_dir" != "$expected_common_dir" ]; then
    echo "Error: $target_path is registered as a git worktree but resolves to a different repository root ($resolved_common_dir)." >&2
    exit 1
  fi
}

base_branch="${CODEX_WORKTREE_BASE_BRANCH-}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base)
      [ "${2-}" != "" ] || usage
      base_branch="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -*)
      usage
      ;;
    *)
      break
      ;;
  esac
done

[ "$#" -eq 1 ] || usage

branch_name="$1"
base_branch="$(resolve_base_branch "$base_branch")"
current_root="$(git rev-parse --show-toplevel)"
common_dir_raw="$(git rev-parse --git-common-dir)"

case "$common_dir_raw" in
  /*) common_dir="$common_dir_raw" ;;
  *) common_dir="$current_root/$common_dir_raw" ;;
esac

common_dir="$(cd "$common_dir" && pwd)"
repo_root="$(cd "$common_dir/.." && pwd)"
worktree_root="$repo_root/.worktrees"
worktree_name="$(printf '%s' "$branch_name" | tr '/' '-')"
target_path="$worktree_root/$worktree_name"

mkdir -p "$worktree_root"

if [ "$current_root" = "$target_path" ]; then
  printf '%s\n' "$target_path"
  exit 0
fi

if git worktree list --porcelain | awk '/^worktree / { print substr($0, 10) }' | grep -Fx -- "$target_path" >/dev/null 2>&1; then
  validate_registered_worktree "$target_path" "$common_dir"
  sync_local_env_files "$current_root" "$target_path"
  printf '%s\n' "$target_path"
  exit 0
fi

if [ -e "$target_path" ]; then
  echo "Error: $target_path already exists but is not a registered git worktree." >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/heads/$branch_name"; then
  git worktree add "$target_path" "$branch_name" >&2
elif git show-ref --verify --quiet "refs/remotes/origin/$branch_name"; then
  git worktree add --track -b "$branch_name" "$target_path" "origin/$branch_name" >&2
else
  if git show-ref --verify --quiet "refs/heads/$base_branch"; then
    git worktree add -b "$branch_name" "$target_path" "$base_branch" >&2
  else
    git worktree add -b "$branch_name" "$target_path" "origin/$base_branch" >&2
  fi
fi

sync_local_env_files "$current_root" "$target_path"

printf '%s\n' "$target_path"
