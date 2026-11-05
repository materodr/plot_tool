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
- Before each push, run locally every test your environment can run, and push only when they pass (PCR-00082), for example with `python -m unittest discover -s tests -t .` (first try `pip install PyQt6 h5py`; where they can't be installed, the GUI and HDF5 tests skip locally and CI runs them).
- Review flow, for every pull request into `develop` (PCR-00088 to PCR-00098):
  1. The implementer makes the change, commits it, updates the branch from `develop` (PCR-00060) and runs the local tests.
  2. Before any pull request is opened, an independent reviewer (another agent) reviews the branch's code and requirements, running the `requirement-validation` judgement pass when requirements are new or changed. It adds tests focused on the problem the branch tackles, changing only files under `tests/`, never `src/`, and runs the local tests (PCR-00088 to PCR-00092).
  3. The reviewer sends its findings to the implementer. After the fixes, it checks only the changes (PCR-00093, PCR-00094).
  4. Only after the reviewer's green light is the pull request opened, and CI runs (PCR-00095).
  5. If CI passes, with no `Fail*` other than those declared in the Fail* section (into `develop` only), the reviewer merges it with no further review (PCR-00096). If CI fails, the branch goes back to the implementer, and the reviewer checks only the fix before CI runs again (PCR-00097).
  6. The reviewer checks every commit added after its green light, such as a merge of `develop` or a conflict fix, before it merges (PCR-00098).
  7. A release (`develop` to `main`) keeps PCR-00050, and the owner merges it.
- Before opening a pull request: don't commit `tests/test_matrix.md`; only the matrix pull requests of a release change it (PCR-00081). `python tests/build_test_matrix.py` writes `test_matrix_local.md`, which git ignores. If the branch changed the matrix, put it back with `git checkout origin/develop -- tests/test_matrix.md`. The hook in `.claude/settings.json` and the `tests` job check this with `tests/check_pr_ready.py`, and the hook also checks the Fail* section of a description given in a file.
  - CI runs every test on the pull request with PyQt6 and h5py, posts the matrix on it, and fails when a test fails (PCR-00062) or an HLFR that the branch affects has no test (PCR-00059). Pushes to `develop` and `main` run no test, only the requirement checks. Between releases, the matrix CI posts on each pull request is the record of that change (PCR-00019).
  - A pull request into `develop` that changes only files outside the list of PCR-00078 (for example only COR or PCR requirements, `CLAUDE.md` or skills), or only `tests/test_matrix.md`, runs no test (PCR-00079, PCR-00083). `python tests/ci_changed_files.py --base develop --head HEAD` tells which case applies. The requirement checks still run (PCR-00080). A pull request from `develop` into `main` always runs every test (PCR-00058).
  - Every pull request description starts with the `## Fail* (PCR-00070)` section. With no exception, its only entry is `- none`. The `fail-star-section` job checks it on every edit against `tests/not_implemented.txt` and the matrix the `tests` job posted for the head commit; the `tests` job checks only the environment `Fail*` of its own run.
  - An HLFR whose implementation isn't done yet goes in `tests/not_implemented.txt`, one ID per line followed by the explanation (PCR-00066). Column 4 then shows `Fail*` (PCR-00065), its entry goes in the Fail* section (`tests/build_test_matrix.py` prints it), and a pull request into `develop` may affect it with no test (PCR-00068). Remove it when the implementation is done (PCR-00067).
  - Only when PyQt6 or h5py can't be installed on the GitHub runner does the `tests` job add `--environment-limit`. The tests it couldn't run then show as `Fail*` and count as passed and as run, in a pull request into `develop` only (PCR-00063, PCR-00064, PCR-00071, PCR-00072). Add the entry from the posted matrix to the Fail* section; `fail-star-section` re-checks it on the edit. A test that runs and fails, locally or in CI, is still a failure.
  - A pull request from `develop` to `main` carries no `Fail*` of any kind (PCR-00069).
- After a release pull request is merged into `main` (PCR-00061, PCR-00084 to PCR-00087), the coordinator or an agent:
  1. downloads the `test-matrix` artifact of the release pull request's last `tests` run (`gh api "repos/materodr/plot_tool/actions/runs?head_sha=<head sha>"` gives the run id, then `gh run download <run id> -n test-matrix`);
  2. if that run failed, opens an issue that names the failed tests and stops (PCR-00086);
  3. otherwise creates `test-matrix/<release PR number>-main` from `main`, puts the artifact's `test_matrix_ci.md` in `tests/test_matrix.md`, commits, pushes and opens a pull request into `main` whose description starts with the Fail* section `- none`. The owner approves it as code owner and merges it;
  4. creates `test-matrix/<release PR number>-develop` from `develop` with the same file and opens a pull request into `develop`. Both skip the tests (PCR-00083), and an agent merges the develop one once its checks pass (PCR-00087).
- Send the owner your open questions about the app's behaviour before you open the pull request, each with the neighbouring cases it also settles, and gather the questions that come up while it is open for one push (PCR-00074 to PCR-00076). Give the owner the direct link of what he must approve or act on (PCR-00077).
- Do not merge your own work. A different agent or a human must review and test it first (PCR-00016), as in the review flow above.
- Before a pull request is merged, fill in the remaining sections of its issue, as listed in PCR-00006 (fixes) or PCR-00008 (features) (PCR-00014).
- Before opening a pull request that changes requirements, run `python tests/check_requirements.py` (PCR-00037). CI posts the result on the pull request (PCR-00038).
- Work in your own git worktree (PCR-00026).
