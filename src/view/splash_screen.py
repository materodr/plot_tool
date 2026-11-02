"""Splash screen shown while the app starts (HLFR-00046).

src/main.py shows it before the slow part of the startup: importing
matplotlib, numpy and pandas and building the main window, which takes
many seconds on the first launch of the standalone app (issue #67). So
this module, and every module it imports (view.icons, view.icon_shapes,
view.theme and model.curve_colors), must not import matplotlib, numpy,
pandas or the plot views at import time (LLFR-00184).

Contents:
- ``SplashScreen``: a white card with the app icon, the app name and
  "Loading..." (LLFR-00185), closed by ``finish`` in the same step
  that shows the main window (LLFR-00186);
- ``show_splash``: create it, centre it on the primary screen, show it
  and make sure it is painted before the slow imports start.

The splash screen is a frameless QWidget, not a QSplashScreen: on
macOS, QSplashScreen.show() waited a full second for the window to be
exposed (its wait asks Qt to process events for the whole remaining
time), which used half of the 2 s of LLFR-00184. A mouse click does
not close it either, unlike a QSplashScreen.
"""

import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QFrame, QLabel, QVBoxLayout, QWidget)

from view import icons, theme

APP_NAME_STR = "plot_tool"
LOADING_TEXT_STR = "Loading..."
CARD_OBJECT_NAME_STR = "splash_card"
ICON_OBJECT_NAME_STR = "splash_icon"
NAME_OBJECT_NAME_STR = "splash_name"
MESSAGE_OBJECT_NAME_STR = "splash_message"
# LLFR-00184: how long show_splash waits at most for the window system
# to put the splash screen on screen.
EXPOSE_TIMEOUT_S = 1.0
EXPOSE_POLL_INTERVAL_S = 0.005


class SplashScreen(QWidget):
    """The splash screen: app icon, app name and "Loading...".

    Inputs:
        device_pixel_ratio_f: the pixel density of the screen it is
            shown on (2.0 on a Retina screen), so the icon is drawn with
            every device pixel and stays sharp.
    Attributes:
        card: the white rounded QFrame that holds the labels.
        icon_label: the QLabel with the app icon.
        name_label: the QLabel with the app name.
        message_label: the QLabel with "Loading...".
    """

    def __init__(self, device_pixel_ratio_f: float = 1.0) -> None:
        """Build the card and its three labels.

        Inputs:
            device_pixel_ratio_f: the screen's device pixel ratio.
        Outputs: none.
        """
        super().__init__(None, Qt.WindowType.SplashScreen
                         | Qt.WindowType.FramelessWindowHint)
        # LLFR-00185: a frameless card with rounded corners; the corners
        # outside the card are transparent.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(theme.SPLASH_WIDTH_I, theme.SPLASH_HEIGHT_I)
        self.setStyleSheet(theme.splash_style_sheet(
            CARD_OBJECT_NAME_STR, NAME_OBJECT_NAME_STR,
            MESSAGE_OBJECT_NAME_STR))
        self.card = QFrame(self)
        self.card.setObjectName(CARD_OBJECT_NAME_STR)
        self.card.setGeometry(0, 0, theme.SPLASH_WIDTH_I,
                              theme.SPLASH_HEIGHT_I)
        # LLFR-00185, LLFR-00183: the app icon, drawn from its vector
        # shape at the screen's full resolution.
        self.icon_label = QLabel(self.card)
        self.icon_label.setObjectName(ICON_OBJECT_NAME_STR)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setPixmap(splash_icon_pixmap(device_pixel_ratio_f))
        # LLFR-00185: the app name and the loading text.
        self.name_label = QLabel(APP_NAME_STR, self.card)
        self.name_label.setObjectName(NAME_OBJECT_NAME_STR)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label = QLabel(LOADING_TEXT_STR, self.card)
        self.message_label.setObjectName(MESSAGE_OBJECT_NAME_STR)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(theme.SPLASH_PADDING_I,
                                  theme.SPLASH_PADDING_I,
                                  theme.SPLASH_PADDING_I,
                                  theme.SPLASH_PADDING_I)
        layout.setSpacing(theme.SPLASH_SPACING_I)
        layout.addStretch(1)
        layout.addWidget(self.icon_label)
        layout.addSpacing(theme.SPLASH_SPACING_I)
        layout.addWidget(self.name_label)
        layout.addWidget(self.message_label)
        layout.addStretch(1)

    def finish(self, main_window, show_function=None) -> None:
        """Show the main window and close the splash screen at once.

        Inputs:
            main_window: the main window, built but not shown yet.
            show_function: function without arguments that shows the
                main window; main_window.show when None.
        Outputs: none. The window is shown, the splash screen closed in
            the same step, with no event handled in between, and the
            window raised and made the active window.
        """
        # LLFR-00186: the window system draws both changes together,
        # so the splash screen is never seen above the visible window.
        # Waiting for the window to be exposed before closing the
        # splash (as before issue #165) left the splash, a window kept
        # on top, over the shown window during that wait.
        if show_function is None:
            show_function = main_window.show
        show_function()
        self.close()
        # LLFR-00186: the window comes to the front with the keyboard
        # focus, where the splash screen was.
        main_window.raise_()
        main_window.activateWindow()


