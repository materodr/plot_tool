# plot_tool

A Python application that reads files containing time series and displays the data to the user.

## Requirements

The requirements below are loaded into every session. Follow them in all work.

@docs/requirements/README.md
@docs/requirements/code_and_organization.md
@docs/requirements/process_of_collaboration.md
@docs/requirements/functional_requirements.md

## How to work in this repository

- Before any work, make sure a GitHub issue exists for it (PCR-00004, PCR-00012). Create it from the Fix or Feature template in `.github/ISSUE_TEMPLATE/` (Note on PCR-00004). When creating it with `gh`, use the same sections as the template.
- Branch names must make the branch type and the issue explicit (PCR-00003, PCR-00005). Project convention: create the branch from `develop` and name it `feature/<issue number>-<short-name>` or `fix/<issue number>-<short-name>`.
- Project convention: feature and fix pull requests go into `develop`.
- Pull requests from `develop` to `main` must follow PCR-00017 and PCR-00018 and need human approval (PCR-00015). Agents never merge into `main`.
- Do not merge your own work. A different agent or a human must review and test it first (PCR-00016).
- Before a pull request is merged, fill in the remaining sections of its issue, as listed in PCR-00006 (fixes) or PCR-00008 (features) (PCR-00014).
- Work in your own git worktree (PCR-00026).
