---
name: "requirement-validation"
description: "Check, validate and correct the plot_tool requirements so each states one obligation about one thing. Required before every develop-to-main PR (PCR-00050) and before every PR into develop whose branch adds requirements (PCR-00052)."
---

# Requirement validation (plot_tool)

This skill checks, validates by independent review, and corrects the requirements in `docs/requirements/` of materodr/plot_tool, without changing their meaning.

**When to run it**
- **Before every pull request from `develop` to `main`** (PCR-00050). The scope is every requirement created or changed since the last merge into `main`, and the release PR must show the result (PCR-00051).
- **Before every pull request into `develop` whose branch adds requirements** (PCR-00052). The scope is the requirements that the branch adds, and the PR must show the result (PCR-00053).
- Whenever the owner asks for a requirements quality check, or the `requirements-quality` CI job fails.

**Owner's ground rules (never break them)**
1. Corrections change requirement text, references, test tags and comments only. No code in `src/` changes, and nothing the app does changes.
2. **The meaning must not change.** The corrected set must say exactly what the old set said:
   - no obligation added, dropped, weakened or strengthened;
   - the same triggers, conditions, values, texts and exceptions.
   Keep an ambiguity rather than guess.
3. The tests must pass.
4. HLFR changes need the owner's approval (PCR-00029). Either ask him, or say in the PR that he approves the HLFR changes there.
5. Agents never merge into `main` (PCR-00015). The owner approves requirement-fix PRs himself unless he says otherwise.

---

## Step 1. Scope
- **Before a develop to main PR:**
  ```bash
  git fetch origin main develop
  git diff origin/main origin/develop -- docs/requirements/
  ```
  Collect every ID whose heading or body changed, plus every new ID.
- **Owner-requested full check:** all active requirements.
- **Before a PR into develop:**
  ```bash
  git fetch origin develop
  git diff origin/develop...HEAD -- docs/requirements/
  ```
  Collect every ID that is new on the branch. A requirement that only changed is out of this scope, and a reviewer still reads it (PCR-00048).

## Step 2. Automatic check
Run `python tests/check_requirements.py`. It checks:
- IDs: valid, unique, no gaps (PCR-00044, PCR-00045).
- References: every ID named exists.
- Parent links: each active LLFR names existing HLFRs (PCR-00031).
- HLFR children: each active HLFR has a child LLFR (PCR-00055).
- One must: "must" exactly once in the statement (PCR-00036). Note and Parent lines are excluded, and a quoted mention such as "must not" is ignored.
- Positive statement: requirements with an ID above `LAST_ID_BEFORE_POSITIVE_RULE_DICT` must not use "must not" (PCR-00049).

Record the result line, for example "Result: pass, 0 problems in N active requirements".

## Step 3. Judgement pass (the script can't do this)
Read every requirement in scope; don't rely on the script alone. Flag the following.

**a. More than one thing, even with one "must".**

Split when obligations can each be met or failed on their own:
- joined by "and", "or", commas or "also": "show the box and keep the file open", "let the user choose a color and draw the item in it";
- one condition with two outcomes: "do X when P, and Y when Q", "zoom in forward, out backward";
- an obligation plus an exception that can stand alone as a second rule.

Keep as ONE thing:
- a list that defines a single thing: file content, menu order, a table of texts, icon parts, the allowed values of one setting, the list of undoable actions;
- one action with a compound object always checked together: "show the x and y values";
- qualifiers of the same obligation: where, when, colour, format;
- simple HLFR-level pairs that are one feature: "zoom in and out", "show and hide the grid".

When in doubt, don't split: over-splitting hurts readability.

**b. Obligations hidden in a `Note:` line.** Look for "must", "has to", "shall", "needs to" and "is required". A note is guidance, so an obligation there is ambiguous. **Never decide alone.** For each one, show the owner the full requirement and ask whether to:
- make the note a separate requirement;
- keep it as a note, reworded without "must";
- rewrite the requirement.

**c. "must not".** PCR-00049 requires positive form for requirements created after it was added. For older requirements that change, the reviewer checks it. Existing "must not" requirements stay unless the owner says otherwise.

