"""Reviewer's tests of issue #260 for the held tool keys C, R, A and V.

The real ToolKeyFilter gets the keys of the main window (LLFR-00148,
LLFR-00287, LLFR-00367, LLFR-01274, LLFR-01277) and is driven through
its handle_key_press and handle_key_release methods, so no window is
needed. Checked: the new mapping (V area, A arrow, C circle, R
rectangle), Ctrl+C that ends the Data tip hold and holds no circle
(LLFR-01274 Note, LLFR-00150), Ctrl pressed while C is held
(LLFR-01276), and C and R while typing (LLFR-00157).
"""

import unittest

from tests.support import covers, requires_qt

from controller.plot_tools import (
    ARROW_TOOL_STR, AREA_TOOL_STR, CIRCLE_TOOL_STR, DELTA_X_TOOL_STR,
    DELTA_Y_TOOL_STR, MARKER_TOOL_STR, RECTANGLE_TOOL_STR, TEXT_TOOL_STR,
    TIP_TOOL_STR, ZOOM_TOOL_STR)


@requires_qt
class HeldShapeKeyTest(unittest.TestCase):
    """The filter with the key table of the main window."""

    def setUp(self) -> None:
        """Create the filter and record its callbacks.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from view import tip_key_filter as keys
        self.keys = keys
        self.control_modifier_i = int(
            Qt.KeyboardModifier.ControlModifier.value)
        self.activated_list = []
        self.release_list = []
        self.key_filter = keys.ToolKeyFilter(
            {keys.TIP_KEY_I: TIP_TOOL_STR, keys.MARKER_KEY_I: MARKER_TOOL_STR,
             keys.DELTA_X_KEY_I: DELTA_X_TOOL_STR,
             keys.DELTA_Y_KEY_I: DELTA_Y_TOOL_STR,
             keys.AREA_KEY_I: AREA_TOOL_STR, keys.TEXT_KEY_I: TEXT_TOOL_STR,
             keys.ARROW_KEY_I: ARROW_TOOL_STR,
             keys.ZOOM_KEY_I: ZOOM_TOOL_STR,
             keys.CIRCLE_KEY_I: CIRCLE_TOOL_STR,
             keys.RECTANGLE_KEY_I: RECTANGLE_TOOL_STR},
            self.activated_list.append,
            lambda: self.release_list.append(True), ())

    @covers("LLFR-00287", "LLFR-00367", "LLFR-01274", "LLFR-01277",
            "HLFR-00158", "HLFR-00032")
    def test_letters_of_the_new_mapping(self) -> None:
        """V holds the vertical area, A the arrow, C the circle and R
        the rectangle; the ten tool keys are different keys.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        keys = self.keys
        self.assertEqual(keys.AREA_KEY_I, int(Qt.Key.Key_V.value))
        self.assertEqual(keys.ARROW_KEY_I, int(Qt.Key.Key_A.value))
        self.assertEqual(keys.CIRCLE_KEY_I, int(Qt.Key.Key_C.value))
        self.assertEqual(keys.RECTANGLE_KEY_I, int(Qt.Key.Key_R.value))
        self.assertEqual(len(self.key_filter.key_tool_dict), 10)
        for key_i, tool_str in ((keys.AREA_KEY_I, AREA_TOOL_STR),
                                (keys.ARROW_KEY_I, ARROW_TOOL_STR),
                                (keys.CIRCLE_KEY_I, CIRCLE_TOOL_STR),
                                (keys.RECTANGLE_KEY_I, RECTANGLE_TOOL_STR)):
            with self.subTest(tool=tool_str):
                self.key_filter.handle_key_press(key_i, 0, False)
                self.assertEqual(self.activated_list[-1], tool_str)
                self.key_filter.handle_key_release(key_i, False)
                self.assertFalse(self.key_filter.is_activation_on())

    @covers("LLFR-01274", "LLFR-00150", "LLFR-00149", "LLFR-01136",
            "HLFR-00158")
    def test_ctrl_c_holds_no_circle(self) -> None:
        """Ctrl held, then C: the Data tip hold ends and no Circle hold
        starts; after both are released, C alone holds the circle.

        Inputs: none.
        Outputs: none.
        """
        keys = self.keys
        self.key_filter.handle_key_press(keys.TIP_KEY_I,
                                         self.control_modifier_i, False)
        self.assertEqual(self.activated_list, [TIP_TOOL_STR])
        self.key_filter.handle_key_press(keys.CIRCLE_KEY_I,
                                         self.control_modifier_i, False)
        self.assertEqual(self.release_list, [True])
        self.assertEqual(self.activated_list, [TIP_TOOL_STR])
        self.assertFalse(self.key_filter.is_activation_on())
        self.key_filter.handle_key_release(keys.CIRCLE_KEY_I, False)
        self.key_filter.handle_key_release(keys.TIP_KEY_I, False)
        self.assertEqual(self.activated_list, [TIP_TOOL_STR])
        # C with the Ctrl modifier alone (no Ctrl press seen) is Copy too.
        self.key_filter.handle_key_press(keys.CIRCLE_KEY_I,
                                         self.control_modifier_i, False)
        self.assertEqual(self.activated_list, [TIP_TOOL_STR])
        self.key_filter.handle_key_release(keys.CIRCLE_KEY_I, False)
        self.key_filter.handle_key_press(keys.CIRCLE_KEY_I, 0, False)
        self.assertEqual(self.activated_list[-1], CIRCLE_TOOL_STR)

    @covers("LLFR-01276", "LLFR-01275", "LLFR-01279", "HLFR-00158")
    def test_another_key_ends_the_shape_hold(self) -> None:
        """Ctrl pressed while C is held, or C while R is held, ends the
        hold and starts no other tool.

        Inputs: none.
        Outputs: none.
        """
        keys = self.keys
        self.key_filter.handle_key_press(keys.CIRCLE_KEY_I, 0, False)
        self.key_filter.handle_key_press(keys.TIP_KEY_I,
                                         self.control_modifier_i, False)
        self.assertEqual(self.activated_list, [CIRCLE_TOOL_STR])
        self.assertEqual(self.release_list, [True])
        self.key_filter.handle_key_release(keys.TIP_KEY_I, False)
        self.key_filter.handle_key_release(keys.CIRCLE_KEY_I, False)
        self.key_filter.handle_key_press(keys.RECTANGLE_KEY_I, 0, False)
        self.key_filter.handle_key_press(keys.CIRCLE_KEY_I, 0, False)
        self.assertEqual(self.activated_list,
                         [CIRCLE_TOOL_STR, RECTANGLE_TOOL_STR])
        self.assertEqual(self.release_list, [True, True])
        self.assertFalse(self.key_filter.is_activation_on())

    @covers("LLFR-00157", "LLFR-01274", "LLFR-01277", "HLFR-00158")
    def test_typing_c_and_r_holds_nothing(self) -> None:
        """C and R pressed while a text field has the focus hold no tool.

        Inputs: none.
        Outputs: none.
        """
        keys = self.keys
        for key_i in (keys.CIRCLE_KEY_I, keys.RECTANGLE_KEY_I):
            self.key_filter.handle_key_press(key_i, 0, False, True)
            self.key_filter.handle_key_release(key_i, False)
        self.assertEqual(self.activated_list, [])


if __name__ == "__main__":
    unittest.main()
