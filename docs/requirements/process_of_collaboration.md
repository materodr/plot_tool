# Process of Collaboration Requirements

Prefix: `PCR`. Format rules: see [README.md](README.md).

### PCR-00001 Repository host
The project must be kept in a GitHub repository.

### PCR-00002 Branch types
The repository must use the following branch types:
1. a permanent `main` branch;
2. a permanent `develop` branch;
3. feature branches, created as needed;
4. fix branches, created as needed;
5. test matrix branches, which an agent creates after each release (PCR-00061, PCR-00085).

Note: A test matrix branch is named `test-matrix/<release pull request number>-main` or `test-matrix/<release pull request number>-develop`. It isn't a feature or a fix, so it has no issue (PCR-00004, PCR-00005, PCR-00014).

### PCR-00003 Branch names
The name of each branch must clearly refer to one of the allowed branch types.

### PCR-00004 Issue for every change
A GitHub issue must be created to track the development of every fix and new feature.

### PCR-00046 Issue templates
Every issue must be created from one of the two templates: [Fix](../../.github/ISSUE_TEMPLATE/fix.yml) or [Feature](../../.github/ISSUE_TEMPLATE/feature.yml).

### PCR-00005 Branch linked to an issue
Feature and fix branches must always be created pointing to an issue.

### PCR-00039 Issue in the branch name
The issue that a feature or fix branch points to (PCR-00005) must be explicit in the branch name.

### PCR-00006 Fix issue contents
A fix issue must contain:
1. a description of the bug;
2. the severity of the bug;
3. a step-by-step description of how to reproduce the bug;
4. the solution;
5. how the solution was tested;
6. the evidence that the solution actually solves the bug.

### PCR-00007 Bug severity levels
The severity of a bug must be classified as low, medium or high.

### PCR-00008 Feature issue contents
A feature issue must contain:
1. a description of the feature;
2. why the app needs it;
3. the urgency of the implementation;
4. how the implementation was done;
5. which tests were used to check that the implementation fulfils the feature;
6. the evidence that it does.

### PCR-00009 Feature urgency levels
The urgency of a feature must be classified as low, medium or high.

### PCR-00010 Work priority of features
Priority of work must be given to feature issues with higher urgency.

### PCR-00040 Work priority of fixes
Priority of work must be given to fix issues with higher severity.

### PCR-00011 Fixes before features
Between a feature of high urgency and a fix of high severity, the fix of high severity must have priority.

### PCR-00012 Issue before work
A feature or fix must only start to be tackled when the issue that tracks it has already been created.

### PCR-00013 Correlated bugs found during work
If a new bug is found while creating a feature or fixing a bug, and the bug is correlated with the ongoing work, it must be fixed under the same issue.

### PCR-00041 Uncorrelated bugs found during work
If a new bug is found while creating a feature or fixing a bug, and the bug is not correlated with the ongoing work, a new issue must be opened.

### PCR-00074 Edge cases in owner questions
When an agent asks the owner to decide a rule, it must list, in the same question, the neighbouring cases that the decision also settles.

Note: For example, a question about what a click over one kind of object does also names clicks over name labels and double-clicks on that object.

### PCR-00075 Questions before the pull request
An implementer agent must send its open questions about the app's behaviour to the owner before it opens its pull request.

Note: Every push to a pull request that changes a file of PCR-00078 runs the whole test suite again, so an answer given after the PR is open costs one more full CI run.

### PCR-00076 Questions gathered for one push
When questions about the app's behaviour come up while a pull request is open, the agent must send them to the owner together, so that his answers go into one push.

### PCR-00077 Direct link for the owner
When the owner needs to approve or act on something, the agent must give him its direct link.

### PCR-00014 Pull request preconditions
A pull request must only be merged if its issue has all the information required by PCR-00006 (fixes) or PCR-00008 (features), except as in PCR-00084 and PCR-00087.

### PCR-00015 Human approval for main
Pull requests into `main` must be approved by humans.

### PCR-00016 Agent merges
An AI agent must only merge a pull request into a branch other than `main` after an agent different from the one that did the implementation has reviewed and tested it independently, except as in PCR-00087.

Note: The review happens before the pull request is opened and before CI runs (PCR-00088 to PCR-00098).

### PCR-00017 Issue list for develop to main
A pull request from `develop` to `main` must list all the issues that track the code changes since the last merge into `main`.

Note: "The last merge into `main`" means the merge of the last release pull request, not the merge of a matrix pull request (PCR-00061).

