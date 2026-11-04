"""The two square pickers of the plot matrix (HLFR-00145, HLFR-00149).

- The **matrix picker** opens from "Plot matrix" in the tab menu
  (LLFR-01061). It shows 10 rows of 10 small squares; the square in row
  R and column C stands for a plot matrix of R rows and C columns
  (LLFR-01062). While the pointer is over a square, every square from
  row 1 to its row and from column 1 to its column is highlighted
  (LLFR-01063) and the text "R × C" is shown below the squares
  (LLFR-01096). The squares of the tab's current matrix are marked when
  the picker opens (LLFR-01064). A square with fewer slots than the tab
  has plots is pale and does nothing (LLFR-01071, LLFR-01072).
- The **position picker** opens from "Position" in the plot menu and in
  the area menu (LLFR-01077, LLFR-01078). It has as many rows and columns
  of squares as the tab's plot matrix, one per slot (LLFR-01079). Only
  the squares of slots that hold a plot are enabled (LLFR-01080); the
  others are pale (LLFR-01081). The square of the plot it was opened
  from is marked (LLFR-01082).

Both are popups: a click on an enabled square calls the choice function
with the row and column of the square, counted from 1, and closes the
picker (LLFR-01065, LLFR-01083); the Esc key or a click outside closes
it with no choice (LLFR-01070). Whether the choice changes anything (the
current matrix, the plot's own slot) is decided by the controller
(LLFR-01069, LLFR-01086).

The geometry of the squares is plain arithmetic (square_rect,
square_at), so tests can click a square without guessing pixels.
"""

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from model.workspace import MAXIMUM_MATRIX_SIZE_I
from view import theme

# LLFR-01062: the size of a square and the gap between two squares.
SQUARE_SIZE_I = 16
SQUARE_GAP_I = 3
# LLFR-01062: the margin around the squares.
PICKER_MARGIN_I = 8
# LLFR-01096: the height of the "R × C" text below the squares.
SIZE_TEXT_HEIGHT_I = 22
# LLFR-01096: how the size of a plot matrix is written.
MATRIX_SIZE_FORMAT_STR = "{rows} × {columns}"
# LLFR-01062, LLFR-01079: the colors of the squares.
SQUARE_COLOR_STR = theme.SURFACE_COLOR_STR
SQUARE_BORDER_COLOR_STR = theme.CONTROL_BORDER_COLOR_STR
# LLFR-01063: the highlighted squares.
HIGHLIGHT_COLOR_STR = theme.FOCUS_COLOR_STR
# LLFR-01064, LLFR-01082: the marked squares get a border of this color
# and width, drawn on top of any fill, so that a square can be pale and
# marked at once.
MARKED_COLOR_STR = theme.ACTIVE_COLOR_STR
MARK_BORDER_WIDTH_I = 2
# LLFR-01071, LLFR-01081: the pale squares.
PALE_COLOR_STR = theme.DISABLED_COLOR_STR
PALE_BORDER_COLOR_STR = theme.DISABLED_BORDER_COLOR_STR
PICKER_BACKGROUND_COLOR_STR = theme.SURFACE_COLOR_STR
PICKER_BORDER_COLOR_STR = theme.HAIRLINE_COLOR_STR
# LLFR-01096: the color of the size text.
SIZE_TEXT_COLOR_STR = theme.TEXT_COLOR_STR
# LLFR-01062: no square under the pointer.
NO_SQUARE_TUPLE = ()


def matrix_size_text(row_count_i: int, column_count_i: int) -> str:
    """Return the text of a plot matrix size, e.g. "2 × 3".

    Inputs:
        row_count_i: number of rows.
        column_count_i: number of columns.
    Outputs: the text `R × C` (LLFR-01096).
    """
    # LLFR-01096: R rows and C columns, written `R × C`.
    return MATRIX_SIZE_FORMAT_STR.format(rows=int(row_count_i),
                                         columns=int(column_count_i))


