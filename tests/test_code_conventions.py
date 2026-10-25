"""Checks that the code follows the code and organization requirements.

The checks read the source files with ``ast`` and cover:
- COR-00017: every class and function in src and tests has a docstring;
- COR-00010: every function in src names at least one LLFR;
- COR-00013: every variable name is shorter than 40 characters;
- COR-00014 and COR-00015: a variable whose type is known from its type
  annotation or from the value assigned to it ends with the matching
  suffix (floats may use an SI unit symbol instead of ``_f``).

The type is only checked where it can be read from the code: literal
values, common built-in calls, numpy and pandas constructors, and type
annotations. Names of other objects (widgets, model objects) are only
checked for length.
"""

import ast
import os
import re
import unittest

from tests.support import REPOSITORY_ROOT_STR, covers

CHECKED_FOLDER_LIST = ["src", "tests"]
MAXIMUM_NAME_LENGTH_I = 40
LLFR_PATTERN_STR = r"LLFR-\d{5}"

# COR-00014: suffix for each type.
TYPE_SUFFIX_DICT = {
    "int": ("_i",),
    "float": ("_f",),
    "str": ("_str",),
    "bool": ("_b",),
    "list": ("_list",),
    "dict": ("_dict",),
    "tuple": ("_tuple",),
    "set": ("_set",),
    "ndarray": ("_array",),
    "DataFrame": ("_df",),
}

# COR-00015: SI unit symbols allowed instead of _f for physical floats.
SI_UNIT_SUFFIX_TUPLE = (
    "_s", "_m", "_kg", "_g", "_a", "_k", "_mol", "_cd", "_hz", "_n",
    "_pa", "_j", "_w", "_c", "_v", "_ohm", "_rad", "_sr", "_t", "_wb",
    "_lm", "_lx", "_ms", "_mm", "_km", "_px",
)

BUILTIN_CALL_TYPE_DICT = {
    "len": "int", "int": "int", "float": "float", "str": "str",
    "bool": "bool", "list": "list", "dict": "dict", "tuple": "tuple",
    "set": "set", "sorted": "list", "round": "float",
}
NUMPY_ARRAY_FUNCTION_SET = {
    "array", "asarray", "zeros", "ones", "arange", "linspace", "empty",
    "full", "concatenate",
}
PANDAS_FRAME_FUNCTION_SET = {"DataFrame", "read_csv", "read_excel"}
IGNORED_NAME_SET = {"self", "cls", "_"}


def python_file_list() -> list:
    """Return the paths of all Python files in the checked folders.

    Inputs: none.
    Outputs: a sorted list of absolute file paths.
    """
    path_list = []
    for folder_str in CHECKED_FOLDER_LIST:
        root_str = os.path.join(REPOSITORY_ROOT_STR, folder_str)
        for directory_str, _, file_name_list in os.walk(root_str):
            for file_name_str in file_name_list:
                if file_name_str.endswith(".py"):
                    path_list.append(os.path.join(directory_str,
                                                  file_name_str))
    return sorted(path_list)


def parse_file(path_str: str) -> tuple:
    """Read and parse one Python file.

    Inputs:
        path_str: absolute path of the file.
    Outputs: a tuple (source text, ast.Module).
    """
    with open(path_str, encoding="utf-8") as source_file:
        source_str = source_file.read()
    return source_str, ast.parse(source_str, filename=path_str)


def annotation_type_name(annotation) -> str:
    """Return the type name of a type annotation, if it is a known type.

    Inputs:
        annotation: an ast expression used as a type annotation.
    Outputs: a key of TYPE_SUFFIX_DICT, or an empty string when the
        annotation is not one of those types.
    """
    if isinstance(annotation, ast.Subscript):
        annotation = annotation.value
    if isinstance(annotation, ast.Name):
        name_str = annotation.id
    elif isinstance(annotation, ast.Attribute):
        name_str = annotation.attr
    else:
        return ""
    return name_str if name_str in TYPE_SUFFIX_DICT else ""


def value_type_name(value) -> str:
    """Return the type of an assigned value, when it can be read.

    Inputs:
        value: the ast expression on the right side of an assignment.
    Outputs: a key of TYPE_SUFFIX_DICT, or an empty string when the type
        can't be read from the expression.
    """
    if isinstance(value, ast.Constant):
        if isinstance(value.value, bool):
            return "bool"
        for type_name_str in ("int", "float", "str"):
            if type(value.value).__name__ == type_name_str:
                return type_name_str
        return ""
    simple_type_dict = {
        ast.JoinedStr: "str", ast.List: "list", ast.ListComp: "list",
        ast.Dict: "dict", ast.DictComp: "dict", ast.Tuple: "tuple",
        ast.Set: "set", ast.SetComp: "set", ast.Compare: "bool",
    }
    for node_type, type_name_str in simple_type_dict.items():
        if isinstance(value, node_type):
            return type_name_str
    if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.Not):
        return "bool"
    if isinstance(value, ast.Call):
        return call_type_name(value)
    return ""


def call_type_name(call) -> str:
    """Return the type returned by a known call.

    Inputs:
        call: an ast.Call expression.
    Outputs: a key of TYPE_SUFFIX_DICT, or an empty string.
    """
    function = call.func
    if isinstance(function, ast.Name):
        return BUILTIN_CALL_TYPE_DICT.get(function.id, "")
    if isinstance(function, ast.Attribute) and isinstance(
            function.value, ast.Name):
        module_str = function.value.id
        if (module_str in ("np", "numpy")
                and function.attr in NUMPY_ARRAY_FUNCTION_SET):
            return "ndarray"
        if (module_str in ("pd", "pandas")
                and function.attr in PANDAS_FRAME_FUNCTION_SET):
            return "DataFrame"
    return ""


