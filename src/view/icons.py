"""Icons of the top panel buttons and the app icon (HLFR-00042, HLFR-00045).

The pictures are vector paths from view.icon_shapes, painted with
QPainter when Qt asks for an image of a given size. Nothing is drawn
from a stored bitmap, so the icons are sharp at any size and on any
screen, including high density (Retina) screens where Qt asks for twice
the pixels, and they look the same on every operating system
(LLFR-00159). No library beyond PyQt6 is needed (COR-00011).

Contents:
- ``icon_for``: the QIcon of a button, drawn in the icon color of each
  button state (LLFR-00160);
- ``icon_state_color_str``: the icon color used for a QIcon mode and
  state;
- ``render_icon_image``: one icon in one color, as a QImage;
- ``app_icon``, ``app_icon_pixmap``, ``app_icon_image`` and
  ``app_icon_png_bytes``: the app icon (LLFR-00182, LLFR-00183).
"""

from PyQt6.QtCore import (
    QBuffer, QByteArray, QIODevice, QPointF, QRectF, QSize, Qt)
from PyQt6.QtGui import (
    QBrush, QColor, QIcon, QIconEngine, QImage, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap)

from model.curve_colors import PALETTE_COLOR_TUPLE
from view import icon_shapes, theme

# LLFR-00183: the blue and red of the curve palette (LLFR-00144).
APP_ICON_BLUE_COLOR_STR = PALETTE_COLOR_TUPLE[0]
APP_ICON_RED_COLOR_STR = PALETTE_COLOR_TUPLE[2]
# LLFR-00182: sizes the operating system may ask for, in pixels.
APP_ICON_SIZE_TUPLE = (16, 24, 32, 48, 64, 128, 256, 512, 1024)


def build_painter_path(command_list: list) -> QPainterPath:
    """Turn the path commands of view.icon_shapes into a QPainterPath.

    Inputs:
        command_list: command tuples ("M", "L", "Q", "C", "Z", "O",
            "R"), as described in view.icon_shapes.
    Outputs: the QPainterPath, in the grid units of the commands.
    """
    # LLFR-00159, LLFR-00183: the icons are vector paths.
    path = QPainterPath()
    for command_tuple in command_list:
        letter_str = command_tuple[0]
        value_list = [float(value_f) for value_f in command_tuple[1:]]
        if letter_str == "M":
            path.moveTo(QPointF(*value_list))
        elif letter_str == "L":
            path.lineTo(QPointF(*value_list))
        elif letter_str == "Q":
            path.quadTo(QPointF(*value_list[0:2]), QPointF(*value_list[2:4]))
        elif letter_str == "C":
            path.cubicTo(QPointF(*value_list[0:2]),
                         QPointF(*value_list[2:4]),
                         QPointF(*value_list[4:6]))
        elif letter_str == "Z":
            path.closeSubpath()
        elif letter_str == "O":
            path.addEllipse(QPointF(value_list[0], value_list[1]),
                            value_list[2], value_list[2])
        elif letter_str == "R":
            path.addRoundedRect(QRectF(*value_list[0:4]), value_list[4],
                                value_list[4])
        else:
            raise ValueError(f"unknown path command {letter_str!r}")
    return path