### PCR-00018 Evidence for develop to main
A pull request from `develop` to `main` must show evidence that the code fulfils all the functional requirements.

Note: The evidence is the test matrix that CI builds on the release pull request and posts on it (PCR-00058, PCR-00061), with no `Fail*` (PCR-00069).

### PCR-00050 Requirements review before develop to main
Before a pull request from `develop` to `main` is opened, the requirements review of the `requirement-validation` skill must be run on every requirement created or changed since the last merge into `main`.

Note: "The last merge into `main`" means the merge of the last release pull request, not the merge of a matrix pull request (PCR-00061). A release keeps this review and its independent check before the release pull request is opened, and the owner merges it (PCR-00015).

### PCR-00051 Requirements review result for develop to main
A pull request from `develop` to `main` must show the result of the requirements review of PCR-00050.

### PCR-00052 Requirements review before a pull request into develop
Before a pull request into `develop` is opened, the requirements review of the `requirement-validation` skill must be run on every requirement that its branch adds.

Note: A branch that adds no requirement has nothing to review, so its pull request has no result to show (PCR-00053).

### PCR-00053 Requirements review result for a pull request into develop
A pull request into `develop` whose branch adds a requirement must show the result of the requirements review of PCR-00052.

### PCR-00019 Test matrix
A table named test matrix must be permanently kept in the `tests` folder.

Note: The file is `tests/test_matrix.md`. It is updated once per release, in `main` and in `develop`, by the matrix pull requests of PCR-00061 and PCR-00085. Between releases, the matrix that CI posts on each pull request is the record of that change.

### PCR-00020 Test matrix column 1
The first column of the test matrix must contain the current set of high-level functional requirements (HLFR).

### PCR-00021 Test matrix column 2
The second column must show, for each HLFR, its child low-level functional requirements (LLFR).

### PCR-00022 Test matrix column 3
The third column must contain the tests linked to each HLFR and the last run status of each test, as passed or failed, except as in PCR-00063.

### PCR-00063 Fail* for an environment limit
The third column of the test matrix must show `Fail*`, followed by a justification that names the missing capability, for each test that could not run because the environment that ran the tests lacked that capability.

Note: For example, PyQt6 or h5py can't be installed in the cloud workspace. `python tests/build_test_matrix.py --environment-limit` writes these cells. A test that runs and fails, locally or on GitHub, is a failed test, not a `Fail*`.

### PCR-00023 Test matrix column 4
The fourth column must contain "pass" if all tests of the HLFR passed, except as in PCR-00065 and PCR-00071.

Note: Besides "pass", the fourth column can show "fail" (PCR-00042), a `Fail*` (PCR-00065, PCR-00071), or "no tests" and "not run" as `tests/build_test_matrix.py` explains.

### PCR-00042 Test matrix column 4 on a failure
The fourth column of the test matrix must contain "fail" if at least one test of the HLFR failed.

### PCR-00065 Fail* for an HLFR not implemented yet
The fourth column of the test matrix must show `Fail*`, followed by the explanation that the implementation has not been done yet, for each HLFR listed in `tests/not_implemented.txt` (PCR-00066), except as in PCR-00042.

### PCR-00071 Fail* in the fourth column for an environment limit
The fourth column of the test matrix must show `Fail*`, followed by the missing capabilities, for an HLFR that has a test shown with the `Fail*` of PCR-00063, except as in PCR-00042 and PCR-00065.

### PCR-00024 Test coverage
Agents must write tests that robustly cover every aspect of the high-level functional requirements.

### PCR-00057 Tests of a pull request into develop
A pull request into `develop` must run every test, except as in PCR-00072, PCR-00079 and PCR-00083.

### PCR-00058 Tests of a pull request into main
A pull request from `develop` to `main` must run every test.

Note: An environment `Fail*` counts as run only into `develop` (PCR-00072), so a release pull request whose run had one fails (PCR-00069).

### PCR-00072 Environment Fail* counts as run
For PCR-00057, a test shown with the `Fail*` of PCR-00063 must count as run, also when the run on GitHub could not run it either.

Note: The `tests` CI job adds `--environment-limit` only when installing PyQt6 or h5py fails on the runner, with a justification that names the failed install. A test that runs and fails still fails the job. An environment `Fail*` is accepted into `develop` only: a pull request into `main` carries no `Fail*` (PCR-00069).

