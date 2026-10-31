"""Tests for the search of signal names (HLFR-00033, HLFR-00034)."""

import random
import time
import unittest

from tests.support import covers

from model.signal_search import (
    NO_MATCH_TEXT_STR, allowed_typo_count, has_close_substring,
    normalize_text, search_signals, split_search_words, word_match_kind)


def reference_substring_distance(word_str: str, name_str: str) -> int:
    """Compute the smallest edit distance between a word and any part.

    Plain dynamic programming (Sellers), used to check the fast
    algorithm of the model.

    Inputs:
        word_str: the search word.
        name_str: the name in which a part is searched.
    Outputs: the smallest number of wrong, missing or extra characters
        between word_str and any substring of name_str.
    """
    previous_row_list = [0] * (len(name_str) + 1)
    for word_index_i in range(1, len(word_str) + 1):
        current_row_list = [word_index_i] + [0] * len(name_str)
        for name_index_i in range(1, len(name_str) + 1):
            cost_i = int(word_str[word_index_i - 1]
                         != name_str[name_index_i - 1])
            current_row_list[name_index_i] = min(
                previous_row_list[name_index_i - 1] + cost_i,
                previous_row_list[name_index_i] + 1,
                current_row_list[name_index_i - 1] + 1)
        previous_row_list = current_row_list
    return min(previous_row_list)


