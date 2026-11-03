# Process of Collaboration Requirements

Prefix: `PCR`. Format rules: see [README.md](README.md).

### PCR-00001 Repository host
The project must be kept in a GitHub repository.

### PCR-00002 Branch types
The repository must use the following branch types:
1. a permanent `main` branch;
2. a permanent `develop` branch;
3. feature branches, created as needed;
4. fix branches, created as needed.

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

### PCR-00014 Pull request preconditions
A pull request must only be merged if its issue has all the information required by PCR-00006 (fixes) or PCR-00008 (features).

### PCR-00015 Human approval for main
Pull requests into `main` must be approved by humans.

### PCR-00016 Agent merges
An AI agent must only merge a pull request into a branch other than `main` after an agent different from the one that did the implementation has reviewed and tested it independently.

### PCR-00017 Issue list for develop to main
A pull request from `develop` to `main` must list all the issues that track the code changes since the last merge into `main`.

### PCR-00018 Evidence for develop to main
A pull request from `develop` to `main` must show evidence that the code fulfils all the functional requirements.

### PCR-00050 Requirements review before develop to main
Before a pull request from `develop` to `main` is opened, the requirements review of the `requirement-validation` skill must be run on every requirement created or changed since the last merge into `main`.

### PCR-00051 Requirements review result for develop to main
A pull request from `develop` to `main` must show the result of the requirements review of PCR-00050.

### PCR-00052 Requirements review before a pull request into develop
Before a pull request into `develop` is opened, the requirements review of the `requirement-validation` skill must be run on every requirement that its branch adds.

Note: A branch that adds no requirement has nothing to review, so its pull request has no result to show (PCR-00053).

### PCR-00053 Requirements review result for a pull request into develop
A pull request into `develop` whose branch adds a requirement must show the result of the requirements review of PCR-00052.

### PCR-00019 Test matrix
A table named test matrix must be permanently kept in the `tests` folder.

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
The fourth column must contain "pass" if all tests of the HLFR passed, except as in PCR-00065.

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
A pull request into `develop` must run every test.

### PCR-00058 Tests of a pull request into main
A pull request from `develop` to `main` must run every test.

### PCR-00059 Affected requirements without tests
The test check of a pull request must fail when a high-level functional requirement that its branch affects has no test, except as in PCR-00068.

Note: A branch affects an HLFR when it changes the text of the HLFR or of a child LLFR, or a function in `src` that names a child LLFR. For a pull request into `main`, these are the changes since the last merge into `main`.

### PCR-00060 Branch up to date before a pull request into develop
A branch must contain the latest commit of `develop` when its pull request into `develop` is opened.

### PCR-00061 Test matrix built from the branch
The test matrix committed on the branch of a pull request into `develop` or `main` must come from a run of every test on the code of that branch.

Note: The matrix holds a hash of the files it was built from, so its own commit doesn't make it old.

### PCR-00062 Tests passed before a pull request
A pull request into `develop` or `main` must be opened only when every test of the run of PCR-00061 has passed, except a test of `tests/known_macos_failures.txt` that fails on macOS, and except as in PCR-00064.

Note: Such a test shows as "known macOS failure" in the matrix and doesn't make column 4 show "fail".

### PCR-00064 Environment Fail* counts as passed
For PCR-00062, a test shown with the `Fail*` of PCR-00063 must count as passed.

Note: A justified `Fail*` is enough to open and to merge the pull request, even when GitHub can't run the test either.

### PCR-00066 List of HLFRs not implemented yet
An HLFR whose implementation has not been done yet must be declared in `tests/not_implemented.txt`, on a line that holds its ID followed by the explanation.

Note: Lines that start with `#` are comments, as in `tests/known_macos_failures.txt`.

### PCR-00067 Implemented HLFR leaves the list
An HLFR must be removed from `tests/not_implemented.txt` when its implementation is done.

### PCR-00068 Not-implemented HLFR in a pull request into develop
In a pull request into `develop`, the test check of PCR-00059 must pass an affected HLFR that has no test when the HLFR is listed in `tests/not_implemented.txt` (PCR-00066).

### PCR-00069 No not-implemented Fail* into main
A pull request from `develop` to `main` must be opened only when its test matrix shows no `Fail*` of PCR-00065.

Note: Every functional requirement then has its implementation (PCR-00018).

### PCR-00070 Fail* list at the top of the pull request
A pull request whose test matrix shows a `Fail*` must start its description with a section headed `## Fail* (PCR-00070)` that lists every `Fail*` of the matrix with its justification.

Note: The reviewer then sees every exception first. `tests/build_test_matrix.py` prints the section, ready to paste, and the `fail-star-section` CI job checks it with `tests/check_pr_ready.py`.

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

### PCR-00048 Review of changed requirements
A reviewer must read every requirement that changed in a pull request, to check the part of PCR-00036 that a script can't check (whether a requirement talks about only one thing).

### PCR-00056 Clarity review of changed requirements
A reviewer must read every requirement that changed in a pull request, to check that it is clear and unambiguous (PCR-00054).

### PCR-00038 Requirements quality result on the pull request
The result of the requirements quality test (PCR-00037) must be added to the pull request.
