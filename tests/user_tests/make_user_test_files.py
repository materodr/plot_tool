"""Generate the sample files used to test plot_tool by hand.

Run from the repository root:

    python tests/user_tests/make_user_test_files.py [--hdf5-only]

It writes two folders next to this script:
- ``good/``: files the app must open (at least one per supported format,
  PCR-00032);
- ``bad/``: files the app must refuse, each with a different File Open
  Error box message.

The HDF5 files need h5py. Without it the other files are still written
and the HDF5 ones are skipped with a message. ``--hdf5-only`` writes only
the HDF5 files; CI uses it to add them to a pull request branch when
``good/signals.h5`` is missing (see .github/workflows/tests.yml).

The files are generated, not tested, so this script is not named
``test_*.py`` and is not run by tests/build_test_matrix.py.
"""

import argparse
import importlib.util
import os

import numpy as np
import pandas as pd
import scipy.io

USER_TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_COUNT_I = 5000
DURATION_S = 10.0
RANDOM_SEED_I = 1
# LLFR-00134: the good HDF5 file keeps "Time" and these signals at the
# top level; the other signals go into groups, by this group path.
HDF5_TOP_LEVEL_SET = {"Time", "Sine_1Hz", "Cosine_1Hz", "Ramp", "Noise"}
HDF5_GROUP_DICT = {
    "Sine_3Hz": "waves", "Square_0p5Hz": "waves", "Sawtooth_2Hz": "waves",
    "Damped_sine": "waves/decaying", "Step_at_5s": "events",
    "Temperature": "sensors", "Pressure": "sensors"}


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


def vehicle_signals(time_array) -> dict:
    """Build the signals of a short vehicle run, for vehicle_run.csv.

    Inputs:
        time_array: the "Time" samples of sample_signals, in seconds.
    Outputs: a dict from signal name to a numpy array with one sample per
        time sample. It holds "Time" and 11 other signals, none of them
        with the name of a signal of sample_signals (HLFR-00116), so that
        the file can be opened together with the other good files.
    """
    random_generator = np.random.default_rng(RANDOM_SEED_I + 1)
    # The driver's inputs: two accelerations, each ended by a braking.
    throttle_array = np.interp(
        time_array, [0.0, 0.5, 3.0, 4.0, 4.2, 5.5, 6.0, 8.0, 8.2, 10.0],
        [0.0, 80.0, 90.0, 40.0, 0.0, 0.0, 70.0, 85.0, 0.0, 0.0])
    brake_array = (((time_array >= 4.3) & (time_array < 5.3))
                   | ((time_array >= 8.3) & (time_array < 9.3))).astype(float)
    # The speed follows the inputs, with a drag that grows with the speed.
    time_step_s = float(time_array[1] - time_array[0])
    speed_list = [0.0]
    for sample_index_i in range(1, len(time_array)):
        speed_m_per_s = speed_list[-1]
        acceleration_f = (0.1 * throttle_array[sample_index_i]
                          - 8.0 * brake_array[sample_index_i]
                          - 0.05 * speed_m_per_s)
        speed_list.append(max(0.0, speed_m_per_s
                              + acceleration_f * time_step_s))
    speed_array = np.array(speed_list)
    speed_kmh_array = 3.6 * speed_array
    # The gear, and the engine speed that follows from it.
    gear_array = np.digitize(speed_kmh_array, [25.0, 50.0, 75.0]) + 1
    rpm_per_kmh_array = np.array([130.0, 75.0, 50.0, 38.0])[gear_array - 1]
    engine_speed_array = 800.0 + rpm_per_kmh_array * speed_kmh_array
    current_array = (2.0 * throttle_array
                     + random_generator.normal(0.0, 3.0, len(time_array)))
    signal_dict = {
        "Time": time_array,
        "Vehicle_Speed_kmh": speed_kmh_array,
        "Engine_Speed_rpm": engine_speed_array,
        "Gear": gear_array.astype(float),
        "Throttle_pct": throttle_array,
        "Brake_Active": brake_array,
        "Longitudinal_Accel_mps2": np.gradient(speed_array, time_array),
        "Oil_Pressure_bar": 1.5 + 0.0007 * engine_speed_array,
        "Coolant_Temp_C": 82.0 + 1.2 * time_array / time_array[-1],
        "Battery_Voltage_V": 13.8 - 0.004 * current_array,
        "Motor_Current_A": current_array,
        "Wheel_Vibration_g": (
            (0.02 + 0.002 * speed_kmh_array)
            * np.sin(2 * np.pi * 40.0 * time_array)),
    }
    return signal_dict


