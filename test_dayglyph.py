import hashlib
import io
import os
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
decode_timestamp = dayglyph.decode_timestamp
encode_date = dayglyph.encode_date
encode_timestamp = dayglyph.encode_timestamp
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


class TestTimestamps(unittest.TestCase):
    def test_precision(self) -> None:
        value = datetime(2026, 11, 11, 9, 40, 23, 123456, tzinfo=timezone.utc)
        for precision, token, expected in [
            ("minute", "¡γ∩♠", "2026-11-11T09:40Z"),
            ("second", ":●⬡↙.", "2026-11-11T09:40:23Z"),
            ("millisecond", "∩⬡p⊗∋α", "2026-11-11T09:40:23.123Z"),
            ("microsecond", "∂uΞ⬡⌥→∈", "2026-11-11T09:40:23.123456Z"),
        ]:
            with self.subTest(precision=precision):
                self.assertEqual(encode_timestamp(value, precision), token)
                local = value.astimezone().isoformat(timespec=dayglyph.TIME_PRECISIONS[precision][2])
                self.assertEqual(dayglyph.decode_token(token, value.isoformat()), f"{expected}\n{local}")

    def test_offset_and_midnight(self) -> None:
        value = datetime(2026, 11, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(dayglyph.parse_timestamp("2026-11-11T19:00:00-05:00"), value)
        self.assertEqual(
            encode_timestamp(datetime.fromisoformat("2026-11-11T19:00:00-05:00"), "second"),
            encode_timestamp(value, "second"),
        )
        self.assertEqual(decode_timestamp(encode_timestamp(value, "second"), value), value)

    def test_nearest(self) -> None:
        value = datetime.min.replace(tzinfo=timezone.utc)
        token = encode_timestamp(value, "minute")
        cycle = timedelta(microseconds=151 ** 4 * 60_000_000)
        midpoint = value + cycle / 2
        self.assertEqual(decode_timestamp(token, midpoint - timedelta(microseconds=1)), value)
        self.assertEqual(decode_timestamp(token, midpoint), value + cycle)
        self.assertEqual(decode_timestamp(token, midpoint + timedelta(microseconds=1)), value + cycle)

    def test_wraparound(self) -> None:
        value = datetime(2026, 11, 11, 9, 40, 23, 123456, tzinfo=timezone.utc)
        for precision, (length, unit, _) in dayglyph.TIME_PRECISIONS.items():
            with self.subTest(precision=precision):
                cycle = timedelta(microseconds=151 ** length * unit)
                token = encode_timestamp(value, precision)
                self.assertEqual(encode_timestamp(value + cycle, precision), token)
                self.assertEqual(decode_timestamp(token, value + cycle),
                                 value + cycle - timedelta(microseconds=dayglyph.timestamp_microseconds(value) % unit))

    def test_limits(self) -> None:
        for value in [
            datetime.min.replace(tzinfo=timezone.utc),
            datetime.max.replace(tzinfo=timezone.utc),
        ]:
            for precision, (_, unit, _) in dayglyph.TIME_PRECISIONS.items():
                with self.subTest(value=value, precision=precision):
                    expected = value - timedelta(microseconds=dayglyph.timestamp_microseconds(value) % unit)
                    self.assertEqual(decode_timestamp(encode_timestamp(value, precision), value), expected)

    def test_invalid(self) -> None:
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            dayglyph.parse_timestamp("2026-11-11T09:40:23")
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            encode_timestamp(datetime(2026, 11, 11, 9, 40), "minute")
        for token in ["e", "eee", "eeeeeeee", "0000"]:
            with self.subTest(token=token), self.assertRaises(ValueError):
                dayglyph.decode_token(token, None)


class TestCli(unittest.TestCase):
    def test_executable(self) -> None:
        executable = Path(__file__).with_name("dayglyph").resolve()
        result = subprocess.run([str(executable), "2026-11-11"], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "∫‡\n")

    def test_timestamp(self) -> None:
        executable = Path(__file__).with_name("dayglyph").resolve()
        for precision, expected, utc, local in [
            ("minute", "¡γ∩♠", "2026-11-11T09:40Z", "2026-11-11T04:40-05:00"),
            ("second", ":●⬡↙.", "2026-11-11T09:40:23Z", "2026-11-11T04:40:23-05:00"),
            ("millisecond", "∩⬡p⊗∋α", "2026-11-11T09:40:23.123Z", "2026-11-11T04:40:23.123-05:00"),
            ("microsecond", "∂uΞ⬡⌥→∈", "2026-11-11T09:40:23.123456Z", "2026-11-11T04:40:23.123456-05:00"),
        ]:
            with self.subTest(precision=precision):
                encoded = subprocess.run(
                    [str(executable), "--precision", precision, "2026-11-11T09:40:23.123456Z"],
                    capture_output=True, text=True, check=True,
                )
                self.assertEqual(encoded.stdout.strip(), expected)
                result = subprocess.run(
                    [str(executable), "--decode", expected, "--reference-date", "2026-11-11"],
                    capture_output=True, text=True, check=True,
                    env={**os.environ, "TZ": "EST5EDT,M3.2.0,M11.1.0"},
                )
                self.assertEqual(result.stdout, f"{utc}\n{local}\n")

    def test_precision_aliases(self) -> None:
        executable = Path(__file__).with_name("dayglyph").resolve()
        for alias, full_name, expected in [
            ("milli", "millisecond", "∩⬡p⊗∋α"),
            ("micro", "microsecond", "∂uΞ⬡⌥→∈"),
        ]:
            with self.subTest(alias=alias):
                value = "2026-11-11T09:40:23.123456Z"
                result = subprocess.run(
                    [str(executable), "--precision", alias, value],
                    capture_output=True, text=True, check=True,
                )
                self.assertEqual(result.stdout.strip(), expected)
                self.assertEqual(dayglyph.encode_value(value, alias), dayglyph.encode_value(value, full_name))

    def test_timestamp_input(self) -> None:
        executable = Path(__file__).with_name("dayglyph").resolve()
        for arguments, expected in [
            (["2026-11-11T23:40:23Z"], encode_date(date(2026, 11, 11))),
            (["2026-11-11T19:40:23-05:00"], encode_date(date(2026, 11, 12))),
            (["2026-11-11T23:40:23"], encode_date(date(2026, 11, 12))),
            (["--precision", "minute", "2026-11-11T23:40:23"], dayglyph.encode_value(
                "2026-11-12T04:40:23Z", "minute")),
        ]:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [str(executable), *arguments],
                    capture_output=True, text=True, check=True,
                    env={**os.environ, "TZ": "EST5EDT,M3.2.0,M11.1.0"},
                )
                self.assertEqual(result.stdout, f"{expected}\n")

    def test_input_help(self) -> None:
        executable = Path(__file__).with_name("dayglyph").resolve()
        result = subprocess.run([str(executable), "--help"], capture_output=True, text=True, check=True)
        self.assertIn("YYYY-MM-DDTHH:MM[:SS[.ffffff]]Z", result.stdout)
        self.assertIn("YYYY-MM-DDTHH:MM[:SS[.ffffff]]±HH:MM", result.stdout)
        self.assertIn("local: YYYY-MM-DDTHH:MM[:SS[.ffffff]] (no offset)", result.stdout)
        self.assertIn("no input: current time", result.stdout)
        self.assertIn("timestamps are converted to UTC before encoding", result.stdout)

    @patch("sys.argv", ["dayglyph", "--precision", "second"])
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("dayglyph.datetime", wraps=datetime)
    def test_timestamp_now(self, clock: MagicMock, output: io.StringIO) -> None:
        clock.now.return_value = datetime(2026, 11, 11, 9, 40, 23, tzinfo=timezone.utc)
        main()
        self.assertEqual(output.getvalue(), ":●⬡↙.\n")
        clock.now.assert_called_once_with(timezone.utc)

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

    @patch("sys.argv", ["dayglyph", "--decode", "ee", "--reference-date", "0001-01-01"])
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("dayglyph.datetime", wraps=datetime)
    def test_decode_reference_date(self, clock: MagicMock, output: io.StringIO) -> None:
        main()
        self.assertEqual(output.getvalue(), "0001-01-01\n")
        clock.now.assert_not_called()

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
            ["--reference-date", "2026-11-11"],
            ["2026-11-11", "--reference-date", "2026-11-11"], ["--test", "--reference-date", "2026-11-11"],
            ["--alphabet", "--reference-date", "2026-11-11"],
            ["--decode", "ee", "--reference-date", "not-a-date"],
            ["--precision", "minute", "2026-11-11"],
            ["--decode", "eee"],
            ["--decode", "eeee", "--reference-date", "2026-11-11T09:40"],
            ["--decode", "eeee", "--precision", "minute"],
            ["--test", "--precision", "second"],
        ]:
            with self.subTest(arguments=arguments):
                argv[:] = ["dayglyph", *arguments]
                with self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code, 2)
        self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
