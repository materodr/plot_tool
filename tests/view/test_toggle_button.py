"""Tests for the toggle button that shows when it is active (HLFR-00003)."""

import unittest

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class ToggleButtonTest(unittest.TestCase):
    """Check the active color and signals of ToggleButton."""

    def setUp(self) -> None:
        """Create and show a toggle button and connect signal counters.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view import toggle_button
        self.toggle_module = toggle_button
        self.button = toggle_button.ToggleButton("Open file")
        self.button.show()
        self.application.processEvents()
        self.activated_count_i = 0
        self.deactivated_count_i = 0
        self.button.activated.connect(self.count_activated)
        self.button.deactivated.connect(self.count_deactivated)

    def tearDown(self) -> None:
        """Close and delete the button.

        Inputs: none.
        Outputs: none.
        """
        self.button.close()
        self.button.deleteLater()
        self.application.processEvents()

    def count_activated(self) -> None:
        """Count one ``activated`` signal.

        Inputs: none.
        Outputs: none.
        """
        self.activated_count_i += 1

    def count_deactivated(self) -> None:
        """Count one ``deactivated`` signal.

        Inputs: none.
        Outputs: none.
        """
        self.deactivated_count_i += 1

    def mouse_click(self) -> None:
        """Click the button with the left mouse button, as a user would.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(self.button, Qt.MouseButton.LeftButton)
        self.application.processEvents()

    def assert_inactive_look(self) -> None:
        """Check that the button is inactive and has the normal color.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.button.is_active())
        self.assertFalse(self.button.isChecked())
        self.assertEqual(self.button.current_background_color_str(),
                         self.toggle_module.NORMAL_COLOR_STR)
        self.assertNotIn(self.toggle_module.ACTIVE_COLOR_STR,
                         self.button.styleSheet())
        self.assertIn(self.toggle_module.NORMAL_COLOR_STR,
                      self.button.styleSheet())

    def assert_active_look(self) -> None:
        """Check that the button is active and has the active color.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.button.is_active())
        self.assertTrue(self.button.isChecked())
        self.assertEqual(self.button.current_background_color_str(),
                         self.toggle_module.ACTIVE_COLOR_STR)
        self.assertIn(self.toggle_module.ACTIVE_COLOR_STR,
                      self.button.styleSheet())

    @covers("LLFR-00001", "LLFR-00002", "LLFR-00003")
    def test_new_button_is_inactive_with_normal_color(self) -> None:
        """A new button is checkable, inactive and has the normal color.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.button.isCheckable())
        self.assertEqual(self.button.text(), "Open file")
        self.assert_inactive_look()
        self.assertNotEqual(self.toggle_module.ACTIVE_COLOR_STR,
                            self.toggle_module.NORMAL_COLOR_STR)

    @covers("LLFR-00001")
    def test_click_activates_and_changes_color(self) -> None:
        """A mouse click makes the button active with the active color.

        Inputs: none.
        Outputs: none.
        """
        self.mouse_click()
        self.assert_active_look()
        self.assertEqual(self.activated_count_i, 1)
        self.assertEqual(self.deactivated_count_i, 0)

    @covers("LLFR-00001")
    def test_programmatic_click_activates(self) -> None:
        """``click()`` activates the button like a mouse click.

        Inputs: none.
        Outputs: none.
        """
        self.button.click()
        self.assert_active_look()
        self.assertEqual(self.activated_count_i, 1)

    @covers("LLFR-00001")
    def test_rendered_color_changes_when_active(self) -> None:
        """The painted button shows the active color only while active.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        self.button.resize(120, 40)
        self.application.processEvents()

        def center_color_str() -> str:
            """Return the color painted at the centre-left of the button.

            Inputs: none.
            Outputs: the color as a lowercase "#rrggbb" string.
            """
            image = self.button.grab().toImage()
            return QColor(image.pixel(6, image.height() // 2)).name()

        inactive_color_str = center_color_str()
        self.mouse_click()
        active_color_str = center_color_str()
        self.assertEqual(active_color_str,
                         self.toggle_module.ACTIVE_COLOR_STR)
        self.assertNotEqual(inactive_color_str, active_color_str)

    @covers("LLFR-00002")
    def test_second_click_deactivates_and_restores_color(self) -> None:
        """A second click returns the button to inactive and normal color.

        Inputs: none.
        Outputs: none.
        """
        self.mouse_click()
        self.mouse_click()
        self.assert_inactive_look()
        self.assertEqual(self.activated_count_i, 1)
        self.assertEqual(self.deactivated_count_i, 1)

    @covers("LLFR-00001", "LLFR-00002")
    def test_repeated_clicks_alternate_state(self) -> None:
        """Each click flips the state and emits the matching signal.

        Inputs: none.
        Outputs: none.
        """
        for click_number_i in range(1, 7):
            self.mouse_click()
            if click_number_i % 2 == 1:
                self.assert_active_look()
            else:
                self.assert_inactive_look()
        self.assertEqual(self.activated_count_i, 3)
        self.assertEqual(self.deactivated_count_i, 3)

    @covers("LLFR-00003")
    def test_finish_restores_normal_color_quietly(self) -> None:
        """``finish()`` makes an active button inactive without signals.

        Inputs: none.
        Outputs: none.
        """
        self.mouse_click()
        self.button.finish()
        self.application.processEvents()
        self.assert_inactive_look()
        self.assertEqual(self.activated_count_i, 1)
        self.assertEqual(self.deactivated_count_i, 0)

    @covers("LLFR-00003")
    def test_finish_on_inactive_button_does_nothing(self) -> None:
        """``finish()`` on an inactive button keeps it inactive, no signal.

        Inputs: none.
        Outputs: none.
        """
        self.button.finish()
        self.assert_inactive_look()
        self.assertEqual(self.activated_count_i, 0)
        self.assertEqual(self.deactivated_count_i, 0)

    @covers("LLFR-00001", "LLFR-00003")
    def test_click_after_finish_activates_again(self) -> None:
        """After ``finish()``, the next click activates the button again.

        Inputs: none.
        Outputs: none.
        """
        self.mouse_click()
        self.button.finish()
        self.mouse_click()
        self.assert_active_look()
        self.assertEqual(self.activated_count_i, 2)
        self.assertEqual(self.deactivated_count_i, 0)

    @covers("LLFR-00001")
    def test_finish_from_activated_slot(self) -> None:
        """A slot on ``activated`` can call ``finish()`` right away.

        This is how "Open file" is used: the click starts the function
        and the function calls ``finish()`` when it ends.

        Inputs: none.
        Outputs: none.
        """
        self.button.activated.connect(self.button.finish)
        self.mouse_click()
        self.assert_inactive_look()
        self.assertEqual(self.activated_count_i, 1)
        self.assertEqual(self.deactivated_count_i, 0)

    @covers("LLFR-00001")
    def test_style_is_scoped_to_object_name(self) -> None:
        """The stylesheet targets the button's objectName only.

        Inputs: none.
        Outputs: none.
        """
        self.button.setObjectName("tip_button")
        self.mouse_click()
        self.assertIn("#tip_button", self.button.styleSheet())
        self.assert_active_look()

    @covers("LLFR-00001", "LLFR-00002")
    def test_two_buttons_are_independent(self) -> None:
        """Activating one button leaves another button inactive.

        Inputs: none.
        Outputs: none.
        """
        other_button = self.toggle_module.ToggleButton("Tip")
        other_button.show()
        self.mouse_click()
        self.assertTrue(self.button.is_active())
        self.assertFalse(other_button.is_active())
        self.assertEqual(other_button.current_background_color_str(),
                         self.toggle_module.NORMAL_COLOR_STR)
        other_button.close()
        other_button.deleteLater()

    @covers("LLFR-00001")
    def test_disabled_button_ignores_click(self) -> None:
        """A disabled button is not activated by a click.

        Inputs: none.
        Outputs: none.
        """
        self.button.setEnabled(False)
        self.mouse_click()
        self.assert_inactive_look()
        self.assertEqual(self.activated_count_i, 0)


if __name__ == "__main__":
    unittest.main()