def solar_inverter_signals(time_array) -> dict:
    """Build the signals of a solar inverter, for solar_inverter_run.csv.

    Inputs:
        time_array: the "Time" samples of sample_signals, in seconds.
    Outputs: a dict from signal name to a numpy array with one sample per
        time sample. It holds "Time" and 11 other signals, none of them
        with the name of a signal of sample_signals or vehicle_signals
        (HLFR-00116).
    """
    random_generator = np.random.default_rng(RANDOM_SEED_I + 2)
    time_step_s = float(time_array[1] - time_array[0])
    # A passing cloud around 4.5 s and a short grid fault at 7.5 s.
    cloud_array = 0.55 * np.exp(-((time_array - 4.5) / 0.9) ** 2)
    fault_array = ((time_array >= 7.5) & (time_array < 7.8)).astype(float)
    irradiance_array = (950 * (1 - cloud_array)
                        + random_generator.normal(0, 4, time_array.size))
    panel_temperature_array = 45 + 0.0015 * time_step_s * np.cumsum(
        irradiance_array - 700)
    dc_power_array = (0.05 * irradiance_array
                      * (1 - 0.004 * (panel_temperature_array - 25)))
    efficiency_array = (97 - 2.5 * np.exp(-dc_power_array / 15)
                        - 40 * fault_array)
    active_power_array = dc_power_array * efficiency_array / 100
    frequency_array = (50 + 0.02 * np.sin(2 * np.pi * 0.3 * time_array)
                       - 0.4 * fault_array)
    # The voltage and the current are sine waves at the grid frequency.
    rms_voltage_array = 230 * (1 - 0.35 * fault_array)
    phase_array = 2 * np.pi * time_step_s * np.cumsum(frequency_array)
    rms_current_array = 1000 * active_power_array / (3 * rms_voltage_array)
    signal_dict = {
        "Time": time_array,
        "Grid_Voltage_V": (np.sqrt(2) * rms_voltage_array
                           * np.sin(phase_array)),
        "Grid_Current_A": (np.sqrt(2) * rms_current_array
                           * np.sin(phase_array - 0.15)),
        "Grid_Frequency_Hz": frequency_array,
        "Active_Power_kW": active_power_array,
        "Reactive_Power_kvar": 0.15 * active_power_array + 6 * fault_array,
        "DC_Bus_Voltage_V": (720 - 0.6 * (dc_power_array - 40)
                             + 45 * fault_array),
        "Irradiance_Wm2": irradiance_array,
        "Panel_Temp_C": panel_temperature_array,
        "Inverter_Efficiency_pct": efficiency_array,
        "Harmonic_Distortion_pct": (
            1.8 + 0.08 * (47 - np.minimum(active_power_array, 47))
            + 6 * fault_array),
        "Fault_Flag": fault_array,
    }
    return signal_dict