class SquarePicker(QWidget):
    """A popup of rows and columns of squares, one of which is chosen.

    Inputs:
        row_count_i: number of rows of squares.
        column_count_i: number of columns of squares.
        choice_function: function taking (row_i, column_i), counted from
            1, called when an enabled square is clicked.
        parent: optional parent widget.
    Attributes:
        hover_tuple: (row_i, column_i) of the square under the pointer,
            or NO_SQUARE_TUPLE.
        chosen_tuple: (row_i, column_i) of the clicked square, or
            NO_SQUARE_TUPLE while none was chosen.
    """

    def __init__(self, row_count_i: int, column_count_i: int,
                 choice_function, parent=None) -> None:
        """Create the picker; it is shown by show_at.

        Inputs:
            row_count_i: see the class docstring.
            column_count_i: see the class docstring.
            choice_function: see the class docstring.
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(parent, Qt.WindowType.Popup)
        # LLFR-01062, LLFR-01079: the rows and columns of squares.
        self.row_count_i = int(row_count_i)
        self.column_count_i = int(column_count_i)
        self.choice_function = choice_function
        self.hover_tuple = NO_SQUARE_TUPLE
        self.chosen_tuple = NO_SQUARE_TUPLE
        # LLFR-01063: hover changes are seen without a pressed button.
        self.setMouseTracking(True)
        self.setFixedSize(self.picker_width(), self.picker_height())

    def picker_width(self) -> int:
        """Return the width of the picker.

        Inputs: none.
        Outputs: the width in pixels.
        """
        # LLFR-01062: the squares and their margins.
        return (2 * PICKER_MARGIN_I + self.column_count_i * SQUARE_SIZE_I
                + (self.column_count_i - 1) * SQUARE_GAP_I)

    def picker_height(self) -> int:
        """Return the height of the picker.

        Inputs: none.
        Outputs: the height in pixels, with room for the text below the
            squares.
        """
        # LLFR-01062, LLFR-01096: the squares, then the text.
        return (2 * PICKER_MARGIN_I + self.row_count_i * SQUARE_SIZE_I
                + (self.row_count_i - 1) * SQUARE_GAP_I
                + SIZE_TEXT_HEIGHT_I)

    def square_rect(self, row_i: int, column_i: int) -> QRect:
        """Return the rectangle of a square.

        Inputs:
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: a QRect in this widget's coordinates.
        """
        # LLFR-01062: row 1 at the top, column 1 at the left.
        step_i = SQUARE_SIZE_I + SQUARE_GAP_I
        return QRect(PICKER_MARGIN_I + (column_i - 1) * step_i,
                     PICKER_MARGIN_I + (row_i - 1) * step_i,
                     SQUARE_SIZE_I, SQUARE_SIZE_I)

    def square_at(self, point) -> tuple:
        """Return the square under a point.

        Inputs:
            point: a QPoint in this widget's coordinates.
        Outputs: (row_i, column_i) counted from 1, or NO_SQUARE_TUPLE
            when the point is not on a square.
        """
        # LLFR-01063: the gaps between the squares count as no square.
        for row_i in range(1, self.row_count_i + 1):
            for column_i in range(1, self.column_count_i + 1):
                if self.square_rect(row_i, column_i).contains(point):
                    return (row_i, column_i)
        return NO_SQUARE_TUPLE

    def is_square_enabled(self, row_i: int, column_i: int) -> bool:
        """Tell whether a click on a square makes a choice.

        Inputs:
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: True for an enabled square; every square here.
        """
        # LLFR-01072, LLFR-01080: the subclasses leave some out.
        return True

    def is_square_marked(self, row_i: int, column_i: int) -> bool:
        """Tell whether a square is shown marked.

        Inputs:
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: False here; the subclasses mark their squares.
        """
        # LLFR-01064, LLFR-01082: the subclasses mark their squares.
        return False

    def is_square_highlighted(self, row_i: int, column_i: int) -> bool:
        """Tell whether a square is highlighted under the pointer.

        Inputs:
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: True for the square under the pointer when it is
            enabled.
        """
        # LLFR-01080: only an enabled square reacts to the pointer.
        return (self.hover_tuple == (row_i, column_i)
                and self.is_square_enabled(row_i, column_i))

    def size_text(self) -> str:
        """Return the text shown below the squares.

        Inputs: none.
        Outputs: an empty text here; the matrix picker shows `R × C`.
        """
        # LLFR-01096: the matrix picker overrides this.
        return ""

    def hover_square(self, square_tuple: tuple) -> None:
        """Show the pointer over a square, or over no square.

        Inputs:
            square_tuple: (row_i, column_i) or NO_SQUARE_TUPLE.
        Outputs: none.
        """
        # LLFR-01063, LLFR-01096: the highlight and the text follow the
        # pointer.
        square_tuple = tuple(square_tuple)
        if square_tuple != self.hover_tuple:
            self.hover_tuple = square_tuple
            self.update()

    def choose_square(self, row_i: int, column_i: int) -> bool:
        """Choose a square as a click on it does.

        Inputs:
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: True when the square was enabled: the picker then
            closes and calls the choice function. A pale square leaves
            the picker open (LLFR-01072, LLFR-01080).
        """
        # LLFR-01072, LLFR-01080: a pale square does nothing.
        if not (1 <= row_i <= self.row_count_i
                and 1 <= column_i <= self.column_count_i):
            return False
        if not self.is_square_enabled(row_i, column_i):
            return False
        # LLFR-01065, LLFR-01083: close first, then make the choice, so
        # that the controller may rebuild the views behind the picker.
        self.chosen_tuple = (row_i, column_i)
        self.close()
        if self.choice_function is not None:
            self.choice_function(row_i, column_i)
        return True

    def show_at(self, global_point) -> None:
        """Show the picker with its top-left corner at a point.

        Inputs:
            global_point: a QPoint in screen coordinates.
        Outputs: none. The picker is moved to stay on the screen.
        """
        # LLFR-01062, LLFR-01079: the picker opens next to the pointer.
        left_i, top_i = global_point.x(), global_point.y()
        screen = QApplication.screenAt(global_point)
        if screen is not None:
            area = screen.availableGeometry()
            left_i = max(area.left(), min(left_i,
                                          area.right() - self.width()))
            top_i = max(area.top(), min(top_i,
                                        area.bottom() - self.height()))
        self.move(QPoint(left_i, top_i))
        self.show()

    def mouseMoveEvent(self, event) -> None:
        """Follow the pointer over the squares.

        Inputs:
            event: the QMouseEvent.
        Outputs: none.
        """
        # LLFR-01063, LLFR-01096.
        self.hover_square(self.square_at(event.position().toPoint()))

    def leaveEvent(self, event) -> None:
        """Remove the highlight when the pointer leaves the picker.

        Inputs:
            event: the QEvent.
        Outputs: none.
        """
        # LLFR-01063: no square under the pointer.
        self.hover_square(NO_SQUARE_TUPLE)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Choose the square under a left click.

        Inputs:
            event: the QMouseEvent.
        Outputs: none. A click outside the squares does nothing; a click
            outside the picker closes it (Qt closes a popup then,
            LLFR-01070).
        """
        # LLFR-01065, LLFR-01083: a left click on an enabled square.
        if event.button() != Qt.MouseButton.LeftButton:
            return
        square_tuple = self.square_at(event.position().toPoint())
        if square_tuple:
            self.choose_square(*square_tuple)

    def keyPressEvent(self, event) -> None:
        """Close the picker with no choice on the Esc key.

        Inputs:
            event: the QKeyEvent.
        Outputs: none.
        """
        # LLFR-01070: Esc closes the picker and changes nothing.
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def square_fill_color_str(self, row_i: int, column_i: int) -> str:
        """Return the fill color of a square.

        Inputs:
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: the "#rrggbb" color: highlighted, then pale, then
            normal. The mark is a border (square_border_color_str).
        """
        # LLFR-01063, LLFR-01071, LLFR-01081.
        if self.is_square_highlighted(row_i, column_i):
            return HIGHLIGHT_COLOR_STR
        if not self.is_square_enabled(row_i, column_i):
            return PALE_COLOR_STR
        return SQUARE_COLOR_STR

    def square_border_color_str(self, row_i: int, column_i: int) -> str:
        """Return the color of the border of a square.

        Inputs:
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: the "#rrggbb" color: MARKED_COLOR_STR for a marked
            square, whatever its fill, then the pale or normal border.
        """
        # LLFR-01064, LLFR-01082: the mark stays visible over a pale or
        # highlighted fill.
        if self.is_square_marked(row_i, column_i):
            return MARKED_COLOR_STR
        if not self.is_square_enabled(row_i, column_i):
            return PALE_BORDER_COLOR_STR
        return SQUARE_BORDER_COLOR_STR

    def paintEvent(self, event) -> None:
        """Draw the squares and the size text.

        Inputs:
            event: the QPaintEvent.
        Outputs: none.
        """
        # LLFR-01062, LLFR-01079: the background and the squares.
        painter = QPainter(self)
        try:
            painter.setPen(QPen(QColor(PICKER_BORDER_COLOR_STR)))
            painter.setBrush(QColor(PICKER_BACKGROUND_COLOR_STR))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
            for row_i in range(1, self.row_count_i + 1):
                for column_i in range(1, self.column_count_i + 1):
                    square_rect = self.square_rect(row_i, column_i)
                    painter.setPen(QPen(QColor(
                        self.square_border_color_str(row_i, column_i))))
                    painter.setBrush(QColor(
                        self.square_fill_color_str(row_i, column_i)))
                    painter.drawRect(square_rect)
                    # LLFR-01064, LLFR-01082: the mark, a border on top
                    # of the fill.
                    if self.is_square_marked(row_i, column_i):
                        mark_pen = QPen(QColor(MARKED_COLOR_STR))
                        mark_pen.setWidth(MARK_BORDER_WIDTH_I)
                        painter.setPen(mark_pen)
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                        painter.drawRect(square_rect.adjusted(1, 1, -1, -1))
            # LLFR-01096: the text below the squares.
            text_str = self.size_text()
            if text_str:
                painter.setPen(QPen(QColor(SIZE_TEXT_COLOR_STR)))
                text_rect = QRect(0, self.height() - PICKER_MARGIN_I
                                  - SIZE_TEXT_HEIGHT_I, self.width(),
                                  SIZE_TEXT_HEIGHT_I)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter,
                                 text_str)
        finally:
            painter.end()


