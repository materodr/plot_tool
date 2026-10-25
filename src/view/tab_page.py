"""Tab page: the plots of one tab, stacked from top to bottom."""

from PyQt6.QtWidgets import QVBoxLayout, QWidget

# LLFR-00050, LLFR-00069: every plot gets the same share of the height.
PLOT_STRETCH_I = 1


class TabPage(QWidget):
    """Page of one tab of the plot panel (HLFR-00014).

    The plots are stacked vertically in creation order (LLFR-00069).
    They all have the same stretch, so they share the page height and
    the remaining ones grow when one is removed (LLFR-00050). The page
    itself accepts no drops: a signal dropped on it, outside a plot,
    creates nothing and shows nothing (LLFR-00022, LLFR-00023).

    Inputs:
        tab_id_i: id of the tab in the model.
        name_str: name shown on the tab.
        parent: optional parent widget.
    Attributes:
        tab_id_i: id of the tab in the model.
        name_str: name shown on the tab.
        page_layout: the vertical layout holding the plot widgets.
    """

    def __init__(self, tab_id_i: int, name_str: str, parent=None) -> None:
        """Create an empty page.

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
        self.plot_widget_list = []
        # LLFR-00022, LLFR-00023: drops outside a plot are not accepted.
        self.setAcceptDrops(False)

    def add_plot_widget(self, plot_widget) -> None:
        """Place a plot widget below the existing ones.

        Inputs:
            plot_widget: the PlotWidget to add.
        Outputs: none.
        """
        # LLFR-00069: new plots go to the bottom, with equal stretch.
        self.plot_widget_list.append(plot_widget)
        self.page_layout.addWidget(plot_widget, PLOT_STRETCH_I)

    def remove_plot_widget(self, plot_widget) -> bool:
        """Take a plot widget out of the page.

        The widget is hidden and removed from the layout; the caller
        deletes it. The other plots grow to fill the free space.

        Inputs:
            plot_widget: the PlotWidget to remove.
        Outputs: True when the widget was on this page.
        """
        # LLFR-00049: remove the plot from the tab.
        if plot_widget not in self.plot_widget_list:
            return False
        self.plot_widget_list.remove(plot_widget)
        plot_widget.hide()
        self.page_layout.removeWidget(plot_widget)
        # LLFR-00050: the remaining plots share the whole height.
        self.page_layout.invalidate()
        return True
