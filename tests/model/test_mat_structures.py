"""Tests for the signals read from structures in MAT files.

A field of a scalar (1x1) structure that holds a one-dimensional numeric
array is a signal named by its path, at any depth (LLFR-00991, in the
order of LLFR-00992). Struct arrays, cell arrays, matrices, text and
other types are ignored with everything they hold (LLFR-00063), the
time signal is only a top-level variable (LLFR-00993), and the checks
of HLFR-00008 and HLFR-00009 apply only to the signals read
(LLFR-00452). Every file is written inside a temporary folder; no Qt is
needed.
"""

import os
import tempfile
import unittest

import numpy as np
import scipy.io

from tests.support import covers

from model.data_files import DataFileSet, without_prefix
from model.errors import (
    SAMPLE_COUNT_CHECK_STR, SIGNAL_COUNT_CHECK_STR, ContentCheckError,
    FileReadError)
from model.file_loader import (
    collect_mat_signals, load_signal_file, mat_structure_field_list)
from model.file_writer import MAT_FORMAT_STR, saved_name_list
from model.signal_search import search_prefixed_signals
from model.synthetic_signals import SyntheticSignalStore

SAMPLE_COUNT_I = 4


def struct_array(field_name_str: str, element_count_i: int) -> np.ndarray:
    """Build a 1xN MATLAB struct array for scipy.io.savemat.

    Inputs:
        field_name_str: the name of its only field.
        element_count_i: the number of structures in the array.
    Outputs: a record array of shape (1, element_count_i) whose every
        field holds a vector of SAMPLE_COUNT_I samples.
    """
    record_array = np.empty((1, element_count_i),
                            dtype=[(field_name_str, "O")])
    for index_i in range(element_count_i):
        record_array[0, index_i][field_name_str] = np.arange(
            float(SAMPLE_COUNT_I))
    return record_array


def cell_array(*element_tuple) -> np.ndarray:
    """Build a 1xN MATLAB cell array for scipy.io.savemat.

    Inputs:
        element_tuple: the values of the cells.
    Outputs: an object array of shape (1, N).
    """
    object_array = np.empty((1, len(element_tuple)), dtype=object)
    for index_i, element in enumerate(element_tuple):
        object_array[0, index_i] = element
    return object_array


class MatStructureTest(unittest.TestCase):
    """Base class with a temporary folder and a MAT file writer."""

    def setUp(self) -> None:
        """Create the temporary folder.

        Inputs: none.
        Outputs: none.
        """
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def write_mat(self, variable_dict: dict) -> str:
        """Write a .mat file with scipy.io.savemat.

        Inputs:
            variable_dict: variable name -> value; a dict is saved as a
                structure.
        Outputs: the path of the file.
        """
        path_str = os.path.join(self.folder.name, "data.mat")
        scipy.io.savemat(path_str, variable_dict)
        return path_str


