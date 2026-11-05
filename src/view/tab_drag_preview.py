"""The image of a dragged tab that follows the pointer (LLFR-01208).

While the user drags a tab, of the main window or of an undocked window,
a small semi-transparent image of the tab's page follows the pointer,
like the image of a tab dragged in a web browser. The tab bars keep
their own movable-tab behaviour (LLFR-01086, LLFR-01157), so the image
is a frameless tool window that ignores the mouse, moved on each mouse
move of the drag and hidden at the release; no QDrag is started, which
would take the mouse from the tab bar.
"""

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QLabel

# LLFR-01208: the image is at most this wide, in pixels.
PREVIEW_MAXIMUM_WIDTH_I = 200
# LLFR-01208: semi-transparent.
PREVIEW_OPACITY_F = 0.6
# LLFR-01208: the image's top-left corner, from the pointer, in pixels,
# so that the pointer stays visible beside it.
PREVIEW_OFFSET_I = 12
PREVIEW_OBJECT_NAME_STR = "tab_drag_preview"


def preview_pixmap(page, maximum_width_i: int = PREVIEW_MAXIMUM_WIDTH_I):
    """Return a small, low-resolution image of a tab page.

    Inputs:
        page: the QWidget of the tab (a TabPage).
        maximum_width_i: the largest width of the image, in pixels.
    Outputs: a QPixmap at most maximum_width_i pixels wide, with the
        page's proportions, or None when the page has no size.
    """
    # LLFR-01208: a scaled grab of the page.
    if page is None or page.width() < 1 or page.height() < 1:
        return None
    pixmap = page.grab()
    if pixmap.isNull():
        return None
    if pixmap.width() > maximum_width_i:
        pixmap = pixmap.scaledToWidth(
            maximum_width_i, Qt.TransformationMode.FastTransformation)
    return pixmap


class TabDragPreview(QLabel):
    """A frameless, semi-transparent window that shows a tab's image.

    Inputs: none.
    Attributes:
        dragged_page: the page whose image is shown, or None.
    """

    def __init__(self) -> None:
        """Create the hidden preview window.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01208: a top-level tool window with no frame, that never
        # takes the mouse or the keyboard focus.
        super().__init__(None, Qt.WindowType.ToolTip
                         | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowTransparentForInput)
        self.setObjectName(PREVIEW_OBJECT_NAME_STR)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowOpacity(PREVIEW_OPACITY_F)
        self.dragged_page = None

    def start(self, page, global_point) -> None:
        """Show the image of a page next to a desktop point.

        Inputs:
            page: the TabPage of the dragged tab.
            global_point: the QPoint of the pointer, in desktop pixels.
        Outputs: none. Nothing is shown for a page with no image.
        """
        # LLFR-01208: shown once the press became a drag.
        pixmap = preview_pixmap(page)
        if pixmap is None:
            return
        self.dragged_page = page
        self.setPixmap(pixmap)
        self.resize(pixmap.size())
        self.follow(global_point)
        self.show()

    def follow(self, global_point) -> None:
        """Move the image next to the pointer.

        Inputs:
            global_point: the QPoint of the pointer, in desktop pixels.
        Outputs: none.
        """
        # LLFR-01208: it follows the pointer until the release.
        if self.dragged_page is None:
            return
        self.move(global_point + QPoint(PREVIEW_OFFSET_I, PREVIEW_OFFSET_I))

    def stop(self) -> None:
        """Hide the image at the release.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01208: removed wherever the tab is dropped.
        self.dragged_page = None
        self.hide()

    def is_shown(self) -> bool:
        """Tell whether the image of a dragged tab is shown.

        Inputs: none.
        Outputs: True from the start of the drag to the release.
        """
        # LLFR-01208.
        return self.dragged_page is not None and self.isVisible()
