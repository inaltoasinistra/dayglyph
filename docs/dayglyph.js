// Indexed order from the Dayglyph CLI.
const alphabet = "g◆q☃bl◓⌘w≢∋▼◑:sφ…d△αo♪⌥+≈↘⌗↗∈⌂j@∂r∠¬⁜↖●hη§Ξ≪▶π♜eΛ◒_»⊢⏏⬢v¶Γ↑γ↙aε‽⊙≫♝∀⊣▽⊥♯○λ□∞•♣tΨ⊕nΠ♮Φ∮★≠▲c⊖,≡⊘☀♚p∵☄≤ψ%δz◐♫√/∃♞∴☂⌐←x∉fμ⊤⊗θ☆♛⌁∩¤k♭↓∫≥♠ζ◇ω‡ξ¿◀mβ¡⬡·→Ω«yΣu.■♥†";
const base = BigInt(alphabet.length);
const day = 86400000000n;
const epoch = Date.parse("0001-01-01T00:00Z");
const limit = BigInt(Date.parse("+010000-01-01T00:00Z") - epoch) * 1000n;
const formats = [
  {name:"Date", length:2, unit:day},
  {name:"Minute", length:4, unit:60000000n},
  {name:"Second", length:5, unit:1000000n},
  {name:"Millisecond", length:6, unit:1000n},
  {name:"Microsecond", length:7, unit:1n}
];

function parseInstant(input, allowDate) {
  if (!input) return BigInt(Date.now() - epoch) * 1000n;
  const match = /^(\d{4}-\d\d-\d\d)(?:T(\d\d:\d\d)(?::(\d\d)(?:\.(\d{1,6}))?)?(Z|[+-]\d\d:\d\d)?)?$/.exec(input);
  if (!match) throw Error("Enter an ISO date or timestamp, such as 2026-11-11T09:40:23Z.");
  const [, date, time, seconds = "00", fraction = "", zone = ""] = match;
  const midnight = new Date(date + "T00:00Z");
  if (isNaN(midnight) || date.startsWith("0000") || midnight.toISOString().slice(0,10) !== date)
    throw Error("Enter a valid date in years 0001–9999.");
  if (!time && !allowDate) throw Error("Include a time for this precision.");
  const ms = time ? Date.parse(date + "T" + time + ":" + seconds + zone) : midnight.getTime();
  if (!Number.isFinite(ms) || (time && time.slice(0,2) > "23")) throw Error("Enter a valid time and UTC offset.");
  const value = BigInt(ms - epoch) * 1000n + BigInt(fraction.padEnd(6,"0"));
  if (value < 0n || value >= limit) throw Error("UTC timestamp falls outside years 0001–9999.");
  return value;
}

function encodeGlyph(value, {length, unit}) {
  let offset = value / unit;
  let result = "";
  for (let i = 0; i < length; i++) {
    result = alphabet[Number(offset % base)] + result;
    offset /= base;
  }
  return result;
}

function decodeGlyph(token, reference) {
  const format = formats.find(f => f.length === [...token].length);
  if (!format) throw Error("Enter a glyph of 2, 4, 5, 6 or 7 characters.");
  let residue = 0n;
  for (const digit of token) {
    const index = alphabet.indexOf(digit);
    if (index < 0) throw Error("Character outside the alphabet: " + digit);
    residue = residue * base + BigInt(index);
  }
  if (format.unit === day) reference = reference / day * day;
  const first = residue * format.unit;
  const cycle = base ** BigInt(format.length) * format.unit;
  const lower = first + ((reference - first) / cycle) * cycle;
  const upper = lower + cycle;
  const nearest = upper < limit && upper - reference <= reference - lower ? upper : lower;
  const iso = new Date(epoch + Number(nearest / 1000n)).toISOString();
  if (format.unit === day) return iso.slice(0,10);
  if (format.length === 7) return iso.slice(0,-1) + String(nearest % 1000n).padStart(3,"0") + "Z";
  return iso.slice(0, {4:16,5:19,6:23}[format.length]) + "Z";
}

const element = id => document.getElementById(id);
for (const format of formats) element("precision").add(new Option(format.name, format.name));
element("precision").value = "Second";
const instant = element("instant");
const token = element("token");
instant.value = new Date().toISOString();
element("version").textContent = encodeGlyph(parseInstant("1010-01-01", true), formats[0]);
element("alphabet").textContent = alphabet;
element("count").textContent = alphabet.length + " characters";

function bindForm(formId, outputId, convert) {
  const form = element(formId);
  const result = element(outputId);
  function update() {
    try {
      result.value = form.checkValidity() ? convert() : "";
    } catch {
      result.value = "";
    }
  }
  form.addEventListener("input", update);
  form.addEventListener("change", update);
  form.addEventListener("submit", event => event.preventDefault());
  return update;
}
const updateDecoded = bindForm("decode", "decoded", () => decodeGlyph(token.value.trim(),
  parseInstant(element("reference").value, true)));
const updateEncoded = bindForm("encode", "encoded", () => {
  const format = formats[element("precision").selectedIndex];
  const glyph = encodeGlyph(parseInstant(instant.value.trim(), format.unit === day), format);
  if (clockTimer !== null) {
    token.value = glyph;
    updateDecoded();
  }
  return glyph;
});

const refresh = element("refresh");
let clockTimer = null;

function refreshTimestamp() {
  if (document.activeElement === instant || document.activeElement === token) return;
  instant.value = new Date().toISOString();
  updateEncoded();
}

function setAutoRefresh(enabled) {
  clearInterval(clockTimer);
  clockTimer = null;
  if (enabled) {
    clockTimer = setInterval(refreshTimestamp, 1000);
    refreshTimestamp();
  }
  refresh.setAttribute("aria-pressed", String(enabled));
  refresh.textContent = enabled ? "Auto-refresh on" : "Auto-refresh off";
}

refresh.addEventListener("click", () => setAutoRefresh(clockTimer === null));
instant.addEventListener("input", () => setAutoRefresh(false));
token.addEventListener("input", () => setAutoRefresh(false));
setAutoRefresh(true);
