#!/usr/bin/env bash
# Helper to author a commit with a specific timestamp.
# Usage: tools/git_author.sh "YYYY-MM-DDTHH:MM:SS" "commit message"
set -euo pipefail

when="$1"
message="$2"

GIT_AUTHOR_DATE="$when" GIT_COMMITTER_DATE="$when" \
  git commit -q -m "$message"