### PCR-00078 Every test for code and functional requirement changes
A pull request into `develop` must run every test when its branch changes a file under `src/`, `tests/`, `bin/` or `.github/workflows/`, a build script (`build_executable.py`, `rebuild_and_launch.py`), a `requirements*.txt` file, or the HLFR or LLFR file.

Note: The branch is compared with its base branch. The sample files of PCR-00032 are under `tests/`. A renamed file counts with its old and its new path, and a deleted file counts too. A pull request from `develop` to `main` always runs every test (PCR-00058). A push to `develop` or `main` runs no test: the run of the pull request already tested the merged code, because its branch was up to date (PCR-00060). In the `tests` CI job, `tests/ci_changed_files.py` makes the decision, and only an explicit decision to skip skips. This follows the owner's decisions of 2026-11-05.

### PCR-00079 Tests skipped for other changes
A pull request into `develop` whose branch changes only files outside the list of PCR-00078 must skip the run of the tests.

Note: For example, a branch that changes only the COR or PCR requirements, `docs/requirements/README.md`, `CLAUDE.md` or the skills in `.claude/skills/`. The `tests` job then skips its test steps and still reports success, so that the required check doesn't block the merge. It still checks PEP 8 and runs the checks of `tests/check_pr_ready.py` that need no test run.

### PCR-00080 Requirement checks on every pull request
Every pull request into `develop` or `main` must run the requirements quality test (PCR-00037) and the `requirement-validation-section` and `fail-star-section` checks, also when it skips the tests (PCR-00079, PCR-00083).

### PCR-00081 Test matrix left as develop has it
The branch of a pull request into `develop`, other than a test matrix branch (PCR-00085), must leave `tests/test_matrix.md` as `develop` has it.

Note: Only the matrix pull requests of a release change the file (PCR-00061, PCR-00085), and they put the same matrix in `main` and in `develop`, so the next release pull request merges it without conflicts. Run locally, `tests/build_test_matrix.py` writes `test_matrix_local.md`, which git ignores. `tests/check_pr_ready.py` fails a branch that changes the matrix and names the file to put back, and fails a test matrix branch that changes any other file.

### PCR-00082 Local tests before each push
An agent must push a feature or fix branch only after every test that its environment can run has passed locally on the commit it pushes.

Note: For example, `python -m unittest discover -s tests -t .` or `python tests/build_test_matrix.py`. Where PyQt6 or h5py can't be installed, the tests that need them are skipped locally, and CI runs them.

### PCR-00059 Affected requirements without tests
The test check of a pull request must fail when a high-level functional requirement that its branch affects has no test, except as in PCR-00068.

Note: A branch affects an HLFR when it changes the text of the HLFR or of a child LLFR, or a function in `src` that names a child LLFR. For a pull request into `main`, these are the changes since the last merge into `main`.

### PCR-00060 Branch up to date before a pull request into develop
A branch must contain the latest commit of `develop` when its pull request into `develop` is opened.

### PCR-00061 Matrix pull request into main after a release
After each release pull request is merged into `main`, an agent must open a pull request into `main`, from a test matrix branch (PCR-00002), that changes only `tests/test_matrix.md`, to the test matrix that CI built on the release pull request, except as in PCR-00086.

Note: The matrix is the `test-matrix` artifact of the last `tests` run of the release pull request, which is complete; its comment on the pull request may be cut. On every pull request, the `tests` job builds the matrix from the code of the pull request, with PyQt6 and h5py installed, and posts it on the pull request; CI itself commits no matrix. An agent opens the matrix pull requests with its own account, because GitHub runs no workflow on a pull request opened with the workflow token. This follows the owner's decisions of 2026-11-05.

### PCR-00085 Matrix pull request into develop after a release
After each release pull request is merged into `main`, an agent must open a pull request into `develop`, from a test matrix branch (PCR-00002), that changes only `tests/test_matrix.md`, to the same matrix as the pull request of PCR-00061, except as in PCR-00086.

### PCR-00086 Failed release run
When the last CI run of a merged release pull request has failed, the agent must open an issue that names the failed tests, in place of the pull requests of PCR-00061 and PCR-00085.

Note: A failed run shouldn't be offered as the matrix of `main` (PCR-00025).

### PCR-00083 Matrix-only changes skip the tests
A pull request into `develop` that changes only `tests/test_matrix.md`, and the pull request of PCR-00061, must skip the run of the tests.

Note: A pull request into `main` from `develop` runs every test even when it changes only the matrix (PCR-00058). Like PCR-00079, the `tests` job then skips its test steps and still reports success.