def splash_icon_pixmap(device_pixel_ratio_f: float):
    """Return the app icon for the splash screen.

    Inputs:
        device_pixel_ratio_f: the screen's device pixel ratio.
    Outputs: a QPixmap of SPLASH_ICON_SIZE_I logical pixels, drawn with
        SPLASH_ICON_SIZE_I * device_pixel_ratio_f device pixels.
    """
    # LLFR-00185, LLFR-00183: the same drawing as the window icon, sharp
    # on high density screens.
    ratio_f = max(1.0, float(device_pixel_ratio_f))
    pixmap = icons.app_icon_pixmap(
        int(round(theme.SPLASH_ICON_SIZE_I * ratio_f)))
    pixmap.setDevicePixelRatio(ratio_f)
    return pixmap


def splash_exposed(widget) -> bool:
    """Tell whether a window is on screen.

    Inputs:
        widget: a top-level widget (the SplashScreen or the main
            window).
    Outputs: True when it is visible and its native window is exposed.
    """
    # LLFR-00184, LLFR-00186: the window system has put it on screen.
    if not widget.isVisible():
        return False
    window_handle = widget.windowHandle()
    return window_handle is not None and window_handle.isExposed()


def wait_until_exposed(application, widget, timeout_s: float) -> bool:
    """Handle events until a window is on screen, or for at most a time.

    Inputs:
        application: the QApplication.
        widget: the shown top-level widget.
        timeout_s: the longest wait.
    Outputs: True when the widget is exposed.
    """
    # LLFR-00184, LLFR-00186: there may be no running event loop, so
    # the events that put the window on screen are handled here; each
    # call handles only the pending events and returns at once.
    deadline_s = time.perf_counter() + timeout_s
    application.processEvents()
    while (not splash_exposed(widget)
           and time.perf_counter() < deadline_s):
        time.sleep(EXPOSE_POLL_INTERVAL_S)
        application.processEvents()
    return splash_exposed(widget)


def show_splash(application: QApplication,
                timeout_s: float = EXPOSE_TIMEOUT_S,
                phase_list: list = None) -> SplashScreen:
    """Show the splash screen and make sure it is painted.

    Inputs:
        application: the QApplication.
        timeout_s: how long to wait at most for the splash to be
            exposed on screen.
        phase_list: when given, (phase name, time.perf_counter()) tuples
            are appended to it as the splash is built, shown, exposed
            and painted, for the startup probe.
    Outputs: the shown SplashScreen. The caller closes it with
        ``finish(main_window)`` (LLFR-00186) or ``close()`` (LLFR-00187).
    """
    # LLFR-00184: the splash is centred on the primary screen and drawn
    # for its pixel density.
    if phase_list is None:
        phase_list = []
    screen = application.primaryScreen()
    ratio_f = screen.devicePixelRatio() if screen is not None else 1.0
    splash = SplashScreen(ratio_f)
    phase_list.append(("splash_built", time.perf_counter()))
    if screen is not None:
        available_rect = screen.availableGeometry()
        splash.move(available_rect.center() - splash.rect().center())
    # LLFR-00184: styled and given its native window first, so that the
    # startup probe tells which part of showing it takes the time.
    splash.ensurePolished()
    phase_list.append(("splash_polished", time.perf_counter()))
    splash.winId()
    phase_list.append(("splash_native", time.perf_counter()))
    splash.show()
    phase_list.append(("splash_show", time.perf_counter()))
    # LLFR-00184: there is no event loop yet, and the slow imports that
    # follow block it, so the events that put the splash on screen are
    # handled here until it is exposed, and then it is painted.
    wait_until_exposed(application, splash, timeout_s)
    phase_list.append(("splash_exposed", time.perf_counter()))
    splash.repaint()
    application.processEvents()
    phase_list.append(("splash_painted", time.perf_counter()))
    return splash