**d. Not clear or ambiguous (PCR-00054).** Flag a requirement that two careful readers could understand differently, for example:
- a word with no measure, such as "quickly", "easy to read" or "small", where a test needs a limit;
- a pronoun or a "that" whose target isn't certain;
- a trigger, condition or exception that leaves a case undecided;
- a term used with two meanings, or two terms for one thing.

**Never decide alone what it means.** Show the owner the full requirement and ask. The ground rule of keeping an ambiguity applies to corrections that split a requirement; it doesn't excuse leaving one unreported here.

**e. Other defects worth reporting:**
- a requirement that reads stronger than intended, for example "must find a signal even when…", which implies a search is never empty;
- an obligation placed on the user instead of the app ("the user must…");
- stale wording such as "today" or "currently";
- a wrong or missing reference or parent.

## Step 4. Correction, through a Fix issue and PR
1. **Issue and branch:**
   - Open a Fix issue with the template sections (Bug description, Severity, Steps to reproduce, Solution, How the solution was tested, Evidence), through REST (`gh api repos/materodr/plot_tool/issues ...`). GraphQL is blocked.
   - Create the branch `fix/<issue>-<short-name>` from `develop`, in its own worktree.
2. **Splitting:**
   - The original ID keeps the main obligation. Adjust its title if it now covers less.
   - Each other obligation gets a new requirement placed directly after the original. Its ID is the next free number of the prefix (PCR-00027). Never reuse or renumber an ID.
   - Each new part restates its trigger or condition and stands alone, for example "When the user chooses \"FFT\" and fewer than 8 samples…".
   - **If a later sentence of the original limited an earlier one, the earlier part must now say "except as in <new ID>".** Missing this was the most common review finding.
   - Don't hide obligations in "must: (1)… (2)…" lists, in "must A and must B" chains, or in notes.
   - Write reported speech without "must": "say that the signal has to increase".
   - **LLFR parents:** copy the original's `*Parent: …*` line. Drop a parent only when it clearly doesn't fit the part, and keep at least one.
   - **New HLFRs:** each one needs at least one child LLFR whose content refines it.
   - **Notes** stay with the part they explain. Copy a note only when it explains both parts.
   - **Positive form:** new requirements use it (PCR-00049).
3. **References:**
   - Grep every split ID in the four requirement files, `docs/requirements/README.md`, `CLAUDE.md`, `.github/workflows/`, the comments in `tests/` and `.gitignore`.
   - Update the references that mean a part that moved, or the whole old requirement; in that case, name all the parts.
   - Comments in `src/` may keep the original ID, because that ID still exists.
4. **Test tags:** for each new ID, add it to the `@covers(...)` of the existing tests that check that part.
   - Read the test body; don't blindly copy every tag of the original.
   - Never change test logic.
   - List the parts that no test checks.
5. **Run the checks:**
   - `python tests/check_requirements.py` must pass;
   - `python -m unittest discover -s tests -t .`;
   - `pycodestyle`.

   PyQt6 and h5py may not install locally (the proxy blocks pypi), so CI runs the GUI tests.
6. **Matrix:** compare it with develop's `tests/test_matrix.md`.
   - No HLFR that passed may become "fail" or "no tests", unless it only passed through a parent link that no longer fits. Report that case explicitly.
   - The CI matrix comment is cut off at GitHub's size limit, so read the HLFR rows from the `tests` job log.

### Large batches (dozens of requirements)
- **Regions:** split the work into regions:
  - COR, PCR, HLFR and the LLFR General section;
  - Top panel;
  - Signal list panel;
  - Plot panel, part 1 and part 2.

  Each region gets one writer agent with its own worktree and branch `fix/<n>-split-<region>`.
- **Writers:**
  - Each writer uses a placeholder ID range (40000+, 50000+, …) and edits only its region.
  - It writes `tags.tsv` (`ID<TAB>module.Class.method`), `xref.tsv` (references outside its region) and `untested.txt`. The HLFR writer also writes `parents.tsv`.