### PCR-00084 Merge of the matrix pull request into main
The owner must approve, as code owner, and merge the pull request of PCR-00061.

Note: The ruleset of `main` asks for a code-owner review. The matrix pull request has no issue, as a test matrix branch (PCR-00002), and it is the one pull request into `main` that doesn't come from `develop`.

### PCR-00087 Merge of the matrix pull request into develop
An agent must merge the pull request of PCR-00085 once its CI checks pass, with no independent review.

Note: The pull request changes only the matrix file, which `tests/check_pr_ready.py` checks (PCR-00081), and it has no issue (PCR-00002).

### PCR-00062 Tests passed before a merge
A pull request into `develop` or `main` must be merged only when every test of its CI run (PCR-00057, PCR-00058) has passed, except a test of `tests/known_macos_failures.txt` that fails on macOS, and except as in PCR-00064, PCR-00079 and PCR-00083.

Note: Such a test shows as "known macOS failure" in the matrix and doesn't make column 4 show "fail".

### PCR-00064 Environment Fail* counts as passed
For PCR-00062, a test shown with the `Fail*` of PCR-00063 must count as passed in a pull request into `develop`.

Note: This follows the owner's decision of 2026-11-03 that a justified `Fail*` is enough, limited on 2026-11-05 to `develop`: a pull request into `main` carries no `Fail*` (PCR-00069). PCR-00072 applies the same decision to the runs of PCR-00057, including the run on GitHub.

### PCR-00066 List of HLFRs not implemented yet
An HLFR whose implementation has not been done yet must be declared in `tests/not_implemented.txt`, on a line that holds its ID followed by the explanation.

Note: Lines that start with `#` are comments, as in `tests/known_macos_failures.txt`.

### PCR-00067 Implemented HLFR leaves the list
An HLFR must be removed from `tests/not_implemented.txt` when its implementation is done.

### PCR-00068 Not-implemented HLFR in a pull request into develop
In a pull request into `develop`, the test check of PCR-00059 must pass an affected HLFR that has no test when the HLFR is listed in `tests/not_implemented.txt` (PCR-00066).

### PCR-00069 No Fail* into main
A pull request from `develop` to `main` must be merged only when the test matrix that CI builds on it shows no `Fail*` of either kind (PCR-00063, PCR-00065).

Note: Every functional requirement then has its implementation and every test has run (PCR-00018, PCR-00058). This follows the owner's decision of 2026-11-05. `tests/check_pr_ready.py` checks the matrix of the run, `tests/not_implemented.txt` and the Fail* section of the description.

### PCR-00070 Fail* list at the top of the pull request
Every pull request into `develop` or `main` must start its description with a section headed `## Fail* (PCR-00070)` that holds one entry for each missing capability of PCR-00063 in the matrix that CI builds on it, with the number of tests it affects, and one entry for each HLFR of PCR-00065, each entry with its justification, or the single entry `none` when there is no `Fail*`.

Note: The reviewer then sees every exception first. CI builds the matrix with PyQt6 and h5py, so a normal pull request has the section with `- none`. `tests/build_test_matrix.py` prints the section, ready to paste. The `fail-star-section` CI job checks it against `tests/not_implemented.txt`, and the `tests` job against the matrix of its run, which alone knows an environment `Fail*`. This follows the owner's decision of 2026-11-05.

### PCR-00088 Independent review before the pull request
Before a pull request into `develop` is opened, an agent other than its implementer must review the branch's code and requirements, except as in PCR-00087.

Note: This is the review of PCR-00016, done before CI. The owner agreed this flow on 2026-11-05. A release keeps PCR-00050, and the owner merges it (PCR-00015).

### PCR-00089 Judgement pass in the review
When the branch adds or changes requirements, the reviewer of PCR-00088 must run on them the judgement pass of the `requirement-validation` skill.

### PCR-00090 Tests written by the reviewer
The reviewer of PCR-00088 must add to the branch tests focused on the problem that the branch tackles.

### PCR-00091 Reviewer's files
The reviewer of PCR-00088 must change only files under `tests/`.

Note: The code under `src/` stays the implementer's work.

### PCR-00092 Reviewer's local tests
The reviewer of PCR-00088 must run the local tests (PCR-00082) on the branch before it gives its green light.

### PCR-00093 Findings to the implementer
The reviewer of PCR-00088 must send its findings to the implementer.

