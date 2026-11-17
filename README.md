# Dayglyph

Dayglyph was designed for terminal prompts and logs, where output is usually read in real time and the date
is almost never useful. Instead of spending ten characters on `YYYY-MM-DD`, it represents the date with just
two Unicode characters. If you later need to know whether a command ran two days or two weeks ago, you can
decode those characters; otherwise, they take up only two characters on screen.

Dayglyph also encodes UTC timestamps at finer precision in 4–7 characters. Decoding selects the matching date
or timestamp nearest to now in UTC, or to a reference date you provide.

## Usage

Requires Python 3.10+; no dependencies.

```sh
./dayglyph                      # Today in UTC
./dayglyph 2026-11-11            # ∫‡
./dayglyph --decode '∫‡'         # Nearest matching date
./dayglyph --decode '∫‡' --reference-date 2026-11-11  # Use a reference date instead of today
./dayglyph --precision minute 2026-11-11T09:40:23Z    # ¡γ∩♠
./dayglyph --precision second 2026-11-11T09:40:23Z    # :●⬡↙.
./dayglyph --precision millisecond 2026-11-11T09:40:23.123Z  # ∩⬡p⊗∋α
./dayglyph --precision microsecond 2026-11-11T09:40:23.123456Z  # ∂uΞ⬡⌥→∈
./dayglyph --decode '∂uΞ⬡⌥→∈' --reference-date 2026-11-11
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
- For dates, reduce the number of days since day zero modulo **22,801** (`151²`).
- Encode that value in base 151, padded to two characters with the zero glyph (`e`).
- Decoding chooses the nearest matching date within years 1–9999, preferring the future on an exact tie.

Tokens repeat about every **62.4 years**, so decoding normally resolves dates within about 31.2 years of today.
A token is not a permanent, globally unique date identifier.
Use `--reference-date YYYY-MM-DD` with `--decode` when you know roughly when the glyph was created; it selects the
matching date nearest that date instead of today. This does not change the format's fixed day zero.

For timestamps, `--precision` chooses the encoded resolution; the default remains `date`.
The positional input accepts `YYYY-MM-DD`, timestamps with `Z` or a UTC offset, and timestamps without an offset
(interpreted in the machine's local timezone). Timestamps are converted to UTC before encoding; with the default
`date` precision, they encode their UTC date. With no positional input, the current time is used.
`milli` and `micro` are aliases for `millisecond` and `microsecond`, respectively.

| Precision   | Characters | Approximate cycle |
|:------------|-----------:|------------------:|
| Minute      | 4          | 988.5 years       |
| Second      | 5          | 2,487.7 years     |
| Millisecond | 6          | 375.6 years       |
| Microsecond | 7          | 56.7 years        |

Timestamp input must include a UTC offset or `Z`; offsets are converted to UTC. Without an input, the current UTC
time is used. Lower precision truncates the timestamp rather than rounding it. Timestamp tokens encode the number
of units since `0001-01-01T00:00:00Z` modulo `151^characters`, so their cycles are not necessarily whole days.
Decoding infers precision from token length and prints two unlabeled lines: UTC with `Z`, then local time with its UTC
offset. Date-only tokens still print one line. `--reference-date` also accepts an ISO timestamp with an offset; a date
alone means midnight UTC. The closest matching timestamp is selected within years 1–9999,
preferring the future on an exact tie. Microsecond precision describes the representation, not the accuracy of the
machine's clock.

Character counts mean Unicode code points, not bytes. Glyph rendering and double-click selection depend
on your terminal and font.

## Tests

```sh
python3 -m unittest -v
```

The tests cover every day code, timestamp precisions, wraparound, date boundaries, deterministic alphabet ordering,
and CLI behavior.
