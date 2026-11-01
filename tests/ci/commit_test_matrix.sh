#!/usr/bin/env bash
# Commits the test matrix built by a CI run on develop to develop
# (PCR-00019, PCR-00022). Used by .github/workflows/tests.yml.
#
# Usage: commit_test_matrix.sh <matrix file> <tested commit> <run id>
#
# Environment (optional): REMOTE (default origin), BRANCH (default
# develop), RETRY_DELAY_S (default 5), BOT_EMAIL (author email of the
# matrix commits).
#
# Only the run for the newest develop code commits its matrix: if the
# remote branch holds commits newer than the tested commit other than
# matrix commits of this bot, a newer run will commit its own matrix,
# so this run skips and exits 0.
#
# The matrix is never merged or rebased: each attempt checks out the
# fetched branch tip and writes this run's matrix over the file, so
# this run's matrix always wins over a matrix committed meanwhile by
# another run (a rebase with -X theirs would only take this run's side
# of the conflicting hunks and could keep lines of the other matrix).
set -u

matrix_path="$1"
tested_sha="$2"
run_id="$3"
remote="${REMOTE:-origin}"
branch="${BRANCH:-develop}"
retry_delay_s="${RETRY_DELAY_S:-5}"
bot_name="github-actions[bot]"
bot_email="${BOT_EMAIL:-41898282+github-actions[bot]@users.noreply.github.com}"
subject_prefix="Update test matrix from CI run"

if [ ! -f "$matrix_path" ]; then
  echo "No test matrix file at $matrix_path, nothing to commit."
  exit 0
fi
# The checkout below replaces the working tree, so keep a copy.
matrix_copy="$(mktemp)"
cp "$matrix_path" "$matrix_copy"

# The environment overrides git config, so set the identity there.
export GIT_AUTHOR_NAME="$bot_name" GIT_AUTHOR_EMAIL="$bot_email"
export GIT_COMMITTER_NAME="$bot_name" GIT_COMMITTER_EMAIL="$bot_email"

for attempt in 1 2 3; do
  if ! git fetch --quiet "$remote" "refs/heads/$branch"; then
    sleep "$retry_delay_s"
    continue
  fi
  tip_sha="$(git rev-parse FETCH_HEAD)"

  if ! git merge-base --is-ancestor "$tested_sha" "$tip_sha"; then
    echo "::notice title=Test matrix not committed::$branch no longer contains the tested commit $tested_sha"
    exit 0
  fi
  # Commits on the branch that this run did not test, other than
  # matrix commits of the bot.
  newer_code_list="$(git log --format='%H%x09%ae%x09%s' \
    "$tested_sha..$tip_sha" \
    | awk -F '\t' -v email="$bot_email" -v prefix="$subject_prefix" \
      '!($2 == email && index($3, prefix) == 1) { print $1 }')"
  if [ -n "$newer_code_list" ]; then
    echo "::notice title=Test matrix not committed::$branch has newer commits than $tested_sha; the run for the newest commit commits its matrix"
    exit 0
  fi

  git checkout --quiet --force --detach "$tip_sha"
  cp "$matrix_copy" tests/test_matrix.md
  if git diff --quiet -- tests/test_matrix.md; then
    echo "The test matrix on $branch is already up to date."
    exit 0
  fi
  git add tests/test_matrix.md
  git commit --quiet -m "$subject_prefix $run_id"
  if git push --quiet "$remote" "HEAD:refs/heads/$branch"; then
    echo "Test matrix committed to $branch."
    exit 0
  fi
  sleep "$retry_delay_s"
done

echo "::error title=Test matrix not committed::could not push tests/test_matrix.md to $branch"
exit 1
