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
- Before opening a pull request: make the change, commit it and update the branch from `develop` (PCR-00060). Don't commit `tests/test_matrix.md`: CI is its only builder (PCR-00061, PCR-00081). `python tests/build_test_matrix.py` writes `test_matrix_local.md`, which git ignores. If the branch changed the matrix, put it back with `git checkout origin/develop -- tests/test_matrix.md`. Push only after the local tests passed (PCR-00082). The hook in `.claude/settings.json` and the `tests` job check this with `tests/check_pr_ready.py`.
  - CI runs every test on the pull request with PyQt6 and h5py, posts the matrix on it, and fails when a test fails (PCR-00062) or an HLFR that the branch affects has no test (PCR-00059). CI commits no matrix to `develop`: after a release, it opens one pull request into `main` that changes only `tests/test_matrix.md`, which skips the tests (PCR-00083) and which the owner merges with his admin bypass (PCR-00084). The matrix comes back to `develop` with the next sync of `main`, which the check accepts (PCR-00081). Between releases, the matrix CI posts on each pull request is the record of that change (PCR-00019, PCR-00061).
  - A pull request into `develop` that changes only files outside the list of PCR-00078 (for example only COR or PCR requirements, `CLAUDE.md` or skills), and the push that merges it, run no test and keep the matrix as it is (PCR-00079). `python tests/ci_changed_files.py --base develop --head HEAD` tells which case applies. The requirement checks still run (PCR-00080). A pull request into `main` always runs every test (PCR-00058).
  - Every pull request description starts with the `## Fail* (PCR-00070)` section. With no exception, its only entry is `- none`. The `fail-star-section` job checks it against `tests/not_implemented.txt`, and the `tests` job against the matrix of its run.
  - An HLFR whose implementation isn't done yet goes in `tests/not_implemented.txt`, one ID per line followed by the explanation (PCR-00066). Column 4 then shows `Fail*` (PCR-00065), its entry goes in the Fail* section (`tests/build_test_matrix.py` prints it), and a pull request into `develop` may affect it with no test (PCR-00068). Remove it when the implementation is done (PCR-00067).
  - Only when PyQt6 or h5py can't be installed on the GitHub runner does the `tests` job add `--environment-limit`. The tests it couldn't run then show as `Fail*` and count as passed and as run, in a pull request into `develop` only (PCR-00063, PCR-00064, PCR-00071, PCR-00072). Add the entry from the posted matrix to the Fail* section and run the `tests` job again. A test that runs and fails, locally or in CI, is still a failure.
  - A pull request from `develop` to `main` carries no `Fail*` of any kind (PCR-00069).
- Send the owner your open questions about the app's behaviour before you open the pull request, each with the neighbouring cases it also settles, and gather the questions that come up while it is open for one push (PCR-00074 to PCR-00076). Give the owner the direct link of what he must approve or act on (PCR-00077).
- Do not merge your own work. A different agent or a human must review and test it first (PCR-00016).
- Before a pull request is merged, fill in the remaining sections of its issue, as listed in PCR-00006 (fixes) or PCR-00008 (features) (PCR-00014).
- Before opening a pull request that changes requirements, run `python tests/check_requirements.py` (PCR-00037). CI posts the result on the pull request (PCR-00038).
- Work in your own git worktree (PCR-00026).
