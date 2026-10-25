"""Generate the sample files used to test plot_tool by hand.

Run from the repository root:

    python tests/user_tests/make_user_test_files.py

It writes two folders next to this script:
- ``good/``: files the app must open (one per supported format);
- ``bad/``: files the app must refuse, each with a different File Open
  Error box message.

The files are generated, not tested, so this script is not named
``test_*.py`` and is not run by tests/build_test_matrix.py.
"""

import os

import numpy as np
import pandas as pd
import scipy.io

USER_TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_COUNT_I = 5000
DURATION_S = 10.0
RANDOM_SEED_I = 1


def sample_signals() -> dict:
    """Build the signals written to every good file.

    Inputs: none.
    Outputs: a dict from signal name to a numpy array of SAMPLE_COUNT_I
        samples. It holds "Time" in seconds and 11 other signals, more
        than the 8 predefined curve colors (LLFR-00033, LLFR-00034).
    """
    # LLFR-00068: "Time" is the x-axis, in seconds (HLFR-00007).
    time_array = np.linspace(0.0, DURATION_S, SAMPLE_COUNT_I)
    random_generator = np.random.default_rng(RANDOM_SEED_I)
    signal_dict = {
        "Time": time_array,
        "Sine_1Hz": np.sin(2 * np.pi * 1.0 * time_array),
        "Cosine_1Hz": np.cos(2 * np.pi * 1.0 * time_array),
        "Sine_3Hz": 0.5 * np.sin(2 * np.pi * 3.0 * time_array),
        "Square_0p5Hz": np.sign(np.sin(2 * np.pi * 0.5 * time_array)),
        "Sawtooth_2Hz": 2 * ((2.0 * time_array) % 1.0) - 1,
        "Ramp": time_array / DURATION_S,
        "Noise": random_generator.normal(0.0, 0.2, SAMPLE_COUNT_I),
        "Damped_sine": (np.exp(-0.3 * time_array)
                        * np.sin(2 * np.pi * 2.0 * time_array)),
        "Step_at_5s": (time_array >= 5.0).astype(float),
        "Temperature": 20 + 5 * np.sin(2 * np.pi * 0.1 * time_array),
        "Pressure": 101.3 + 0.5 * np.cos(2 * np.pi * 0.2 * time_array),
    }
    return signal_dict


def write_good_files(folder_str: str, signal_dict: dict) -> None:
    """Write one file per supported format, each of which must open.

    Inputs:
        folder_str: the folder to write into; it must exist.
        signal_dict: the signals returned by sample_signals.
    Outputs: none. Writes five files into folder_str.
    """
    signal_df = pd.DataFrame(signal_dict)
    # HLFR-00005, LLFR-00059, LLFR-00061: CSV with "," and "." decimals.
    signal_df.to_csv(os.path.join(folder_str, "signals_comma.csv"),
                     index=False)
    # LLFR-00061: CSV with ";" and "," decimals.
    signal_df.to_csv(os.path.join(folder_str, "signals_semicolon.csv"),
                     index=False, sep=";", decimal=",")
    # HLFR-00005, LLFR-00059, LLFR-00060: Excel, first sheet.
    signal_df.to_excel(os.path.join(folder_str, "signals.xlsx"),
                       index=False)
    # LLFR-00062, LLFR-00063: MAT signals plus two variables that must be
    # ignored (a text and a 2-D matrix).
    mat_variable_dict = dict(signal_dict)
    mat_variable_dict["description"] = "sample signals"
    mat_variable_dict["matrix_2d"] = np.ones((3, 3))
    scipy.io.savemat(os.path.join(folder_str, "signals.mat"),
                     mat_variable_dict)
    # HLFR-00008: a small file with the minimum useful content.
    small_df = signal_df[["Time", "Sine_1Hz", "Cosine_1Hz"]].iloc[:11]
    small_df.round(4).to_csv(os.path.join(folder_str, "small_3_signals.csv"),
                             index=False)


def write_bad_files(folder_str: str, signal_dict: dict) -> None:
    """Write files that the app must refuse to open.

    Inputs:
        folder_str: the folder to write into; it must exist.
        signal_dict: the signals returned by sample_signals.
    Outputs: none. Writes nine files into folder_str.
    """
    signal_df = pd.DataFrame(signal_dict)
    # HLFR-00008, LLFR-00012: no time signal.
    signal_df.drop(columns="Time").to_csv(
        os.path.join(folder_str, "no_time_column.csv"), index=False)
    # LLFR-00053: "time" is not "Time" (case-sensitive).
    signal_df.rename(columns={"Time": "time"}).to_csv(
        os.path.join(folder_str, "lowercase_time.csv"), index=False)
    # HLFR-00008, LLFR-00012: no signal other than "Time".
    signal_df[["Time"]].to_csv(os.path.join(folder_str, "only_time.csv"),
                               index=False)
    # LLFR-00065: empty cells, which is how a shorter column looks in CSV.
    with open(os.path.join(folder_str, "empty_cells.csv"), "w") as text_file:
        text_file.write("Time,A,B\n0.0,1,2\n0.1,3,4\n0.2,5,\n0.3,7,\n")
    # LLFR-00065: a value that is not a number.
    text_df = signal_df[["Time", "Sine_1Hz"]].iloc[:10].astype(object)
    text_df.iloc[4, 1] = "abc"
    text_df.to_csv(os.path.join(folder_str, "non_numeric_value.csv"),
                   index=False)
    # HLFR-00009, LLFR-00012: different sample counts (only MAT files can
    # hold signals of different lengths).
    scipy.io.savemat(os.path.join(folder_str, "different_lengths.mat"),
                     {"Time": signal_dict["Time"],
                      "Short": np.arange(10.0)})
    # LLFR-00011: an extension that is not supported.
    with open(os.path.join(folder_str, "unsupported_format.txt"),
              "w") as text_file:
        text_file.write("Time,A\n0,1\n1,2\n")
    # LLFR-00008: files whose content does not match their format.
    random_generator = np.random.default_rng(RANDOM_SEED_I)
    with open(os.path.join(folder_str, "corrupt.xlsx"), "wb") as binary_file:
        binary_file.write(random_generator.bytes(2048))
    with open(os.path.join(folder_str, "corrupt.mat"), "wb") as binary_file:
        binary_file.write(b"not a mat file " * 50)


def main() -> None:
    """Create the good/ and bad/ folders and write all sample files.

    Inputs: none.
    Outputs: none. Prints the folder the files were written to.
    """
    signal_dict = sample_signals()
    good_folder_str = os.path.join(USER_TESTS_FOLDER_STR, "good")
    bad_folder_str = os.path.join(USER_TESTS_FOLDER_STR, "bad")
    os.makedirs(good_folder_str, exist_ok=True)
    os.makedirs(bad_folder_str, exist_ok=True)
    write_good_files(good_folder_str, signal_dict)
    write_bad_files(bad_folder_str, signal_dict)
    print(f"Sample files written to {USER_TESTS_FOLDER_STR}")


if __name__ == "__main__":
    main()
