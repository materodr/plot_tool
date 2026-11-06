#!/usr/bin/env bash
# Install PyQt6 and h5py from the ci-wheels branch (PCR-00130, PCR-00131).
#
# Usage:
#     bash tests/install_local_wheels.sh [--folder DIR] [--no-install]
#
# For an agent's workspace that can't install these packages from PyPI
# but can reach github.com. The script:
# 1. fetches origin ci-wheels and writes its files into a folder outside
#    the worktree (by default ~/.cache/plot_tool/ci_wheels, or
#    $PLOT_TOOL_WHEELS_FOLDER, or --folder DIR), replacing what it held;
#    a folder that isn't empty is replaced only when this script wrote
#    it before;
# 2. joins the parts <wheel>.part-00, <wheel>.part-01, ... of each wheel
#    that the Wheels workflow split, because GitHub rejects files over
#    100 MB;
# 3. checks every wheel against SHA256SUMS, and that no wheel is missing
#    from it;
# 4. runs pip install --no-index --find-links <folder> for PyQt6 and
#    h5py, at the versions that requirements.txt allows, adding
#    --break-system-packages when pip refuses an externally managed
#    environment, and prints the installed versions.
# --no-install stops after step 3.
#
# When the branch doesn't exist yet, can't be fetched, or a step fails,
# the script prints why and what to do, and exits with code 1: the agent
# reports it and carries on as before, with the GUI and HDF5 tests
# skipped locally and run in CI (PCR-00131). It uses bash, git, tar,
# sha256sum and the Python of $PYTHON (python3 by default).

set -uo pipefail

BRANCH_NAME="ci-wheels"
TRACKING_REF="refs/remotes/origin/$BRANCH_NAME"
PYTHON_COMMAND="${PYTHON:-python3}"
WHEELS_FOLDER="${PLOT_TOOL_WHEELS_FOLDER:-$HOME/.cache/plot_tool/ci_wheels}"
INSTALL_PACKAGES=1
MARKER_NAME=".plot_tool_ci_wheels"

# Print the reason of a failure, what the agent does next, and exit 1.
fail() {
    echo "install_local_wheels: $1" >&2
    echo "install_local_wheels: PyQt6 and h5py were not installed from $BRANCH_NAME." \
        "Report it and carry on: the GUI and HDF5 tests skip locally and CI runs them (PCR-00131)." >&2
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --folder)
            [ $# -ge 2 ] || fail "--folder needs a folder"
            WHEELS_FOLDER="$2"
            shift 2
            ;;
        --no-install)
            INSTALL_PACKAGES=0
            shift
            ;;
        -h|--help)
            sed -n '2,/^$/s/^# \{0,1\}//p' "$0"
            exit 0
            ;;
        *)
            fail "unknown option $1"
            ;;
    esac
done

SCRIPT_FOLDER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(git -C "$SCRIPT_FOLDER" rev-parse --show-toplevel 2>/dev/null)" \
    || fail "$SCRIPT_FOLDER is not in a git checkout"

# The folder must be outside the worktree, so that the wheels are never
# committed.
mkdir -p "$WHEELS_FOLDER" || fail "can't create $WHEELS_FOLDER"
WHEELS_FOLDER="$(cd "$WHEELS_FOLDER" && pwd)"
case "$WHEELS_FOLDER/" in
    "$REPOSITORY_ROOT/"*)
        fail "the folder $WHEELS_FOLDER is inside the worktree $REPOSITORY_ROOT; choose one outside it"
        ;;
esac

# Step 1: fetch only ci-wheels, into its remote-tracking ref.
echo "Fetching origin $BRANCH_NAME ..."
if ! git -C "$REPOSITORY_ROOT" fetch --no-tags origin \
        "+refs/heads/$BRANCH_NAME:$TRACKING_REF"; then
    fail "can't fetch origin $BRANCH_NAME: the branch may not exist yet (the Wheels workflow writes it after its merge into develop), or github.com can't be reached"
fi
commit="$(git -C "$REPOSITORY_ROOT" rev-parse "$TRACKING_REF")"
echo "Writing $BRANCH_NAME $commit into $WHEELS_FOLDER"
# Only a folder that is empty or that this script wrote before (it holds
# the marker file) is emptied, so that a wrong --folder deletes nothing.
if [ -n "$(ls -A "$WHEELS_FOLDER")" ] && [ ! -f "$WHEELS_FOLDER/$MARKER_NAME" ]; then
    fail "the folder $WHEELS_FOLDER is not empty and was not written by this script; choose an empty folder"