- **Integration:** merge the region branches into the fix branch; the regions are disjoint, so the merges are clean. One integration agent then applies xref and parents, renumbers, and applies the tags.
- **Renumber script:** maps each prefix's IDs ≥ 40000, in heading order, to max(real IDs)+1, +2, …
  ```python
  import os, re, sys
  FILES = {"COR": "code_and_organization.md", "PCR": "process_of_collaboration.md",
           "HLFR": "high_level_functional_requirements.md",
           "LLFR": "low_level_functional_requirements.md"}
  root, extra = sys.argv[1], sys.argv[2:]
  folder = os.path.join(root, "docs", "requirements")
  mapping = {}
  for prefix, name in FILES.items():
      text = open(os.path.join(folder, name), encoding="utf-8").read()
      numbers = [int(n) for n in re.findall(rf"^### {prefix}-(\d{{5}}) ", text, re.M)]
      nxt = max(n for n in numbers if n < 40000) + 1
      for n in numbers:
          if n >= 40000:
              mapping[f"{prefix}-{n:05d}"] = f"{prefix}-{nxt:05d}"; nxt += 1
  pat = re.compile(r"\b(?:COR|PCR|HLFR|LLFR)-\d{5}\b")
  for path in [os.path.join(folder, n) for n in FILES.values()] + extra:
      t = open(path, encoding="utf-8").read()
      open(path, "w", encoding="utf-8").write(pat.sub(lambda m: mapping.get(m.group(0), m.group(0)), t))
  ```
- **Tag script:** parse each test file with `ast`, find `Class.method`, and append the IDs to its `@covers(...)` call. Wrap at 79 columns, and add `@covers` if it's missing.

## Step 5. Independent validation (never the writer)
- Start reviewer agents that didn't write the change: one per region for a big batch, one for a small change. Give them the code, not your conclusion. They report and don't edit.
- For every changed requirement, the reviewer compares the old text at the base commit with the new original plus all its new parts, and checks:
  1. **Same meaning:**
     - nothing added, dropped, weakened or strengthened;
     - no trigger, condition, value or exception lost;
     - no "except as in" whose reach changed;
     - no "may" turned into "must";
     - no description turned into a rule;
     - no reported speech turned into an obligation.
  2. **One obligation about one thing:** watch for hidden lists, and for over-splitting.
  3. **Each part stands alone:** its trigger is clear and its references are right.
  4. **Parents fit each part.**
  5. **References elsewhere** still mean the same.
  6. **Test tags:** check about 20 per region, or more than 60 across a big PR.
     - Does the tagged test check that part?
     - Was a tag put on the wrong method?
     - The `tests/` and `src/` diffs must contain only `@covers` lines and comments.
  7. **A sample of unsplit single-"must" requirements:** should any of them have been split?
- Findings are ranked:
  - **BLOCKING:** the meaning changed;
  - **SHOULD-FIX:** unclear wording, a wrong reference or parent, or a lost trigger or exception;
  - **MINOR:** style or over-splitting.

  Each finding gives the old text, the new text and an exact fix.
- Fix every BLOCKING and SHOULD-FIX finding, then check again. Bring the owner every choice that is his: notes, HLFR wording, and parents that change matrix results.

## Step 6. Report
- **PR description and issue sections:**
  - the check result line;
  - counts per prefix, before and after;
  - the owner decisions applied;
  - the matrix counts (pass, fail, no tests), with the reason for each HLFR that doesn't pass;
  - the untested new parts;
  - known points.
- **For a develop to main PR (PCR-00051):** add a "Requirement validation (PCR-00050)" section. **For a PR into develop whose branch adds requirements (PCR-00053):** add a "Requirement validation (PCR-00052)" section instead. `tests/check_requirement_review.py` looks for these headings. The section has:
  - the scope (the IDs created or changed since the last merge into `main`, or the IDs the branch adds);
  - the check result;
  - the judgement-pass findings and how each was resolved, with links to the fix issue and PR;
  - a statement that no finding is still open.

  If a finding is still open, fix it first through a Fix issue and a PR into `develop`, then open the release PR.

## Practical notes
- The shared clone's remote-tracking refs can be stale, so use `git fetch origin <branch>` and FETCH_HEAD.
- GitHub is REST only (`gh api`). A draft PR can't be merged or marked ready through REST, so open PRs as non-draft.
- If the stop hook reports "unpushed commits" on a new branch, push it and set its upstream config.
- For long CI waits, poll `gh api repos/materodr/plot_tool/commits/<sha>/check-runs` in a background loop.