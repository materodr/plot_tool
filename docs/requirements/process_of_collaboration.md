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

Note: Every issue must be created from one of the two templates: [Fix](../../.github/ISSUE_TEMPLATE/fix.yml) or [Feature](../../.github/ISSUE_TEMPLATE/feature.yml).

### PCR-00005 Branch linked to an issue
Feature and fix branches must always be created pointing to an issue, and the issue must be explicit in the branch name.

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

### PCR-00010 Work priority
Priority of work must be given to feature issues with higher urgency and fix issues with higher severity.

### PCR-00011 Fixes before features
Between a feature of high urgency and a fix of high severity, the fix of high severity must have priority.

### PCR-00012 Issue before work
A feature or fix must only start to be tackled when the issue that tracks it has already been created.

### PCR-00013 Bugs found during work
If a new bug is found while creating a feature or fixing a bug:
1. if the bug is correlated with the ongoing work, it must be fixed under the same issue;
2. if it is not correlated, a new issue must be opened.

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

### PCR-00019 Test matrix
A table named test matrix must be permanently kept in the `tests` folder.

### PCR-00020 Test matrix column 1
The first column of the test matrix must contain the current set of high-level functional requirements (HLFR).

### PCR-00021 Test matrix column 2
The second column must show, for each HLFR, its child low-level functional requirements (LLFR).

### PCR-00022 Test matrix column 3
The third column must contain the tests linked to each HLFR and the last run status of each test, as passed or failed.

### PCR-00023 Test matrix column 4
The fourth column must contain "pass" if all tests of the HLFR passed and "fail" if at least one test failed.

### PCR-00024 Test coverage
Agents must write tests that robustly cover every aspect of the high-level functional requirements.

### PCR-00025 Stable permanent branches
The `develop` and `main` branches must be kept free of crashes.

### PCR-00026 Worktrees
Worktrees must be used to give each agent a separate environment.

### PCR-00027 Deleted requirements
When a requirement is deleted, its ID must stay in the file and its title and text must be replaced by `DELETED`. The ID must never be reused, and new requirements must continue from the next number.

### PCR-00028 Functional requirement categories
Functional requirements must be divided into two categories: high-level functional requirements (HLFR) and low-level functional requirements (LLFR).

### PCR-00029 HLFR approval
High-level functional requirements must have human approval to be created or modified.

### PCR-00030 LLFR ownership
Low-level functional requirements must be created and edited by agents during development.

### PCR-00031 LLFR traceability
Every low-level functional requirement must be linked to at least one high-level functional requirement.

### PCR-00032 Sample file for every format
The `tests/user_tests/good` folder must contain at least one sample file that the app can open for each file format listed in HLFR-00005.

Note: The files are generated by `tests/user_tests/make_user_test_files.py`, which must be updated when a format is added.
