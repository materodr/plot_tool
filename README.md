# plot_tool

A desktop application that reads files containing time series (CSV, Excel and MATLAB) and displays the signals as curves.

The requirements are in [docs/requirements](docs/requirements), and the rules for working in this repository are in [CLAUDE.md](CLAUDE.md).

## Folder layout

| Folder | Contents |
|---|---|
| `src/` | All code needed to run the app, split into `model/`, `view/` (PyQt6) and `controller/` (MVC) |
| `tests/` | All tests, the test matrix (`tests/test_matrix.md`) and the script that builds it |
| `bin/` | Standalone executables built from `src/`. Build outputs are not committed |

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python src/main.py
```

## Test

The tests use the standard library `unittest`. Each test is tagged with the requirement IDs it checks, so the test matrix can be built from the results:

```bash
python tests/build_test_matrix.py        # runs every test, writes tests/test_matrix.md
python -m pycodestyle src tests          # PEP 8 check
```

GUI tests are skipped when PyQt6 is not installed. The GitHub Actions workflow (`.github/workflows/tests.yml`) runs every test with PyQt6 on each pull request.

## Build a standalone executable

```bash
pip install -r requirements.txt -r requirements-build.txt   # PyInstaller
python build_executable.py
```

`build_executable.py` holds the whole PyInstaller configuration, so everyone builds the app the same way. It builds one folder (`--onedir --windowed`), not one file: a one-file executable unpacks the whole app into a temporary folder on every launch and starts it again as a second process, which made the macOS app take tens of seconds to open and its Dock icon disappear and reappear (issue #67). Modules the app doesn't use (tkinter, other GUI toolkits and matplotlib backends, IPython, test packages) are left out.

Where the app ends up (in `bin/`, never committed):

| OS | App | How to start it |
|---|---|---|
| macOS | `bin/plot_tool.app` | Open it from Finder, or drag it to Applications first |
| Windows | `bin\plot_tool\plot_tool.exe` | Double-click it; keep the whole `plot_tool` folder together |
| Linux | `bin/plot_tool/plot_tool` | Run it; keep the whole `plot_tool` folder together |

On macOS the bundle is signed ad hoc, so an app you build yourself opens without extra Gatekeeper checks. An app copied from another computer or downloaded still has to be approved once (right-click it, then Open). The very first launch is also slower than the next ones, because matplotlib builds its font cache (kept in `~/.matplotlib`).

### Check the startup time

With the environment variable `PLOT_TOOL_STARTUP_PROBE=1`, the app prints when its window was shown and quits; without it, nothing changes. `tests/user_tests/measure_startup.py` uses it to time launches:

```bash
python tests/user_tests/measure_startup.py --runs 2 -- bin/plot_tool.app/Contents/MacOS/plot_tool
python tests/user_tests/measure_startup.py --runs 2 -- python src/main.py
```

The GitHub Actions workflow `.github/workflows/macos_build.yml` builds the macOS app, checks that it is a one-folder bundle, opens every file of `tests/user_tests/good` with it and fails when a warm launch takes longer than 10 s.