def target_name(target) -> str:
    """Return the variable name of an assignment target.

    Inputs:
        target: an ast assignment target.
    Outputs: the name for a plain name or a ``self.<name>`` attribute,
        otherwise an empty string.
    """
    if isinstance(target, ast.Name):
        return target.id
    if (isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"):
        return target.attr
    return ""


def named_values(tree) -> list:
    """List every variable name in a module with its readable type.

    Inputs:
        tree: an ast.Module.
    Outputs: a list of tuples (name, type name or "", line number).
    """
    found_list = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            type_name_str = value_type_name(node.value)
            for target in node.targets:
                if isinstance(target, ast.Tuple):
                    for element in target.elts:
                        found_list.append((target_name(element), "",
                                           node.lineno))
                else:
                    found_list.append((target_name(target), type_name_str,
                                       node.lineno))
        elif isinstance(node, ast.AnnAssign):
            found_list.append((target_name(node.target),
                               annotation_type_name(node.annotation),
                               node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arguments = node.args
            for argument in (arguments.posonlyargs + arguments.args
                             + arguments.kwonlyargs):
                found_list.append((argument.arg,
                                   annotation_type_name(argument.annotation),
                                   node.lineno))
        elif isinstance(node, ast.For) and isinstance(node.target,
                                                      ast.Name):
            found_list.append((node.target.id, "", node.lineno))
    return [entry for entry in found_list
            if entry[0] and entry[0] not in IGNORED_NAME_SET
            and not entry[0].startswith("__")]


def suffix_matches(name_str: str, type_name_str: str) -> bool:
    """Tell whether a name ends with the suffix its type requires.

    Inputs:
        name_str: the variable name.
        type_name_str: a key of TYPE_SUFFIX_DICT.
    Outputs: True when the suffix is right (case-insensitive, so that
        constants such as MAXIMUM_PLOTS_I also match).
    """
    allowed_tuple = TYPE_SUFFIX_DICT[type_name_str]
    if type_name_str == "float":
        allowed_tuple = allowed_tuple + SI_UNIT_SUFFIX_TUPLE
    return name_str.lower().endswith(allowed_tuple)


def relative_path(path_str: str) -> str:
    """Return a path relative to the repository root, for messages.

    Inputs:
        path_str: absolute file path.
    Outputs: the path relative to the repository root.
    """
    return os.path.relpath(path_str, REPOSITORY_ROOT_STR)


class CodeConventionsTest(unittest.TestCase):
    """Check COR-00010, COR-00013, COR-00014, COR-00015 and COR-00017."""

    @covers("COR-00017")
    def test_every_class_and_function_has_a_docstring(self) -> None:
        """Every class and function in src and tests has a docstring.

        Inputs: none.
        Outputs: none.
        """
        missing_list = []
        for path_str in python_file_list():
            source_str, tree = parse_file(path_str)
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef,
                                     ast.AsyncFunctionDef)):
                    if not ast.get_docstring(node):
                        missing_list.append(
                            f"{relative_path(path_str)}:{node.lineno} "
                            f"{node.name}")
        self.assertEqual(missing_list, [], "Missing docstrings")

    @covers("COR-00010")
    def test_every_source_function_names_an_llfr(self) -> None:
        """Every function in src names at least one LLFR in its text.

        Inputs: none.
        Outputs: none.
        """
        missing_list = []
        source_root_str = os.path.join(REPOSITORY_ROOT_STR, "src")
        for path_str in python_file_list():
            if not path_str.startswith(source_root_str):
                continue
            source_str, tree = parse_file(path_str)
            line_list = source_str.splitlines()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef,
                                     ast.AsyncFunctionDef)):
                    body_str = "\n".join(
                        line_list[node.lineno - 1:node.end_lineno])
                    if not re.search(LLFR_PATTERN_STR, body_str):
                        missing_list.append(
                            f"{relative_path(path_str)}:{node.lineno} "
                            f"{node.name}")
        self.assertEqual(missing_list, [], "Functions without an LLFR ID")

    @covers("COR-00013")
    def test_variable_names_are_shorter_than_40_characters(self) -> None:
        """Every variable name has fewer than 40 characters.

        Inputs: none.
        Outputs: none.
        """
        long_list = []
        for path_str in python_file_list():
            source_str, tree = parse_file(path_str)
            for name_str, _, line_i in named_values(tree):
                if len(name_str) >= MAXIMUM_NAME_LENGTH_I:
                    long_list.append(
                        f"{relative_path(path_str)}:{line_i} {name_str}")
        self.assertEqual(long_list, [], "Names of 40 characters or more")

    @covers("COR-00014", "COR-00015")
    def test_variable_names_end_with_their_type_suffix(self) -> None:
        """Variables of a readable type end with the matching suffix.

        Inputs: none.
        Outputs: none.
        """
        wrong_list = []
        for path_str in python_file_list():
            source_str, tree = parse_file(path_str)
            for name_str, type_name_str, line_i in named_values(tree):
                if type_name_str and not suffix_matches(name_str,
                                                        type_name_str):
                    wrong_list.append(
                        f"{relative_path(path_str)}:{line_i} {name_str} "
                        f"({type_name_str})")
        self.assertEqual(wrong_list, [], "Names without their type suffix")


if __name__ == "__main__":
    unittest.main()