### PCR-00094 Review of the fixes
After the implementer has fixed the findings, the reviewer of PCR-00088 must check only the changes made since its last review.

### PCR-00095 Pull request after the green light
A pull request into `develop`, other than the pull request of PCR-00085, must be opened only after the green light of the reviewer of PCR-00088.

Note: CI runs once the pull request is open.

### PCR-00096 Merge by the reviewer
When the CI checks of the pull request pass, with no `Fail*` other than those declared in its Fail* section (PCR-00070), the reviewer of PCR-00088 must merge it into `develop` with no further review.

Note: A declared `Fail*` is accepted into `develop` only (PCR-00069).

### PCR-00097 CI failure goes back to the implementer
When the CI checks of the pull request fail, the branch must go back to the implementer for a fix, which the reviewer checks as in PCR-00094 before CI runs again.

### PCR-00098 Commits after the green light
The reviewer of PCR-00088 must check every commit added to the branch after its green light, such as a merge of `develop` or a conflict fix, before it merges the pull request.

### PCR-00025 Stable permanent branches
The `develop` and `main` branches must be kept free of crashes.

### PCR-00026 Worktrees
Worktrees must be used to give each agent a separate environment.

### PCR-00027 Deleted requirement ID kept
When a requirement is deleted, its ID must stay in the file.

### PCR-00043 Deleted requirement text
When a requirement is deleted, its title and text must be replaced by `DELETED`.

### PCR-00044 Deleted IDs not reused
The ID of a deleted requirement must never be reused.

### PCR-00045 Numbering after a deletion
When a requirement is deleted, new requirements must continue from the next number.

### PCR-00028 Functional requirement categories
Functional requirements must be divided into two categories: high-level functional requirements (HLFR) and low-level functional requirements (LLFR).

### PCR-00029 HLFR approval
High-level functional requirements must have human approval to be created or modified.

### PCR-00030 LLFR ownership
Low-level functional requirements must be created and edited by agents during development.

### PCR-00031 LLFR traceability
Every low-level functional requirement must be linked to at least one high-level functional requirement.

### PCR-00055 HLFR children
Every high-level functional requirement must have at least one low-level functional requirement linked to it.

Note: `tests/check_requirements.py` tests it.

### PCR-00032 Sample file for every format
The `tests/user_tests/good` folder must contain at least one sample file that the app can open for each file format listed in HLFR-00005.

Note: The files are generated by `tests/user_tests/make_user_test_files.py`.

### PCR-00047 Sample file generator kept up to date
`tests/user_tests/make_user_test_files.py`, which generates the files of PCR-00032, must be updated when a format is added to HLFR-00005.

### PCR-00073 Big sample files in the build
The build of the standalone executable must generate, in a folder that is not committed, one sample file for each format of HLFR-00005 with 100 signals and a time signal of 4 hours sampled every 0.01 s.

Note: An Excel file holds at most 1,048,576 rows, so the Excel file holds as many samples as fit (about 2.9 hours).

### PCR-00033 Language of the requirements
All the requirements must be written in English.

### PCR-00034 Language of issues and pull requests
All GitHub issues and pull requests must be written in English.

### PCR-00035 Language of Markdown files
All the Markdown (`.md`) files in the repository must be written in English.

### PCR-00036 One statement per requirement
Each requirement must state only one obligation, about only one thing.

Note: The word `must` therefore appears only once in the statement. A `Note:` line is not part of the statement, and deleted requirements are excluded.

### PCR-00054 Clear requirements
Each requirement must be clear and unambiguous.

Note: A script can't tell this, so the requirements review of the `requirement-validation` skill and the reviewer of PCR-00056 check it.

### PCR-00049 Positive statements in new requirements
Each requirement created after this requirement was added must state its obligation in positive form, without the words "must not".

### PCR-00037 Requirements quality test
The quality of the requirements must be tested before every merge, in the same way as the functional requirements are tested.

Note: `tests/check_requirements.py` tests it and runs on every pull request.

### PCR-00048 Review of new and changed requirements
A reviewer must read every requirement that was created or changed in a pull request, to check the part of PCR-00036 that a script can't check (whether a requirement talks about only one thing).

### PCR-00056 Clarity review of new and changed requirements
A reviewer must read every requirement that was created or changed in a pull request, to check that it is clear and unambiguous (PCR-00054).

### PCR-00038 Requirements quality result on the pull request
The result of the requirements quality test (PCR-00037) must be added to the pull request.
