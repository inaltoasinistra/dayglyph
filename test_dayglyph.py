import hashlib
import io
import re
import subprocess
import sys
import unicodedata
import unittest
from datetime import date, datetime, timedelta, timezone
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from unittest.mock import MagicMock, patch

# Load the extensionless executable as a module so patches target its globals.
spec = spec_from_loader("dayglyph", SourceFileLoader("dayglyph", str(Path(__file__).with_name("dayglyph"))))
assert spec is not None and spec.loader is not None
dayglyph = module_from_spec(spec)
sys.modules[spec.name] = dayglyph
spec.loader.exec_module(dayglyph)

ALPHABET = dayglyph.ALPHABET
CYCLE_DAYS = dayglyph.CYCLE_DAYS
SHUFFLED_ALPHABET = dayglyph.SHUFFLED_ALPHABET
decode_date = dayglyph.decode_date
encode_date = dayglyph.encode_date
main = dayglyph.main
shift_years = dayglyph.shift_years
shuffle_alphabet = dayglyph.shuffle_alphabet


REFERENCE = date(2026, 11, 11)


class TestAlphabet(unittest.TestCase):
    def test_membership(self) -> None:
        expected = (
            "abcdefghijklmnopqrstuvwxyz+@_ΓΔΘΛΞΠΣΦΨΩαβγδεζηθλμξπφψω←↑→↓∞√∫≈≠∩∀∂∃∇∈∉∋∧∨∠∴∵"
            "⊕⊖⊗⊘⊙⊥⊤⊢⊣■□▲△▼▽◀▶●○★☆♠♣♥♦♪♫≡≢≤≥≪≫∮⌘⌥⌁⌗⌂⏏↖↗↘↙♭♮♯⬡⬢◇◆◐◑◒◓"
            ".,:/%·•…‽¡¿«»¬⌐⁜§¶†‡"
        )
        self.assertCountEqual(ALPHABET, expected)
        self.assertEqual(len(set(ALPHABET)), 151)
        self.assertEqual(CYCLE_DAYS, 22801)
        for character in ALPHABET:
            with self.subTest(character=character):
                self.assertTrue(character.isprintable())
                self.assertNotIn(unicodedata.category(character)[0], "CMZ")
                self.assertNotIn(unicodedata.east_asian_width(character), "WF")

    def test_shuffle(self) -> None:
        self.assertCountEqual(SHUFFLED_ALPHABET, ALPHABET)
        hashes = [
            hashlib.sha256(f"short-ts-v1:{character}".encode("utf-8")).digest() for character in SHUFFLED_ALPHABET
        ]
        self.assertEqual(hashes, sorted(hashes))
        self.assertEqual(shuffle_alphabet(ALPHABET[::-1]), SHUFFLED_ALPHABET)
        self.assertNotEqual(ALPHABET, SHUFFLED_ALPHABET)

    def test_names(self) -> None:
        source = Path(__file__).with_name("dayglyph").read_text()
        annotations = dict(re.findall(r'^    "(.)"  # (.+)$', source, re.MULTILINE))
        special = set(ALPHABET) - set("abcdefghijklmnopqrstuvwxyz")
        self.assertEqual(set(annotations), special)
        for character in special:
            with self.subTest(character=character):
                self.assertEqual(annotations[character], unicodedata.name(character))

    def test_shell_arguments(self) -> None:
        tokens = [character * 2 for character in ALPHABET]
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", "printf '%s\\n' " + " ".join(tokens)],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.splitlines(), tokens)