class NormalizeTest(unittest.TestCase):
    """Check how words and names are normalized."""

    @covers("LLFR-00098", "HLFR-00034")
    def test_lowercase(self) -> None:
        """Text is turned into lowercase.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(normalize_text("EnGiNe"), "engine")

    @covers("LLFR-00100", "HLFR-00034")
    def test_separators_removed(self) -> None:
        """Spaces, underscores, hyphens and dots are removed.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(normalize_text("a_b-c.d e"), "abcde")

    @covers("LLFR-00105", "LLFR-00100", "HLFR-00034")
    def test_split_search_words(self) -> None:
        """Text is split at spaces, words are normalized, empties dropped.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(split_search_words("  Mate_us  so-2.5 _ "),
                         ["mateus", "so25"])
        self.assertEqual(split_search_words("   "), [])
        self.assertEqual(split_search_words(""), [])


class TypoAllowanceTest(unittest.TestCase):
    """Check the typo allowance of LLFR-00101."""

    @covers("LLFR-00101", "HLFR-00034")
    def test_allowed_typo_count(self) -> None:
        """0 below 4 characters, then 1 per full 4 characters.

        Inputs: none.
        Outputs: none.
        """
        expected_dict = {1: 0, 2: 0, 3: 0, 4: 1, 7: 1, 8: 2, 11: 2,
                         12: 3}
        for length_i, typos_i in expected_dict.items():
            self.assertEqual(allowed_typo_count("x" * length_i), typos_i)

    @covers("LLFR-00101", "HLFR-00034")
    def test_three_characters_need_exact(self) -> None:
        """A 3-character word with one typo does not match.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(word_match_kind("rpm", "rpm"), "exact")
        self.assertEqual(word_match_kind("rpn", "enginerpm"), "")
        self.assertEqual(word_match_kind("rp", "enginerpm"), "exact")
        self.assertEqual(search_signals(["Engine_RPM"], "rpn"), [])

    @covers("LLFR-00101", "HLFR-00034")
    def test_one_edit_of_each_kind(self) -> None:
        """Wrong, missing and extra characters each count as one typo.

        Inputs: none.
        Outputs: none.
        """
        # 4 characters: wrong, missing, extra.
        self.assertEqual(word_match_kind("spxe", "enginespeed"), "typo")
        self.assertEqual(word_match_kind("spee", "enginespeed"), "exact")
        self.assertEqual(word_match_kind("sped", "enginespeed"), "typo")
        self.assertEqual(word_match_kind("spxx", "enginespeed"), "")
        self.assertEqual(word_match_kind("speeed", "enginespeed"), "typo")
        # 7 characters (presure is missing an "s").
        self.assertEqual(word_match_kind("presure", "pressure"), "typo")
        self.assertEqual(word_match_kind("pressxre", "pressure"), "typo")

    @covers("LLFR-00101", "HLFR-00034")
    def test_two_edits_boundary(self) -> None:
        """Two typos fail for 7 characters and pass for 8.

        Inputs: none.
        Outputs: none.
        """
        # 7 characters, two wrong characters.
        self.assertEqual(word_match_kind("prxsxre", "pressure"), "")
        # 8 characters, two wrong characters.
        self.assertEqual(word_match_kind("prxssxre", "pressure"), "typo")
        # 8 characters, one missing and one extra character.
        self.assertEqual(word_match_kind("pessuree", "xpressurex"),
                         "typo")
        # 8 characters, three wrong characters fail.
        self.assertEqual(word_match_kind("pxxssxre", "pressure"), "")

    @covers("LLFR-00101", "HLFR-00034")
    def test_requirement_examples(self) -> None:
        """presure finds Pressure and sine_2hz finds Sine_3Hz.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(search_signals(["Time", "Pressure"], "presure"),
                         ["Pressure"])
        self.assertEqual(search_signals(["Time", "Sine_3Hz"], "sine_2hz"),
                         ["Sine_3Hz"])

    @covers("LLFR-00101", "HLFR-00034")
    def test_fast_check_matches_reference(self) -> None:
        """The fast check agrees with plain dynamic programming.

        Inputs: none.
        Outputs: none.
        """
        generator = random.Random(37)
        for _ in range(3000):
            word_str = "".join(generator.choice("abc") for _ in range(
                generator.randint(1, 12)))
            name_str = "".join(generator.choice("abc") for _ in range(
                generator.randint(0, 20)))
            distance_i = reference_substring_distance(word_str, name_str)
            for maximum_i in range(0, 4):
                self.assertEqual(
                    has_close_substring(word_str, name_str, maximum_i),
                    distance_i <= maximum_i,
                    (word_str, name_str, maximum_i))


class SearchSignalsTest(unittest.TestCase):
    """Check search_signals against LLFR-00096 to LLFR-00105."""

    @covers("LLFR-00096", "HLFR-00033")
    def test_empty_text_returns_all(self) -> None:
        """Empty or spaces-only text gives all names in file order.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", "b", "a"]
        for text_str in ("", " ", "    "):
            result_list = search_signals(name_list, text_str)
            self.assertEqual(result_list, name_list)
            self.assertIsNot(result_list, name_list)

    @covers("LLFR-00097", "HLFR-00033")
    def test_no_match(self) -> None:
        """No match gives an empty list and the no-match text is fixed.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(search_signals(["Time", "Speed"], "voltage"), [])
        self.assertEqual(search_signals([], "x"), [])
        self.assertEqual(NO_MATCH_TEXT_STR, "No matching signals")

    @covers("LLFR-00098", "HLFR-00034")
    def test_case_insensitive(self) -> None:
        """Case is ignored in the text and in the names.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(search_signals(["ENGINE", "fan"], "eNgInE"),
                         ["ENGINE"])
        self.assertEqual(search_signals(["engine"], "ENGINE"), ["engine"])

    @covers("LLFR-00099", "HLFR-00034")
    def test_partial_name(self) -> None:
        """A word matches at the start, middle and end of a name.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["SpeedFront", "FrontSpeedLeft", "WheelSpeed", "Fan"]
        self.assertEqual(search_signals(name_list, "speed"),
                         ["SpeedFront", "FrontSpeedLeft", "WheelSpeed"])

    @covers("LLFR-00100", "HLFR-00034")
    def test_separators(self) -> None:
        """Separators are ignored in text and names, spaces in names.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(search_signals(["Time", "Engine_Speed"],
                                        "enginespeed"), ["Engine_Speed"])
        self.assertEqual(search_signals(["enginespeed"], "engine_speed"),
                         ["enginespeed"])
        self.assertEqual(search_signals(["enginespeed"], "en-gine.spe_ed"),
                         ["enginespeed"])
        self.assertEqual(search_signals(["Engine Speed", "x"],
                                        "enginespeed"), ["Engine Speed"])
        self.assertEqual(search_signals(["Engine-Speed.A"], "speeda"),
                         ["Engine-Speed.A"])

    @covers("LLFR-00105", "HLFR-00034")
    def test_requirement_multi_word_example(self) -> None:
        """mate so 25 finds only mateus_soares_rodrigues 2025.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["mateus_soares_rodrigues 2026",
                     "mateus_soares_rodrigues 2025"]
        self.assertEqual(search_signals(name_list, "mate so 25"),
                         ["mateus_soares_rodrigues 2025"])

    @covers("LLFR-00105", "HLFR-00034")
    def test_every_word_any_order(self) -> None:
        """Every word must match; the order of the words is free.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Front_Left_Speed", "Front_Right_Speed", "Rear_Left"]
        self.assertEqual(search_signals(name_list, "speed left"),
                         ["Front_Left_Speed"])
        self.assertEqual(search_signals(name_list, "left   front"),
                         ["Front_Left_Speed"])
        self.assertEqual(search_signals(name_list, "left voltage"), [])

    @covers("LLFR-00105", "HLFR-00034")
    def test_repeated_words(self) -> None:
        """A repeated word matches like the single word.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Speed", "Speed_Speed", "Fan"]
        self.assertEqual(search_signals(name_list, "speed speed"),
                         ["Speed", "Speed_Speed"])

    @covers("LLFR-00105", "LLFR-00101", "HLFR-00034")
    def test_typo_per_word(self) -> None:
        """Each word gets its own typo allowance.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Engine_Speed_Front", "Engine_Front"]
        self.assertEqual(search_signals(name_list, "engin spxed"),
                         ["Engine_Speed_Front"])
        self.assertEqual(search_signals(name_list, "xngine fxont"),
                         ["Engine_Speed_Front", "Engine_Front"])

    @covers("LLFR-00102", "HLFR-00034")
    def test_group_order(self) -> None:
        """Starts-with exact first, other exact second, typo last.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Spead_Rear", "Wheel_Speed", "Speed_Front",
                     "Spead_Front", "Rear_Speed", "Speed_Rear", "Fan"]
        self.assertEqual(search_signals(name_list, "speed"),
                         ["Speed_Front", "Speed_Rear", "Wheel_Speed",
                          "Rear_Speed", "Spead_Rear", "Spead_Front"])

    @covers("LLFR-00102", "LLFR-00105", "HLFR-00034")
    def test_group_one_uses_first_word_only(self) -> None:
        """Group 1 depends on the first typed word, not on the others.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Rear_Speed", "Speed_Rear"]
        # Speed_Rear starts with "speed", which is the first word.
        self.assertEqual(search_signals(name_list, "speed rear"),
                         ["Speed_Rear", "Rear_Speed"])
        # With "rear" first, Rear_Speed is in group 1.
        self.assertEqual(search_signals(name_list, "rear speed"),
                         ["Rear_Speed", "Speed_Rear"])

    @covers("LLFR-00102", "HLFR-00034")
    def test_typo_word_moves_name_to_group_three(self) -> None:
        """A starts-with name that needs a typo for a word is in group 3.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Speed_Reer", "Wheel_Speed_Rear"]
        self.assertEqual(search_signals(name_list, "speed rear"),
                         ["Wheel_Speed_Rear", "Speed_Reer"])

    @covers("LLFR-00102", "LLFR-00100", "HLFR-00034")
    def test_starts_with_uses_normalized_name(self) -> None:
        """Group 1 compares the normalized name with the first word.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["X_Engine", "_Engine-Speed"]
        self.assertEqual(search_signals(name_list, "engine"),
                         ["_Engine-Speed", "X_Engine"])

    @covers("LLFR-00099", "LLFR-00054", "HLFR-00033")
    def test_time_signal_searchable(self) -> None:
        """The time signal is found like any other signal.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", "Engine_Speed", "Lap_Time"]
        self.assertEqual(search_signals(name_list, "time"),
                         ["Time", "Lap_Time"])
        self.assertEqual(search_signals(name_list, "TI"),
                         ["Time", "Lap_Time"])

    @covers("LLFR-00095", "HLFR-00033")
    def test_fast_enough_for_typing(self) -> None:
        """1,000 long names and 3 words are searched quickly.

        Inputs: none.
        Outputs: none.
        """
        generator = random.Random(95)
        alphabet_str = "abcdefghijklmnopqrstuvwxyz0123456789_"
        name_list = ["".join(generator.choice(alphabet_str)
                             for _ in range(60)) for _ in range(1000)]
        start_s = time.perf_counter()
        search_signals(name_list, "engine speed_front temperature")
        elapsed_s = time.perf_counter() - start_s
        self.assertLess(elapsed_s, 0.5)


if __name__ == "__main__":
    unittest.main()