class MatrixPicker(SquarePicker):
    """The 10 x 10 picker of the plot matrix of a tab (LLFR-01062).

    Inputs:
        current_row_count_i: rows of the tab's current plot matrix.
        current_column_count_i: columns of the tab's current matrix.
        plot_count_i: number of plots in the tab.
        choice_function: function taking (row_count_i, column_count_i).
        parent: optional parent widget.
    """

    def __init__(self, current_row_count_i: int, current_column_count_i: int,
                 plot_count_i: int, choice_function, parent=None) -> None:
        """Create the matrix picker.

        Inputs:
            current_row_count_i: see the class docstring.
            current_column_count_i: see the class docstring.
            plot_count_i: see the class docstring.
            choice_function: see the class docstring.
            parent: optional parent widget.
        Outputs: none.
        """
        # LLFR-01062: always 10 rows and 10 columns of squares.
        super().__init__(MAXIMUM_MATRIX_SIZE_I, MAXIMUM_MATRIX_SIZE_I,
                         choice_function, parent)
        self.current_row_count_i = int(current_row_count_i)
        self.current_column_count_i = int(current_column_count_i)
        self.plot_count_i = int(plot_count_i)

    def is_square_enabled(self, row_i: int, column_i: int) -> bool:
        """Tell whether a matrix has room for every plot of the tab.

        Inputs:
            row_i: rows of the matrix of the square.
            column_i: columns of the matrix of the square.
        Outputs: False when row_i times column_i is smaller than the
            number of plots of the tab (LLFR-01071).
        """
        # LLFR-01071, LLFR-01072, HLFR-00146.
        return row_i * column_i >= self.plot_count_i

    def is_square_marked(self, row_i: int, column_i: int) -> bool:
        """Tell whether a square is inside the current plot matrix.

        Inputs:
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: True from row 1 to the current last row and from
            column 1 to the current last column (LLFR-01064).
        """
        # LLFR-01064: the tab's current matrix.
        return (row_i <= self.current_row_count_i
                and column_i <= self.current_column_count_i)

    def is_square_highlighted(self, row_i: int, column_i: int) -> bool:
        """Tell whether a square is in the rectangle under the pointer.

        Inputs:
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: True from row 1 to the hovered row and from column 1
            to the hovered column (LLFR-01063), but never while the
            hovered square is pale (LLFR-01071).
        """
        # LLFR-01063: the R x C rectangle of the hovered square;
        # LLFR-01071: a pale size is not highlighted, so it never looks
        # like a size that can be chosen.
        if not self.hover_tuple or not self.is_square_enabled(
                *self.hover_tuple):
            return False
        hover_row_i, hover_column_i = self.hover_tuple
        return row_i <= hover_row_i and column_i <= hover_column_i

    def size_text(self) -> str:
        """Return the size of the plot matrix under the pointer.

        Inputs: none.
        Outputs: `R × C` while the pointer is over a square that is not
            pale, otherwise the size of the current matrix.
        """
        # LLFR-01096: the text of the hovered square; LLFR-01071: not for
        # a pale size, which cannot be chosen.
        if self.hover_tuple and self.is_square_enabled(*self.hover_tuple):
            return matrix_size_text(*self.hover_tuple)
        return matrix_size_text(self.current_row_count_i,
                                self.current_column_count_i)