def write_good_files(folder_str: str, signal_dict: dict) -> None:
    """Write one file per supported format, each of which must open.

    Inputs:
        folder_str: the folder to write into; it must exist.
        signal_dict: the signals returned by sample_signals.
    Outputs: none. Writes ten files into folder_str.
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
    # LLFR-00991, LLFR-00992, LLFR-00993, LLFR-00063: signals in nested
    # scalar structures, named by their path ("car/engine/speed"); a
    # "Time" field inside a structure is an ordinary signal; a struct
    # array, a cell array and a matrix inside the structures are ignored.
    scipy.io.savemat(os.path.join(folder_str, "nested_structures.mat"),
                     nested_mat_variables(signal_dict))
    # HLFR-00008: a small file with the minimum useful content.
    small_df = signal_df[["Time", "Sine_1Hz", "Cosine_1Hz"]].iloc[:11]
    small_df.round(4).to_csv(os.path.join(folder_str, "small_3_signals.csv"),
                             index=False)
    # LLFR-00053: "time" is the time signal (any letter case).
    signal_df.rename(columns={"Time": "time"}).to_csv(
        os.path.join(folder_str, "lowercase_time.csv"), index=False)
    # HLFR-00070, LLFR-00325, LLFR-00329: no signal is named "Time", so
    # the app asks for the time signal; "t_s" (and "Ramp") always
    # increase, the other signals are refused.
    signal_df.rename(columns={"Time": "t_s"}).to_csv(
        os.path.join(folder_str, "time_signal_to_choose.csv"), index=False)
    # HLFR-00116: other signals over the same time, to plot together with
    # the signals of the other good files.
    pd.DataFrame(vehicle_signals(signal_dict["Time"])).to_csv(
        os.path.join(folder_str, "vehicle_run.csv"), index=False)
    pd.DataFrame(solar_inverter_signals(signal_dict["Time"])).to_csv(
        os.path.join(folder_str, "solar_inverter_run.csv"), index=False)


def nested_mat_variables(signal_dict: dict) -> dict:
    """Build the variables of good/nested_structures.mat.

    Inputs:
        signal_dict: the signals returned by sample_signals.
    Outputs: a dict variable name -> value for scipy.io.savemat, where a
        dict is saved as a scalar structure. It holds "Time" and
        "Sine_1Hz" at the top level, the other signals in structures up
        to three levels deep, and values that must be ignored.
    """
    # LLFR-00063: a 1x2 struct array and a 1x2 cell array, ignored with
    # everything they hold.
    struct_array = np.empty((1, 2), dtype=[("speed", "O")])
    for index_i in range(2):
        struct_array[0, index_i]["speed"] = signal_dict["Ramp"]
    cell_array = np.empty((1, 2), dtype=object)
    cell_array[0, 0] = signal_dict["Noise"]
    cell_array[0, 1] = {"hidden": signal_dict["Noise"]}
    # LLFR-00991: "Ramp" as a 1xN row and "Pressure" as an Nx1 column.
    return {
        "Time": signal_dict["Time"],
        "Sine_1Hz": signal_dict["Sine_1Hz"],
        "waves": {
            "Cosine_1Hz": signal_dict["Cosine_1Hz"],
            "Sine_3Hz": signal_dict["Sine_3Hz"],
            "decaying": {"Damped_sine": signal_dict["Damped_sine"]},
        },
        "car": {
            "engine": {
                "Time": signal_dict["Time"],
                "oil": {"Temperature": signal_dict["Temperature"]},
                "Pressure": signal_dict["Pressure"].reshape(-1, 1),
            },
            "Ramp": signal_dict["Ramp"].reshape(1, -1),
            "runs": struct_array,
            "notes": cell_array,
            "calibration": np.ones((3, 3)),
            "label": "sample car",
        },
    }


def write_bad_files(folder_str: str, signal_dict: dict) -> None:
    """Write files that the app must refuse to open.

    Inputs:
        folder_str: the folder to write into; it must exist.
        signal_dict: the signals returned by sample_signals.
    Outputs: none. Writes eight files into folder_str.
    """
    signal_df = pd.DataFrame(signal_dict)
    # HLFR-00008, LLFR-00012: fewer than two signals.
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


def write_hdf5_files(good_folder_str: str, bad_folder_str: str,
                     signal_dict: dict) -> None:
    """Write the HDF5 sample files (PCR-00032).

    Inputs:
        good_folder_str: folder of the files that must open.
        bad_folder_str: folder of the files that must be refused.
        signal_dict: the signals returned by sample_signals.
    Outputs: none. Writes good/signals.h5, good/time_in_group.h5 and
        bad/corrupt.h5. Needs h5py.
    """
    import h5py
    # LLFR-00134: "Time" at the top level, some signals in groups (named
    # by their path), one stored as a 1xN row, one as an Nx1 column and
    # one as integers.
    with h5py.File(os.path.join(good_folder_str, "signals.h5"),
                   "w") as hdf5_file:
        for name_str, signal_array in signal_dict.items():
            group_str = HDF5_GROUP_DICT.get(name_str, "")
            path_str = f"{group_str}/{name_str}" if group_str else name_str
            if name_str == "Ramp":
                signal_array = signal_array.reshape(1, -1)
            elif name_str == "Pressure":
                signal_array = signal_array.reshape(-1, 1)
            elif name_str == "Step_at_5s":
                signal_array = signal_array.astype(np.int32)
            hdf5_file.create_dataset(path_str, data=signal_array,
                                     track_times=False)
        # LLFR-00135: datasets that must be ignored: a 2-D matrix, a
        # text, a scalar and a boolean vector.
        hdf5_file.create_dataset("matrix_2d", data=np.ones((3, 3)),
                                 track_times=False)
        hdf5_file.create_dataset("description", data="sample signals",
                                 track_times=False)
        hdf5_file.create_dataset("sensors/calibration_gain", data=1.5,
                                 track_times=False)
        hdf5_file.create_dataset(
            "events/flags", data=np.zeros(SAMPLE_COUNT_I, dtype=bool),
            track_times=False)
    # LLFR-00330: a "Time" inside a group is not found as the time
    # signal, so the app asks for it (LLFR-00325); "run/Time" can be
    # chosen.
    with h5py.File(os.path.join(good_folder_str, "time_in_group.h5"),
                   "w") as hdf5_file:
        hdf5_file.create_dataset("run/Time", data=signal_dict["Time"],
                                 track_times=False)
        hdf5_file.create_dataset("run/Sine_1Hz",
                                 data=signal_dict["Sine_1Hz"],
                                 track_times=False)
    # LLFR-00008: an .h5 file whose content is not HDF5.
    with open(os.path.join(bad_folder_str, "corrupt.h5"),
              "wb") as binary_file:
        binary_file.write(b"not an hdf5 file " * 50)


def main() -> None:
    """Create the good/ and bad/ folders and write the sample files.

    Inputs: the optional command-line flag --hdf5-only.
    Outputs: none. Prints the folder the files were written to.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hdf5-only", action="store_true",
                        help="write only the HDF5 sample files")
    argument_namespace = parser.parse_args()
    signal_dict = sample_signals()
    good_folder_str = os.path.join(USER_TESTS_FOLDER_STR, "good")
    bad_folder_str = os.path.join(USER_TESTS_FOLDER_STR, "bad")
    os.makedirs(good_folder_str, exist_ok=True)
    os.makedirs(bad_folder_str, exist_ok=True)
    if not argument_namespace.hdf5_only:
        write_good_files(good_folder_str, signal_dict)
        write_bad_files(bad_folder_str, signal_dict)
    # PCR-00032: the HDF5 files need h5py.
    if importlib.util.find_spec("h5py") is not None:
        write_hdf5_files(good_folder_str, bad_folder_str, signal_dict)
    elif argument_namespace.hdf5_only:
        raise SystemExit("h5py is not installed: no HDF5 file written.")
    else:
        print("h5py is not installed: the HDF5 files were not written.")
    print(f"Sample files written to {USER_TESTS_FOLDER_STR}")


if __name__ == "__main__":
    main()