def paint_layer_list(painter: QPainter, layer_list: list,
                     target_rect: QRectF, grid_f: float,
                     role_brush_dict: dict) -> None:
    """Paint the layers of a shape into a rectangle.

    Inputs:
        painter: an active QPainter.
        layer_list: the layers of view.icon_shapes.
        target_rect: the rectangle, in the painter's coordinates, that
            the shape's grid fills.
        grid_f: the side of the shape's grid (24 or 100 units).
        role_brush_dict: color role name -> QColor or QBrush.
    Outputs: none. The painter's state is restored afterwards.
    """
    # LLFR-00159, LLFR-00183: the grid is scaled to the target, so the
    # paths are drawn at the device's full resolution with antialiasing.
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.translate(target_rect.topLeft())
    painter.scale(target_rect.width() / grid_f,
                  target_rect.height() / grid_f)
    for command_list, stroke_role_str, fill_role_str, width_f in layer_list:
        path = build_painter_path(command_list)
        if fill_role_str:
            painter.setBrush(QBrush(role_brush_dict[fill_role_str]))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        if stroke_role_str:
            # LLFR-00159: round caps and joins for every stroke.
            pen = QPen(QBrush(role_brush_dict[stroke_role_str]),
                       float(width_f), Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
    painter.restore()


def icon_state_color_str(mode, state) -> str:
    """Return the icon color for a QIcon mode and state.

    Inputs:
        mode: a QIcon.Mode (Normal, Active, Selected or Disabled).
        state: a QIcon.State; On is used while the button is checked,
            that is active (LLFR-00001).
    Outputs: theme.ICON_DISABLED_COLOR_STR while disabled,
        theme.ICON_ACTIVE_COLOR_STR while active, otherwise
        theme.ICON_COLOR_STR.
    """
    # LLFR-00160: a paler icon on the disabled button (LLFR-00141), a
    # white icon on the dark active button and dark ink otherwise.
    if mode == QIcon.Mode.Disabled:
        return theme.ICON_DISABLED_COLOR_STR
    if state == QIcon.State.On:
        return theme.ICON_ACTIVE_COLOR_STR
    return theme.ICON_COLOR_STR


def new_transparent_image(width_i: int, height_i: int) -> QImage:
    """Return a fully transparent ARGB image.

    Inputs:
        width_i: width in pixels.
        height_i: height in pixels.
    Outputs: the QImage.
    """
    # LLFR-00159, LLFR-00183: icons are drawn on a clear background.
    image = QImage(max(1, width_i), max(1, height_i),
                   QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    return image


def render_icon_image(icon_name_str: str, color_str: str,
                      size_i: int) -> QImage:
    """Draw one button icon in one color.

    Inputs:
        icon_name_str: a name of icon_shapes.ICON_NAME_TUPLE.
        color_str: the icon color, "#rrggbb".
        size_i: the side of the image, in pixels.
    Outputs: a transparent QImage of size_i by size_i with the icon.
    """
    # LLFR-00159: every icon is drawn from its vector shape.
    image = new_transparent_image(size_i, size_i)
    painter = QPainter(image)
    paint_layer_list(painter, icon_shapes.icon_layer_list(icon_name_str),
                     QRectF(0.0, 0.0, size_i, size_i),
                     icon_shapes.ICON_GRID_F,
                     {icon_shapes.INK_ROLE_STR: QColor(color_str)})
    painter.end()
    return image


class ButtonIconEngine(QIconEngine):
    """Icon engine that paints a button icon in the color of its state.

    Inputs:
        icon_name_str: a name of icon_shapes.ICON_NAME_TUPLE.
        normal_color_str: the color in the normal state; None for
            theme.ICON_COLOR_STR.
    Attributes:
        icon_name_str: the icon name.
        normal_color_str: the color of the normal, inactive state.
    """

    def __init__(self, icon_name_str: str,
                 normal_color_str: str = None) -> None:
        """Store the icon name and its normal color.

        Inputs:
            icon_name_str: the icon name; raises KeyError if unknown.
            normal_color_str: the normal color, or None for the theme's.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00159: the shape is looked up now, so a wrong name fails
        # where the icon is made.
        icon_shapes.icon_layer_list(icon_name_str)
        self.icon_name_str = icon_name_str
        self.normal_color_str = normal_color_str or theme.ICON_COLOR_STR

    def color_str(self, mode, state) -> str:
        """Return the color used for one mode and state.

        Inputs:
            mode: a QIcon.Mode.
            state: a QIcon.State.
        Outputs: the color "#rrggbb".
        """
        # LLFR-00160: the color follows the button state.
        color_str = icon_state_color_str(mode, state)
        if color_str == theme.ICON_COLOR_STR:
            return self.normal_color_str
        return color_str

    def paint(self, painter, rect, mode, state) -> None:
        """Paint the icon into a rectangle.

        Inputs:
            painter: the QPainter.
            rect: the QRect to fill.
            mode: a QIcon.Mode.
            state: a QIcon.State.
        Outputs: none.
        """
        # LLFR-00159, LLFR-00160: the vector shape in the state color.
        side_f = float(min(rect.width(), rect.height()))
        target_rect = QRectF(rect.x() + (rect.width() - side_f) / 2.0,
                             rect.y() + (rect.height() - side_f) / 2.0,
                             side_f, side_f)
        paint_layer_list(
            painter, icon_shapes.icon_layer_list(self.icon_name_str),
            target_rect, icon_shapes.ICON_GRID_F,
            {icon_shapes.INK_ROLE_STR: QColor(self.color_str(mode, state))})

    def pixmap(self, size, mode, state) -> QPixmap:
        """Return the icon drawn at a size in pixels.

        Inputs:
            size: the QSize asked for; on a high density screen Qt asks
                for the size in device pixels.
            mode: a QIcon.Mode.
            state: a QIcon.State.
        Outputs: a transparent QPixmap of that size with the icon.
        """
        # LLFR-00159: drawn at exactly the asked size, so it is sharp.
        image = new_transparent_image(size.width(), size.height())
        painter = QPainter(image)
        self.paint(painter, image.rect(), mode, state)
        painter.end()
        return QPixmap.fromImage(image)

    def clone(self) -> QIconEngine:
        """Return a copy of the engine, as Qt requires.

        Inputs: none.
        Outputs: a new ButtonIconEngine with the same icon and color.
        """
        # LLFR-00159: Qt copies the engine when it copies the icon.
        return ButtonIconEngine(self.icon_name_str, self.normal_color_str)

    def isNull(self) -> bool:
        """Tell Qt that the icon is never empty.

        Inputs: none.
        Outputs: False.
        """
        # LLFR-00158: every top panel button has a picture.
        return False


def icon_for(icon_name_str: str, color_str: str = None) -> QIcon:
    """Return the QIcon of a top panel button.

    Inputs:
        icon_name_str: a name of icon_shapes.ICON_NAME_TUPLE.
        color_str: the icon color in the normal state; None for
            theme.ICON_COLOR_STR. The active and disabled colors always
            come from the theme (LLFR-00160).
    Outputs: the QIcon. Raises KeyError for an unknown name.
    """
    # LLFR-00158, LLFR-00159: the picture shown on the button.
    return QIcon(ButtonIconEngine(icon_name_str, color_str))


def app_icon_brush_dict() -> dict:
    """Return the colors of the app icon's roles.

    Inputs: none.
    Outputs: role name -> QColor, or a QLinearGradient brush for the
        background, which is lit from the top.
    """
    # LLFR-00183: a light square, dark axes, a blue and a red curve.
    gradient = QLinearGradient(QPointF(0.0, 0.0),
                               QPointF(0.0, icon_shapes.APP_ICON_GRID_F))
    gradient.setColorAt(0.0, QColor(theme.APP_ICON_TOP_COLOR_STR))
    gradient.setColorAt(1.0, QColor(theme.APP_ICON_BOTTOM_COLOR_STR))
    return {
        icon_shapes.BACKGROUND_ROLE_STR: QBrush(gradient),
        icon_shapes.BORDER_ROLE_STR: QColor(theme.APP_ICON_BORDER_COLOR_STR),
        icon_shapes.AXIS_ROLE_STR: QColor(theme.APP_ICON_AXIS_COLOR_STR),
        icon_shapes.BLUE_ROLE_STR: QColor(APP_ICON_BLUE_COLOR_STR),
        icon_shapes.RED_ROLE_STR: QColor(APP_ICON_RED_COLOR_STR),
    }


def paint_app_icon(painter: QPainter, target_rect: QRectF,
                   size_i: int) -> None:
    """Paint the app icon into a square.

    Inputs:
        painter: an active QPainter.
        target_rect: the square to fill, in the painter's coordinates.
        size_i: the side of the square in device pixels, which picks
            the simpler drawing for small sizes (LLFR-00183).
    Outputs: none.
    """
    # LLFR-00183: the drawing that suits the size.
    paint_layer_list(painter, icon_shapes.app_icon_layer_list(size_i),
                     target_rect, icon_shapes.APP_ICON_GRID_F,
                     app_icon_brush_dict())


def app_icon_image(size_i: int, margin_fraction_f: float = 0.0) -> QImage:
    """Draw the app icon as a transparent square image.

    Inputs:
        size_i: the side of the image, in pixels.
        margin_fraction_f: the empty border on each side, as a fraction
            of the side (macOS icons leave about 0.1).
    Outputs: the QImage.
    """
    # LLFR-00182, LLFR-00183: the same drawing for every use.
    image = new_transparent_image(size_i, size_i)
    margin_f = size_i * float(margin_fraction_f)
    drawn_side_f = size_i - 2.0 * margin_f
    painter = QPainter(image)
    paint_app_icon(painter, QRectF(margin_f, margin_f, drawn_side_f,
                                   drawn_side_f), int(round(drawn_side_f)))
    painter.end()
    return image


class AppIconEngine(QIconEngine):
    """Icon engine that paints the app icon at any size (LLFR-00183).

    Inputs: none.
    """

    def paint(self, painter, rect, mode, state) -> None:
        """Paint the app icon into a rectangle.

        Inputs:
            painter: the QPainter.
            rect: the QRect to fill.
            mode: a QIcon.Mode (not used: the app icon has one look).
            state: a QIcon.State (not used).
        Outputs: none.
        """
        # LLFR-00183: centred in the largest square of the rectangle.
        side_f = float(min(rect.width(), rect.height()))
        device_side_i = int(round(
            side_f * painter.device().devicePixelRatioF()))
        paint_app_icon(painter, QRectF(
            rect.x() + (rect.width() - side_f) / 2.0,
            rect.y() + (rect.height() - side_f) / 2.0, side_f, side_f),
            device_side_i)

    def pixmap(self, size, mode, state) -> QPixmap:
        """Return the app icon drawn at a size in pixels.

        Inputs:
            size: the QSize asked for, in device pixels.
            mode: a QIcon.Mode.
            state: a QIcon.State.
        Outputs: a transparent QPixmap of that size.
        """
        # LLFR-00182: the window, Dock and taskbar ask for these.
        side_i = min(size.width(), size.height())
        image = new_transparent_image(size.width(), size.height())
        painter = QPainter(image)
        paint_app_icon(painter, QRectF(
            (size.width() - side_i) / 2.0, (size.height() - side_i) / 2.0,
            side_i, side_i), side_i)
        painter.end()
        return QPixmap.fromImage(image)

    def availableSizes(self, mode=None, state=None) -> list:
        """Return the sizes the operating system can ask for.

        Inputs:
            mode: a QIcon.Mode (not used).
            state: a QIcon.State (not used).
        Outputs: a list of QSize; macOS builds the Dock icon from them.
        """
        # LLFR-00182: without sizes, macOS would show no Dock icon.
        return [QSize(side_i, side_i) for side_i in APP_ICON_SIZE_TUPLE]

    def clone(self) -> QIconEngine:
        """Return a copy of the engine, as Qt requires.

        Inputs: none.
        Outputs: a new AppIconEngine.
        """
        # LLFR-00182: Qt copies the engine when it copies the icon.
        return AppIconEngine()

    def isNull(self) -> bool:
        """Tell Qt that the icon is never empty.

        Inputs: none.
        Outputs: False.
        """
        # LLFR-00182: the app always has its icon.
        return False


def app_icon() -> QIcon:
    """Return the app icon, for the window, Dock and taskbar.

    Inputs: none.
    Outputs: the QIcon (LLFR-00182, LLFR-00183).
    """
    # LLFR-00182: one icon for every place the system shows the app.
    return QIcon(AppIconEngine())


def app_icon_pixmap(size_i: int) -> QPixmap:
    """Return the app icon as a square pixmap, e.g. for a splash screen.

    Inputs:
        size_i: the side in pixels.
    Outputs: the QPixmap.
    """
    # LLFR-00183: the same drawing as the window icon.
    return QPixmap.fromImage(app_icon_image(size_i))


def app_icon_png_bytes(size_i: int, margin_fraction_f: float = 0.0) -> bytes:
    """Return the app icon as the bytes of a PNG file.

    Inputs:
        size_i: the side in pixels.
        margin_fraction_f: the empty border on each side (see
            app_icon_image).
    Outputs: the PNG file content. Used to build the .icns and .ico
        files of the standalone executable (view.app_icon_files).
    """
    # LLFR-00182: the executable icon is made from the same drawing.
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not app_icon_image(size_i, margin_fraction_f).save(buffer, "PNG"):
        raise RuntimeError(f"could not encode the {size_i} px app icon")
    buffer.close()
    return bytes(byte_array.data())