class TestDates(unittest.TestCase):
    def test_encode(self) -> None:
        for value, expected in [
            ("0001-01-01", "ee"),
            ("0001-01-02", "e⊙"),
            ("2026-11-11", "∫‡"),
            ("0063-06-05", "dd"),
            ("0063-06-06", "ee"),
        ]:
            with self.subTest(value=value):
                self.assertEqual(encode_date(date.fromisoformat(value)), expected)

    def test_cycles(self) -> None:
        for cycles in [-3, -1, 0, 1, 3]:
            with self.subTest(cycles=cycles):
                value = REFERENCE + timedelta(days=22801 * cycles)
                self.assertEqual(encode_date(value), "∫‡")
                self.assertEqual(decode_date("∫‡", value), value)

    def test_decode(self) -> None:
        self.assertEqual(decode_date("dd", date.min), date(63, 6, 5))
        for token, expected in [
            ("ee", "1998-09-01"),
            ("dd", "1998-08-31"),
            (":/", "2049-06-17"),
            ("∀a", "2034-07-17"),
        ]:
            with self.subTest(token=token):
                self.assertEqual(decode_date(token, REFERENCE), date.fromisoformat(expected))

    def test_all_day_codes(self) -> None:
        # Check every modular residue against an independent day-by-day calendar.
        epoch = date(1, 1, 1)
        for day in range(22801):
            value = epoch + timedelta(days=day)
            token = encode_date(value)
            self.assertEqual(len(token), 2)
            self.assertEqual(token, SHUFFLED_ALPHABET[day // 151] + SHUFFLED_ALPHABET[day % 151])
            self.assertEqual(decode_date(token, value), value)

    def test_midpoint(self) -> None:
        lower = date(1, 1, 1)
        upper = lower + timedelta(days=22801)
        for days, expected in [(11400, lower), (11401, upper)]:
            with self.subTest(days=days):
                self.assertEqual(decode_date("ee", lower + timedelta(days=days)), expected)

    @patch("dayglyph.CYCLE_DAYS", 10)
    def test_tie(self) -> None:
        self.assertEqual(decode_date("ee", date(1, 1, 6)), date(1, 1, 11))

    def test_date_limits(self) -> None:
        for value in [date.min, date.max]:
            with self.subTest(value=value):
                self.assertEqual(decode_date(encode_date(value), value), value)

    def test_invalid(self) -> None:
        for token in [
            "", "e", "eee", "ee090909", "ee09:09:09", "ee\n", "0e", "e ", "∝e", "ee·090909",
            "「e", "」e", "【e", "】e", "※e",
        ]:
            with self.subTest(token=token), self.assertRaises(ValueError):
                decode_date(token, REFERENCE)

    def test_leap_day(self) -> None:
        leap = date(2024, 2, 29)
        for years, expected in [(1, "2025-02-28"), (-1, "2023-02-28"), (100, "2124-02-29")]:
            with self.subTest(years=years):
                self.assertEqual(shift_years(leap, years), date.fromisoformat(expected))


class TestCli(unittest.TestCase):
    def test_executable(self) -> None:
        executable = Path(__file__).with_name("dayglyph").resolve()
        result = subprocess.run([str(executable), "2026-11-11"], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "∫‡\n")

    @patch("sys.argv", new_callable=list)
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("dayglyph.datetime", wraps=datetime)
    def test_encode(self, clock: MagicMock, output: io.StringIO, argv: list[str]) -> None:
        clock.now.return_value = datetime(2026, 11, 11, 23, 59, 59, tzinfo=timezone.utc)
        for arguments, expected in [
            ([], "∫‡"),
            (["0001-01-01"], "ee"),
        ]:
            with self.subTest(arguments=arguments):
                output.seek(0)
                output.truncate()
                argv[:] = ["dayglyph", *arguments]
                main()
                self.assertEqual(output.getvalue(), expected + "\n")
        clock.now.assert_called_once_with(timezone.utc)

    @patch("sys.argv", new_callable=list)
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("dayglyph.datetime", wraps=datetime)
    def test_decode(self, clock: MagicMock, output: io.StringIO, argv: list[str]) -> None:
        clock.now.return_value = datetime(2026, 11, 11, 23, 59, 59, tzinfo=timezone.utc)
        for token, expected in [("ee", "1998-09-01"), (":/", "2049-06-17"), ("∀a", "2034-07-17")]:
            with self.subTest(token=token):
                output.seek(0)
                output.truncate()
                argv[:] = ["dayglyph", "--decode", token]
                main()
                self.assertEqual(output.getvalue(), expected + "\n")
        clock.now.assert_called_with(timezone.utc)

    @patch("sys.argv", ["dayglyph", "--alphabet"])
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_alphabet(self, output: io.StringIO) -> None:
        main()
        self.assertEqual(output.getvalue(), f"{SHUFFLED_ALPHABET}\nLength: 151\n")

    @patch("sys.argv", ["dayglyph", "--test"])
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("dayglyph.datetime", wraps=datetime)
    def test_examples(self, clock: MagicMock, output: io.StringIO) -> None:
        clock.now.return_value = datetime(2026, 11, 11, 9, 40, 23, tzinfo=timezone.utc)
        main()
        text = output.getvalue()
        self.assertIn("Epoch (day 0): 0001-01-01; offset from today: -739930 days", text)
        self.assertIn("Today      2026-11-11  ∫‡\n", text)
        self.assertIn("+1 year    2027-11-11  »θ\n", text)
        self.assertIn("-1 year    2025-11-11  ∨Ω\n", text)
        self.assertIn("+10 years  2036-11-11  ↗∩\n", text)
        self.assertIn("+100 years 2126-11-11  sq -> nearest: 2002-01-03\n", text)
        self.assertIn("Cycle: 22801 days (~62.4 years)", text)
        self.assertIn("First wraparound: 0063-06-06  ee\n", text)
        rows = text.split("Special-character tokens:\n")[1].splitlines()
        self.assertEqual([row.split()[0] for row in rows], [".,", ":/", "%·", "¬⌐", "⁜†", "↑∞"])
        for row in rows:
            token, value = row.split()
            self.assertEqual(decode_date(token, REFERENCE), date.fromisoformat(value))

    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("sys.argv", new_callable=list)
    def test_invalid_arguments(self, argv: list[str], output: io.StringIO) -> None:
        for arguments in [
            ["--test", "2026-01-01"], ["--test", "--decode", "ee"], ["--alphabet", "--test"],
            ["--time-separators"], ["--base", "64"], ["--decode", "ee090909"], ["not-a-date"],
            ["2026-01-01T09:40:23Z"],
        ]:
            with self.subTest(arguments=arguments):
                argv[:] = ["dayglyph", *arguments]
                with self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code, 2)
        self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
