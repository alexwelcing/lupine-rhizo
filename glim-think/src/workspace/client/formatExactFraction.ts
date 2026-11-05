/** Exact short decimals when possible; a nonzero fraction is never rounded to zero. */
export function formatExactFraction(value: { numerator: string; denominator: string }): string {
  let n = BigInt(value.numerator); const d = BigInt(value.denominator);
  if (d <= 0n) throw new Error("Invalid denominator");
  const sign = n < 0n ? "-" : ""; if (n < 0n) n = -n;
  let scale = 1n;
  for (let places = 0; places <= 6; places++, scale *= 10n) {
    if (n * scale % d !== 0n) continue;
    const digits = (n * scale / d).toString().padStart(places + 1, "0");
    return sign + (places ? digits.slice(0, -places) + "." + digits.slice(-places) : digits);
  }
  return value.numerator + "/" + value.denominator;
}