fi
find "$WHEELS_FOLDER" -mindepth 1 -delete || fail "can't empty $WHEELS_FOLDER"
touch "$WHEELS_FOLDER/$MARKER_NAME" || fail "can't write into $WHEELS_FOLDER"
git -C "$REPOSITORY_ROOT" archive "$TRACKING_REF" | tar -x -C "$WHEELS_FOLDER" \
    || fail "can't write the files of $BRANCH_NAME into $WHEELS_FOLDER"

cd "$WHEELS_FOLDER" || fail "can't enter $WHEELS_FOLDER"
shopt -s nullglob

# Step 2: join the parts of each split wheel, in the order of their
# numbers (the glob sorts them).
for first_part in *.part-00; do
    wheel="${first_part%.part-00}"
    part_list=("$wheel".part-*)
    cat "${part_list[@]}" > "$wheel" || fail "can't join the parts of $wheel"
    rm -f "${part_list[@]}"
    echo "Joined ${#part_list[@]} parts into $wheel"
done
leftover_list=(*.part-*)
[ ${#leftover_list[@]} -eq 0 ] \
    || fail "parts without a first part .part-00: ${leftover_list[*]}"

# Step 3: every wheel is listed in SHA256SUMS and matches it.
[ -f SHA256SUMS ] || fail "$BRANCH_NAME has no SHA256SUMS file"
wheel_list=(*.whl)
[ ${#wheel_list[@]} -gt 0 ] || fail "$BRANCH_NAME holds no wheel"
for wheel in "${wheel_list[@]}"; do
    awk -v name="$wheel" '{ listed = $2; sub(/^\*/, "", listed) }
        listed == name { found = 1 } END { exit !found }' SHA256SUMS \
        || fail "$wheel is not listed in SHA256SUMS"
done
sha256sum --check --strict --quiet SHA256SUMS \
    || fail "a wheel doesn't match SHA256SUMS"
echo "All ${#wheel_list[@]} wheels match SHA256SUMS."

if [ "$INSTALL_PACKAGES" -eq 0 ]; then
    echo "Wheels ready in $WHEELS_FOLDER (--no-install)."
    exit 0
fi

# Step 4: the requirements of PyQt6 and h5py as requirements.txt gives
# them, for example PyQt6>=6.5.
requirement_list=()
while IFS= read -r requirement; do
    requirement_list+=("$requirement")
done < <(grep -iE '^(pyqt6|h5py)\b' "$REPOSITORY_ROOT/requirements.txt" | cut -d' ' -f1)
[ ${#requirement_list[@]} -eq 2 ] \
    || fail "requirements.txt doesn't name both PyQt6 and h5py"

pip_option_list=(--no-index --find-links "$WHEELS_FOLDER")
echo "Installing ${requirement_list[*]} from $WHEELS_FOLDER ..."
pip_output="$("$PYTHON_COMMAND" -m pip install "${pip_option_list[@]}" \
    "${requirement_list[@]}" 2>&1)"
pip_status=$?
if [ $pip_status -ne 0 ] && grep -q "externally-managed-environment" <<< "$pip_output"; then
    echo "pip refuses an externally managed environment; trying again with --break-system-packages"
    pip_output="$("$PYTHON_COMMAND" -m pip install "${pip_option_list[@]}" \
        --break-system-packages "${requirement_list[@]}" 2>&1)"
    pip_status=$?
fi
echo "$pip_output"
[ $pip_status -eq 0 ] || fail "pip install from $WHEELS_FOLDER failed"

"$PYTHON_COMMAND" - <<'PYTHON' || fail "PyQt6 or h5py can't be imported after the install"
from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
import h5py
print(f"PyQt6 {PYQT_VERSION_STR} (Qt {QT_VERSION_STR}), h5py {h5py.__version__}")
PYTHON
echo "Run the tests with QT_QPA_PLATFORM=offscreen, for example: QT_QPA_PLATFORM=offscreen python tests/build_test_matrix.py"