class PositionPicker(SquarePicker):
    """The picker of the slot a plot moves to (LLFR-01079).

    Inputs:
        row_count_i: rows of the tab's plot matrix.
        column_count_i: columns of the tab's plot matrix.
        plot_count_i: number of plots in the tab.
        own_slot_tuple: (row_i, column_i), from 1, of the plot the
            picker was opened from.
        choice_function: function taking (row_i, column_i) of the
            chosen slot, from 1.
        parent: optional parent widget.
    """

    def __init__(self, row_count_i: int, column_count_i: int,
                 plot_count_i: int, own_slot_tuple: tuple,
                 choice_function, parent=None) -> None:
        """Create the position picker.

        Inputs:
            row_count_i: see the class docstring.
            column_count_i: see the class docstring.
            plot_count_i: see the class docstring.
            own_slot_tuple: see the class docstring.
            choice_function: see the class docstring.
            parent: optional parent widget.
        Outputs: none.
        """
        # LLFR-01079: one square per slot of the plot matrix.
        super().__init__(row_count_i, column_count_i, choice_function,
                         parent)
        self.plot_count_i = int(plot_count_i)
        self.own_slot_tuple = tuple(own_slot_tuple)

    def is_square_enabled(self, row_i: int, column_i: int) -> bool:
        """Tell whether a slot holds a plot.

        Inputs:
            row_i: row of the slot, from 1.
            column_i: column of the slot, from 1.
        Outputs: True when the slot is one of the first plot_count_i
            slots of the fill order (LLFR-01080).
        """
        # LLFR-01073, LLFR-01080, LLFR-01081.
        slot_index_i = (row_i - 1) * self.column_count_i + (column_i - 1)
        return slot_index_i < self.plot_count_i

    def is_square_marked(self, row_i: int, column_i: int) -> bool:
        """Tell whether a square is the slot of the plot itself.

        Inputs:
            row_i: row of the slot, from 1.
            column_i: column of the slot, from 1.
        Outputs: True for the own slot (LLFR-01082).
        """
        # LLFR-01082: the plot the picker was opened from.
        return (row_i, column_i) == self.own_slot_tuple
