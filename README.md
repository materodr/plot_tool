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
pip install pyinstaller
pyinstaller --onefile --windowed --distpath bin --workpath build src/main.py
```
