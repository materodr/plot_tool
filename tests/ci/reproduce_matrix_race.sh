#!/usr/bin/env bash
# Reproduces the race of two CI runs committing tests/test_matrix.md to
# develop (issue #81) in a throwaway bare repository, and checks
# tests/ci/commit_test_matrix.sh against it.
#
# Usage: bash tests/ci/reproduce_matrix_race.sh [work folder]
# Prints PASS or FAIL for each scenario and exits 1 if any failed.
set -u

script_path="$(cd "$(dirname "$0")" && pwd)/commit_test_matrix.sh"
work_path="${1:-$(mktemp -d)}"
rm -rf "$work_path"
mkdir -p "$work_path"
cd "$work_path" || exit 1
export RETRY_DELAY_S=0
export GIT_AUTHOR_NAME=dev GIT_AUTHOR_EMAIL=dev@example.com
export GIT_COMMITTER_NAME=dev GIT_COMMITTER_EMAIL=dev@example.com
failures=0

check() {
  # check <scenario name> <command...>: PASS when the command succeeds.
  name="$1"
  shift
  if "$@"; then
    echo "PASS: $name"
  else
    echo "FAIL: $name"
    failures=$((failures + 1))
  fi
}

# Remote with develop at: base, code commit 1 (sha1), code commit 2
# (sha2). Each "run" is a clone checked out at the commit it tested.
setup_remote() {
  rm -rf origin.git seed run_a run_b
  git init --quiet --bare -b develop origin.git
  git clone --quiet origin.git seed 2> /dev/null
  cd seed || exit 1
  git checkout --quiet -b develop
  mkdir -p tests
  printf 'line 1 old\nline 2 old\nline 3 old\n' > tests/test_matrix.md
  echo base > code.txt
  git add . && git commit --quiet -m base
  echo one >> code.txt && git commit --quiet -am "Merge pull request #1"
  sha1="$(git rev-parse HEAD)"
  echo two >> code.txt && git commit --quiet -am "Merge pull request #2"
  sha2="$(git rev-parse HEAD)"
  git push --quiet origin develop
  cd ..
  git clone --quiet origin.git run_a && git -C run_a checkout --quiet --detach "$sha2"
  git clone --quiet origin.git run_b && git -C run_b checkout --quiet --detach "$sha2"
}

remote_matrix() {
  git --git-dir=origin.git show develop:tests/test_matrix.md
}

# Run A and run B both tested sha2 and built different matrices (they
# differ in different lines, as runs with different results do).
printf 'line 1 run A\nline 2 old\nline 3 old\n' > matrix_a.md
printf 'line 1 old\nline 2 run B\nline 3 run B\n' > matrix_b.md

# Scenario 1: the old workflow step fails on the second run.
setup_remote
(cd run_a && bash "$script_path" ../matrix_a.md "$sha2" 1 > /dev/null)
old_step_failed() {
  (
    cd run_b || exit 1
    cp ../matrix_b.md tests/test_matrix.md
    git -c user.name=bot -c user.email=bot@example.com \
      commit --quiet -am "Update test matrix from CI run 2"
    for attempt in 1 2 3; do
      if git pull --quiet --rebase origin develop > /dev/null 2>&1 \
        && git push --quiet origin HEAD:develop 2> /dev/null; then
        exit 1
      fi
      git rebase --abort 2> /dev/null
    done
    exit 0
  )
}
check "old step: second run cannot commit (bug reproduced)" old_step_failed

# Scenario 2: with the script, the second run commits its own matrix
# on top of the first run's matrix commit.
setup_remote
(cd run_a && bash "$script_path" ../matrix_a.md "$sha2" 1 > /dev/null)
second_run_wins() {
  (cd run_b && bash "$script_path" ../matrix_b.md "$sha2" 2) || return 1
  [ "$(remote_matrix)" = "$(cat matrix_b.md)" ] || return 1
  [ "$(git --git-dir=origin.git log -1 --format=%s develop)" \
    = "Update test matrix from CI run 2" ] || return 1
  [ "$(git --git-dir=origin.git rev-list --count "$sha2..develop")" = 2 ]
}
check "script: second run's matrix wins, both matrix commits kept" second_run_wins

# Scenario 3: a run for older code skips when develop has newer code.
setup_remote
git -C run_a checkout --quiet --detach "$sha1"
older_run_skips() {
  output_str="$(cd run_a && bash "$script_path" ../matrix_a.md "$sha1" 3)" \
    || return 1
  echo "$output_str"
  echo "$output_str" | grep -q '::notice title=Test matrix not committed' \
    || return 1
  [ "$(git --git-dir=origin.git rev-parse develop)" = "$sha2" ]
}
check "script: older run skips when develop has newer code" older_run_skips

# Scenario 4: same as 3 when the newer code is followed by a matrix
# commit of the bot.
setup_remote
(cd run_b && bash "$script_path" ../matrix_b.md "$sha2" 4 > /dev/null)
git -C run_a checkout --quiet --detach "$sha1"
older_run_skips_after_bot() {
  tip_before="$(git --git-dir=origin.git rev-parse develop)"
  (cd run_a && bash "$script_path" ../matrix_a.md "$sha1" 5) || return 1
  [ "$(git --git-dir=origin.git rev-parse develop)" = "$tip_before" ]
}
check "script: older run skips past a newer bot matrix commit" older_run_skips_after_bot

# Scenario 5: an unchanged matrix makes no commit.
setup_remote
(cd run_a && bash "$script_path" ../matrix_a.md "$sha2" 6 > /dev/null)
unchanged_no_commit() {
  tip_before="$(git --git-dir=origin.git rev-parse develop)"
  (cd run_b && bash "$script_path" ../matrix_a.md "$sha2" 7) || return 1
  [ "$(git --git-dir=origin.git rev-parse develop)" = "$tip_before" ]
}
check "script: unchanged matrix makes no commit" unchanged_no_commit

# Scenario 6: a push that keeps failing ends with the error annotation.
setup_remote
printf '#!/bin/sh\nexit 1\n' > origin.git/hooks/pre-receive
chmod +x origin.git/hooks/pre-receive
push_failure_annotated() {
  output_str="$(cd run_b && bash "$script_path" ../matrix_b.md "$sha2" 8 2> /dev/null)" \
    && return 1
  echo "$output_str"
  echo "$output_str" | grep -q '::error title=Test matrix not committed'
}
check "script: lasting push failure fails with the error annotation" push_failure_annotated

if [ "$failures" -ne 0 ]; then
  echo "$failures scenario(s) failed"
  exit 1
fi
echo "All scenarios passed"
