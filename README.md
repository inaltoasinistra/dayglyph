# Dayglyph

Encode a calendar date as **two Unicode characters** for terminal prompts and logs.
Decode a token to the matching date nearest to today in UTC.

## Usage

Requires Python 3.10+; no dependencies.

```sh
./dayglyph                      # Today in UTC
./dayglyph 2026-11-11            # ∫‡
./dayglyph --decode '∫‡'         # Nearest matching date
./dayglyph --decode '∫‡' --reference-date 2026-11-11  # Use a reference date instead of today
./dayglyph --alphabet            # Encoding alphabet and its length
./dayglyph --test                # Examples, cycle length, and wraparound
```

To install the command on your PATH:

```sh
mkdir -p ~/.local/bin
install -m 755 dayglyph ~/.local/bin/dayglyph
```

## Format

- The alphabet contains 151 characters. Its readable groups and Unicode names are in the source.
- Encoding order is determined by sorting the SHA-256 digests of `short-ts-v1:` followed by each character,
  encoded as UTF-8. This seed is part of the format.
- Day zero is `0001-01-01` in the proleptic Gregorian calendar.
- Reduce the number of days since day zero modulo **22,801** (`151²`).
- Encode that value in base 151, padded to two characters with the zero glyph (`e`).
- Decoding chooses the nearest matching date within years 1–9999, preferring the future on an exact tie.

Tokens repeat about every **62.4 years**, so decoding normally resolves dates within about 31.2 years of today.
A token is not a permanent, globally unique date identifier. Time of day is outside the format.
Use `--reference-date YYYY-MM-DD` with `--decode` when you know roughly when the glyph was created; it selects the
matching date nearest that date instead of today. This does not change the format's fixed day zero.

Two characters means two Unicode code points, not two bytes. Glyph rendering and double-click selection depend
on your terminal and font.

## Tests

```sh
python3 -m unittest -v
```

The tests cover every day code, wraparound, date boundaries, deterministic alphabet ordering, and CLI behavior.
