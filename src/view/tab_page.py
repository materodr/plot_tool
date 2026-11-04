"""Tab page: the plots of one tab, laid out in its plot matrix."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from model.workspace import (
    DEFAULT_MATRIX_COLUMNS_I, DEFAULT_MATRIX_ROWS_I, matrix_row_list,
    matrix_slot_tuple)
from view import theme

# LLFR-01075, LLFR-01076: every shown row gets the same share of the
# height, and every plot of a row the same share of its width.
PLOT_STRETCH_I = 1


class TabPage(QWidget):
    """Page of one tab of the plot panel (HLFR-00014).

    The plots are laid out in the tab's plot matrix (HLFR-00145): they
    fill row 1 from left to right, then row 2, and so on (LLFR-01073).
    Only the rows that hold a plot are shown, one below the other, each
    with the same share of the page height (LLFR-01075), and the plots of
    a row share its whole width (LLFR-01076), so a partly filled row
    stretches its plots. With the default 5 x 1 matrix the plots are
    stacked vertically (LLFR-00069). The page lays its plots out again
    whenever a plot is added or removed (LLFR-00050), the matrix changes
    (LLFR-01065) or two plots swap (LLFR-01083). The page itself accepts
    no drops: a signal dropped on it, outside a plot, creates nothing and
    shows nothing (LLFR-00022, LLFR-00023).

    Inputs:
        tab_id_i: id of the tab in the model.
        name_str: name shown on the tab.
        parent: optional parent widget.
    Attributes:
        tab_id_i: id of the tab in the model.
        name_str: name shown on the tab.
        page_layout: the vertical layout that holds one row layout per
            shown row.
        row_layout_list: the horizontal layouts of the shown rows, top
            to bottom.
        plot_widget_list: the PlotWidgets, in fill order.
        row_count_i: number of rows of the plot matrix.
        column_count_i: number of columns of the plot matrix.
    """

    def __init__(self, tab_id_i: int, name_str: str, parent=None) -> None:
        """Create an empty page with the default plot matrix.

        Inputs:
            tab_id_i: id of the tab in the model.
            name_str: name shown on the tab.
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00024, LLFR-00026: a new tab page has no plots.
        self.tab_id_i = tab_id_i
        self.name_str = name_str
        self.page_layout = QVBoxLayout(self)
        self.page_layout.setContentsMargins(0, 0, 0, 0)
        # LLFR-00069: a small gap of the plot well between the rows.
        self.page_layout.setSpacing(theme.PLOT_SPACING_I)
        self.row_layout_list = []
        self.plot_widget_list = []
        # LLFR-01087: the 5 x 1 matrix until the controller says more.
        self.row_count_i = DEFAULT_MATRIX_ROWS_I
        self.column_count_i = DEFAULT_MATRIX_COLUMNS_I
        # LLFR-00022, LLFR-00023: drops outside a plot are not accepted.
        self.setAcceptDrops(False)
        # LLFR-00137: a click on an empty part of the page takes the
        # keyboard focus from the text fields, as a click on a plot does.
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def relayout(self) -> None:
        """Place every plot widget in its slot of the plot matrix.

        Inputs: none.
        Outputs: none. The row layouts are made again from the fill
            order; the plot widgets stay children of the page.
        """
        # LLFR-01073 to LLFR-01076: take every plot out of its row, then
        # put the plots back row by row.
        for row_layout in self.row_layout_list:
            while row_layout.count():
                row_layout.takeAt(0)
            self.page_layout.removeItem(row_layout)
            row_layout.deleteLater()
        self.row_layout_list = []
        for row_widget_list in matrix_row_list(self.plot_widget_list,
                                               self.column_count_i):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            # LLFR-01076: the same gap between the plots of a row as
            # between the rows.
            row_layout.setSpacing(theme.PLOT_SPACING_I)
            for plot_widget in row_widget_list:
                row_layout.addWidget(plot_widget, PLOT_STRETCH_I)
            # LLFR-01075: each shown row gets an equal share.
            self.page_layout.addLayout(row_layout, PLOT_STRETCH_I)
            self.row_layout_list.append(row_layout)
        # LLFR-00050: the plots fill the free space at once.
        self.page_layout.invalidate()

    def set_plot_matrix(self, row_count_i: int, column_count_i: int) -> None:
        """Lay the plots out in another plot matrix.

        Inputs:
            row_count_i: number of rows, 1 to 10.
            column_count_i: number of columns, 1 to 10.
        Outputs: none.
        """
        # LLFR-01065, LLFR-01067: the plots keep their fill order.
        self.row_count_i = int(row_count_i)
        self.column_count_i = int(column_count_i)
        self.relayout()

    def set_plot_order(self, plot_widget_list: list) -> None:
        """Place the plot widgets in a new fill order.

        Inputs:
            plot_widget_list: the PlotWidgets of this page, in their new
                fill order. Widgets that are not on the page are left
                out; widgets of the page that are not listed keep their
                place at the end.
        Outputs: none.
        """
        # LLFR-01083: after a swap, each plot is in the other's slot.
        ordered_list = [plot_widget for plot_widget in plot_widget_list
                        if plot_widget in self.plot_widget_list]
        ordered_list.extend(plot_widget
                            for plot_widget in self.plot_widget_list
                            if plot_widget not in ordered_list)
        self.plot_widget_list = ordered_list
        self.relayout()

    def plot_slot_tuple(self, plot_widget) -> tuple:
        """Return the slot of a plot widget of this page.

        Inputs:
            plot_widget: a PlotWidget.
        Outputs: (row_index_i, column_index_i), counted from 0, or ()
            when the widget is not on this page.
        """
        # LLFR-01073, LLFR-01082: the slot follows the fill order.
        if plot_widget not in self.plot_widget_list:
            return ()
        return matrix_slot_tuple(self.plot_widget_list.index(plot_widget),
                                 self.column_count_i)

    def plot_widget_at_slot(self, row_index_i: int, column_index_i: int):
        """Return the plot widget in a slot of the plot matrix.

        Inputs:
            row_index_i: row of the slot, from 0.
            column_index_i: column of the slot, from 0.
        Outputs: the PlotWidget, or None when the slot holds no plot.
        """
        # LLFR-01080, LLFR-01083: only an occupied slot has a plot.
        if not (0 <= column_index_i < self.column_count_i
                and 0 <= row_index_i < self.row_count_i):
            return None
        plot_index_i = row_index_i * self.column_count_i + column_index_i
        if plot_index_i >= len(self.plot_widget_list):
            return None
        return self.plot_widget_list[plot_index_i]

    def add_plot_widget(self, plot_widget) -> None:
        """Place a plot widget in the next slot of the plot matrix.

        Inputs:
            plot_widget: the PlotWidget to add.
        Outputs: none.
        """
        # LLFR-01074: the new plot goes after the last one.
        plot_widget.setParent(self)
        self.plot_widget_list.append(plot_widget)
        self.relayout()
        plot_widget.show()

    def remove_plot_widget(self, plot_widget) -> bool:
        """Take a plot widget out of the page.

        The widget is hidden and removed from the layout; the caller
        deletes it. The other plots move back one slot and fill the
        free space.

        Inputs:
            plot_widget: the PlotWidget to remove.
        Outputs: True when the widget was on this page.
        """
        # LLFR-00049: remove the plot from the tab.
        if plot_widget not in self.plot_widget_list:
            return False
        self.plot_widget_list.remove(plot_widget)
        plot_widget.hide()
        # LLFR-00050: the plots after it move back one slot.
        self.relayout()
        return True
