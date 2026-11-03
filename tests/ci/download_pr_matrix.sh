#!/usr/bin/env bash
# Downloads the test matrix built by the Tests run of the pull request
# that a commit on develop came from (PCR-00019, PCR-00022, PCR-00057).
# Used by .github/workflows/commit_matrix.yml.
#
# Usage: download_pr_matrix.sh <repository> <commit> <output folder>
#
# When the commit has no pull request or its matrix can't be found, the
# script gives a notice and exits 0 without a file, and
# commit_test_matrix.sh then has nothing to commit.
set -u

repository="$1"
commit_sha="$2"
output_folder="$3"

# A failed gh api prints its error to standard output, so its output is
# used only when it succeeds.
if ! head_sha="$(gh api "repos/$repository/commits/$commit_sha/pulls" \
    --jq '.[0].head.sha // empty')"; then
  head_sha=""
fi
if [ -z "$head_sha" ]; then
  echo "::notice title=Test matrix not found::$commit_sha has no pull request"
  exit 0
fi

run_id="$(gh run list --repo "$repository" --workflow tests.yml \
  --commit "$head_sha" --event pull_request --limit 1 \
  --json databaseId --jq '.[0].databaseId // empty')"
if [ -z "$run_id" ]; then
  echo "::notice title=Test matrix not found::no Tests run for $head_sha"
  exit 0
fi

if ! gh run download "$run_id" --repo "$repository" --name test-matrix \
    --dir "$output_folder"; then
  echo "::notice title=Test matrix not found::run $run_id has no test-matrix artifact"
fi
exit 0
