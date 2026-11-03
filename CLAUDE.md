# plot_tool

A Python application that reads files containing time series and displays the data to the user.

## Requirements

The requirements below are loaded into every session. Follow them in all work.

@docs/requirements/README.md
@docs/requirements/code_and_organization.md
@docs/requirements/process_of_collaboration.md
@docs/requirements/high_level_functional_requirements.md
@docs/requirements/low_level_functional_requirements.md

## How to work in this repository

- Before any work, make sure a GitHub issue exists for it (PCR-00004, PCR-00012). Create it from the Fix or Feature template in `.github/ISSUE_TEMPLATE/` (PCR-00046). When creating it with `gh`, use the same sections as the template.
- Branch names must make the branch type and the issue explicit (PCR-00003, PCR-00005, PCR-00039). Project convention: create the branch from `develop` and name it `feature/<issue number>-<short-name>` or `fix/<issue number>-<short-name>`.
- Project convention: feature and fix pull requests go into `develop`.
- Pull requests from `develop` to `main` must follow PCR-00017 and PCR-00018 and need human approval (PCR-00015). Agents never merge into `main`.
- Before opening a pull request from `develop` to `main`, run the `requirement-validation` skill on every requirement created or changed since the last merge into `main`, fix what it finds through a fix issue, and put its result in the pull request under the heading "Requirement validation (PCR-00050)" (PCR-00050, PCR-00051).
- Before opening a pull request into `develop` from a branch that adds requirements, run the `requirement-validation` skill on the requirements it adds, and put its result in the pull request under the heading "Requirement validation (PCR-00052)" (PCR-00052, PCR-00053).
- The hook in `.claude/settings.json` and the `requirement-validation-section` CI job use `tests/check_requirement_review.py` to check that these results are there. They can't check that the review was good.
- Before opening a pull request: make the change, commit it, update the branch from `develop` (PCR-00060), run `python tests/build_test_matrix.py --require-qt --require-h5py --base develop --head HEAD`, commit `tests/test_matrix.md` (PCR-00061), and open the pull request only if it passed (PCR-00062). The hook in `.claude/settings.json` and the `tests` job check this with `tests/check_pr_ready.py`. CI also runs every test (PCR-00057, PCR-00058) and fails when an HLFR that the branch affects has no test (PCR-00059).
  - Only when PyQt6 or h5py can't be installed where you work (first try `pip install PyQt6 h5py`), add `--environment-limit`, optionally followed by a short text such as `"pypi.org is blocked in the cloud workspace"`. The tests skipped for that reason then show as `Fail*` with the missing capability, and count as passed (PCR-00063, PCR-00064, PCR-00071). A test that runs and fails, locally or in CI, is still a failure.
  - An HLFR whose implementation isn't done yet goes in `tests/not_implemented.txt`, one ID per line followed by the explanation (PCR-00066). Column 4 then shows `Fail*` (PCR-00065), and a pull request into `develop` may affect it with no test (PCR-00068). Remove it when the implementation is done (PCR-00067). A pull request from `develop` to `main` must have none (PCR-00069).
  - When the matrix shows any `Fail*`, the script prints a `## Fail* (PCR-00070)` section: paste it, unchanged, as the very first lines of the pull request description (PCR-00070). The `fail-star-section` CI job checks it.
- Do not merge your own work. A different agent or a human must review and test it first (PCR-00016).
- Before a pull request is merged, fill in the remaining sections of its issue, as listed in PCR-00006 (fixes) or PCR-00008 (features) (PCR-00014).
- Before opening a pull request that changes requirements, run `python tests/check_requirements.py` (PCR-00037). CI posts the result on the pull request (PCR-00038).
- Work in your own git worktree (PCR-00026).