class NestedStructureTest(MatStructureTest):
    """Fields of scalar structures are signals named by their path."""

    @covers("LLFR-00991", "LLFR-00992", "LLFR-00062", "HLFR-00005")
    def test_nested_fields_named_by_path_in_file_order(self) -> None:
        """Fields at every depth are read, named and ordered by path.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.arange(float(SAMPLE_COUNT_I))
        path_str = self.write_mat({
            "Time": time_array,
            "car": {"engine": {"speed": time_array * 2,
                               "oil": {"temperature": time_array + 90}},
                    "mass": time_array * 0 + 1200},
            "Gear": np.array([1, 2, 3, 4], dtype=np.int8),
            "engine": {"speed": time_array * 3},
        })
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list, [
            "Time", "car/engine/speed", "car/engine/oil/temperature",
            "car/mass", "Gear", "engine/speed"])
        np.testing.assert_array_equal(
            signal_file.signal_array("car/engine/oil/temperature"),
            time_array + 90)
        np.testing.assert_array_equal(
            signal_file.signal_array("engine/speed"), time_array * 3)
        self.assertEqual(signal_file.time_signal_name_str, "Time")

    @covers("LLFR-00991")
    def test_row_column_and_integer_fields(self) -> None:
        """1xN, Nx1 and integer fields are float64 1-D signals.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "Time": np.arange(3.0),
            "log": {"row": np.array([[1.0, 2.0, 3.0]]),
                    "column": np.array([[4.0], [5.0], [6.0]]),
                    "count": np.array([7, 8, 9], dtype=np.uint16)},
        })
        signal_file = load_signal_file(path_str)
        for name_str, expected_list in (("log/row", [1, 2, 3]),
                                        ("log/column", [4, 5, 6]),
                                        ("log/count", [7, 8, 9])):
            signal_array = signal_file.signal_array(name_str)
            self.assertEqual(signal_array.dtype, np.float64)
            self.assertEqual(signal_array.shape, (3,))
            np.testing.assert_array_equal(signal_array, expected_list)

    @covers("LLFR-00991", "LLFR-00008")
    def test_non_finite_field_names_its_path(self) -> None:
        """A NaN in a field gives a read error naming the field's path.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "Time": np.arange(3.0),
            "car": {"engine": {"speed": np.array([1.0, np.nan, 2.0])}}})
        with self.assertRaises(FileReadError) as context:
            load_signal_file(path_str)
        self.assertIn("'car/engine/speed' sample 2", str(context.exception))


class IgnoredTypeTest(MatStructureTest):
    """Only scalar structures are walked (LLFR-00063)."""

    @covers("LLFR-00063", "LLFR-00991")
    def test_other_types_ignored_at_every_level(self) -> None:
        """Struct arrays, cells, matrices and text are ignored anywhere.

        Inputs: none.
        Outputs: none.
        """
        vector_array = np.arange(float(SAMPLE_COUNT_I))
        ignored_dict = {
            "matrix": np.ones((3, 3)),
            "label": "abc",
            "complex": np.array([1 + 2j, 3, 4, 5]),
            "empty": np.array([]),
            "runs": struct_array("speed", 2),
            "cells": cell_array(vector_array, vector_array),
            "boxed": cell_array({"speed": vector_array}),
        }
        path_str = self.write_mat({
            "Time": vector_array,
            "top_runs": struct_array("speed", 3),
            "top_cells": cell_array({"speed": vector_array}),
            "car": dict(ignored_dict, speed=vector_array,
                        engine=dict(ignored_dict, rpm=vector_array)),
        })
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list,
                         ["Time", "car/speed", "car/engine/rpm"])

    @covers("LLFR-00063", "LLFR-00991")
    def test_struct_array_of_one_element_is_a_structure(self) -> None:
        """A 1x1 struct array is a scalar structure; a 1x1 cell is not.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "Time": np.arange(float(SAMPLE_COUNT_I)),
            "single": struct_array("speed", 1),
            "boxed": cell_array(struct_array("speed", 1)),
        })
        self.assertEqual(load_signal_file(path_str).signal_name_list,
                         ["Time", "single/speed"])

    @covers("LLFR-00063", "LLFR-00991")
    def test_both_scipy_structure_forms(self) -> None:
        """Record arrays and mat_struct objects give the same signals.

        Inputs: none.
        Outputs: none.
        """
        vector_array = np.arange(float(SAMPLE_COUNT_I))
        path_str = self.write_mat({
            "Time": vector_array,
            "car": {"engine": {"speed": vector_array},
                    "runs": struct_array("speed", 2),
                    "boxed": cell_array({"speed": vector_array})},
        })
        expected_list = ["Time", "car/engine/speed"]
        for option_dict in ({"struct_as_record": True},
                            {"struct_as_record": False}):
            with self.subTest(option_dict=option_dict):
                variable_dict = scipy.io.loadmat(path_str, **option_dict)
                signal_dict = {}
                for name_str, value in variable_dict.items():
                    if not name_str.startswith("__"):
                        collect_mat_signals("data.mat", name_str, value,
                                            signal_dict)
                self.assertEqual(list(signal_dict), expected_list)
        # LLFR-00991: squeezed forms (a single record or mat_struct) are
        # structures too.
        for option_bool in (True, False):
            with self.subTest(struct_as_record=option_bool):
                car = scipy.io.loadmat(path_str, squeeze_me=True,
                                       struct_as_record=option_bool)["car"]
                field_list = mat_structure_field_list(car)
                self.assertEqual([name_str for name_str, _ in field_list],
                                 ["engine", "runs", "boxed"])
        self.assertIsNone(mat_structure_field_list(np.ones((2, 2))))
        self.assertIsNone(mat_structure_field_list("text"))


