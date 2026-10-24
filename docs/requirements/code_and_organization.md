# Code and Organization Requirements

Prefix: `COR`. Format rules: see [README.md](README.md).

### COR-00001 Programming language
The code must be written in Python.

### COR-00002 Style guide
The code must follow the PEP 8 style guide.

### COR-00003 Design pattern
The code must follow the Model-View-Controller (MVC) design pattern.

### COR-00004 Project folder layout
The project must be kept in a folder that contains the sub-folders `src`, `tests` and `bin`.

### COR-00005 Contents of src
The `src` folder must contain all the code and other artifacts needed to run the code.

### COR-00006 Contents of tests
The `tests` folder must contain all the tests used to evaluate the code.

### COR-00007 Contents of bin
The `bin` folder must contain the standalone executables built from the code in `src` (for example with PyInstaller). Build outputs must not be committed to the repository.

### COR-00008 Layout of src
The `src` folder must contain the sub-folders `model`, `view` and `controller`.

### COR-00009 Separation of the view
The view code must be kept separate from the model and controller code.

### COR-00010 Traceability comments
The code comments, besides explaining the code, must trace each code section to at least one low-level functional requirement, using its ID (for example `# LLFR-00012`).

### COR-00011 External libraries
A new external library must only be added when there is high confidence that the current set of libraries is not enough.

### COR-00012 Meaningful names
The names of variables, classes and methods must be meaningful and self-explanatory. Unnecessary abbreviations must be avoided.

### COR-00013 Variable name length
Variable names must be shorter than 40 characters.

### COR-00014 Type suffixes
Variable names must end with a suffix that indicates the type of the variable:

| Type | Suffix |
|---|---|
| dict | `_dict` |
| float | `_f` |
| int | `_i` |
| bool | `_b` |
| str | `_str` |
| list | `_list` |
| tuple | `_tuple` |
| set | `_set` |
| pandas DataFrame | `_df` |
| numpy array | `_array` |

### COR-00015 Physical quantity suffixes
If a float variable carries a physical quantity, the `_f` suffix must be replaced by the symbol of the quantity's unit as recommended by the International System of Units (SI), for example `_s` for seconds or `_m` for meters.

### COR-00016 Language
All the code must be written in English.

### COR-00017 Docstrings
All classes and functions must have a docstring that explains their inputs, outputs and what they do.

### COR-00018 Zen of Python
The code must follow the Zen of Python guidelines.

### COR-00019 User interface library
The user interface (view) code must be written with PyQt.