class StructureTimeSignalTest(MatStructureTest):
    """A Time field inside a structure is an ordinary signal."""

    @covers("LLFR-00993", "LLFR-00053", "HLFR-00006")
    def test_time_field_is_an_ordinary_signal(self) -> None:
        """The top-level Time wins; engine/Time is just another signal.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "engine": {"Time": np.arange(3.0) * 10,
                       "time": np.arange(3.0) * 20},
            "Time": np.arange(3.0)})
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.time_signal_name_str, "Time")
        self.assertFalse(signal_file.needs_time_signal_choice_b)
        self.assertEqual(signal_file.signal_name_list,
                         ["engine/Time", "engine/time", "Time"])

    @covers("LLFR-00993", "LLFR-00325", "HLFR-00070")
    def test_only_time_inside_structure_asks_for_it(self) -> None:
        """With Time only in a structure, the user chooses the time.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "run": {"Time": np.arange(3.0), "speed": np.ones(3)}})
        signal_file = load_signal_file(path_str)
        self.assertTrue(signal_file.needs_time_signal_choice_b)
        self.assertEqual(signal_file.choose_time_signal("run/Time"), "")
        self.assertEqual(signal_file.time_signal_name_str, "run/Time")

    @covers("LLFR-00993", "LLFR-00991", "LLFR-00325")
    def test_structure_variable_named_time(self) -> None:
        """A top-level structure named Time is not the time signal.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "Time": {"t": np.arange(3.0), "speed": np.ones(3)}})
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list,
                         ["Time/t", "Time/speed"])
        self.assertTrue(signal_file.needs_time_signal_choice_b)


class StructureContentCheckTest(MatStructureTest):
    """HLFR-00008 and HLFR-00009 check only the signals read."""

    @covers("LLFR-00452", "LLFR-00063", "HLFR-00009")
    def test_ignored_fields_skip_the_sample_count_check(self) -> None:
        """Ignored fields of other lengths don't fail HLFR-00009.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "Time": np.arange(4.0),
            "car": {"speed": np.arange(4.0), "table": np.ones((2, 7)),
                    "runs": struct_array("speed", 2),
                    "cells": cell_array(np.arange(9.0))}})
        self.assertEqual(load_signal_file(path_str).signal_name_list,
                         ["Time", "car/speed"])

    @covers("LLFR-00452", "LLFR-00991", "LLFR-00012", "HLFR-00009")
    def test_field_of_another_length_fails(self) -> None:
        """A field of another sample count fails HLFR-00009 by path.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "Time": np.arange(5.0),
            "car": {"engine": {"speed": np.arange(3.0)}}})
        with self.assertRaises(ContentCheckError) as context:
            load_signal_file(path_str)
        self.assertEqual(context.exception.failed_check_str,
                         SAMPLE_COUNT_CHECK_STR)
        self.assertIn("'car/engine/speed' has 3", str(context.exception))

    @covers("LLFR-00452", "LLFR-00063", "LLFR-00012", "HLFR-00008")
    def test_structure_without_signals_fails_signal_count(self) -> None:
        """A structure with no signal field adds no signal (HLFR-00008).

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "Time": np.arange(3.0),
            "settings": {"table": np.ones((3, 3)), "name": "run 1",
                         "inner": {"runs": struct_array("speed", 2)}}})
        with self.assertRaises(ContentCheckError) as context:
            load_signal_file(path_str)
        self.assertEqual(context.exception.failed_check_str,
                         SIGNAL_COUNT_CHECK_STR)

    @covers("LLFR-00452", "LLFR-00991", "HLFR-00008")
    def test_structure_fields_meet_the_signal_count(self) -> None:
        """Time and one structure field are enough to open the file.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat({
            "Time": np.arange(3.0), "car": {"speed": np.ones(3)}})
        self.assertEqual(load_signal_file(path_str).signal_name_list,
                         ["Time", "car/speed"])


class StructureNameUseTest(MatStructureTest):
    """The slashed names work with the rest of the app."""

    def load_data_files(self) -> DataFileSet:
        """Open a MAT file with nested structures as data file 1.

        Inputs: none.
        Outputs: the DataFileSet that holds it.
        """
        path_str = self.write_mat({
            "Time": np.arange(3.0),
            "car": {"engine": {"speed": np.arange(3.0) * 2}}})
        data_files = DataFileSet()
        data_files.add(load_signal_file(path_str), path_str)
        return data_files

    @covers("LLFR-00991", "LLFR-00905", "LLFR-00099")
    def test_prefix_and_search(self) -> None:
        """The path gets the file prefix and is found by the search.

        Inputs: none.
        Outputs: none.
        """
        data_files = self.load_data_files()
        name_list = data_files.signal_name_list
        self.assertEqual(name_list, ["file1_Time",
                                     "file1_car/engine/speed"])
        self.assertEqual(without_prefix(name_list[1]), "car/engine/speed")
        np.testing.assert_array_equal(
            data_files.signal_array("file1_car/engine/speed"),
            [0.0, 2.0, 4.0])
        self.assertEqual(search_prefixed_signals(name_list, "engine speed"),
                         ["file1_car/engine/speed"])
        self.assertEqual(search_prefixed_signals(name_list, "car/eng"),
                         ["file1_car/engine/speed"])

    @covers("LLFR-00991", "LLFR-00240")
    def test_synthetic_signal_name(self) -> None:
        """A synthetic signal of a field keeps the path in its name.

        Inputs: none.
        Outputs: none.
        """
        store = SyntheticSignalStore()
        self.assertEqual(
            store.default_names("integral", ["file1_car/engine/speed"],
                                None),
            (1, "file1_int_car/engine/speed", "int_car/engine/speed"))

    @covers("LLFR-00991", "LLFR-00543", "LLFR-00403")
    def test_save_signals_as_mat_flattens_the_path(self) -> None:
        """Save signals writes engine/speed as the variable engine_speed.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            saved_name_list(["Time", "car/engine/speed"], "Time",
                            MAT_FORMAT_STR),
            ["Time", "car_engine_speed"])


if __name__ == "__main__":
    unittest.main()
