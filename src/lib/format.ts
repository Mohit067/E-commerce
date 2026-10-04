export function inr(n: number | string): string {
  const v = typeof n === "string" ? parseFloat(n) : n;
  if (!isFinite(v)) return "₹0";
  return "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function stars(r: number): string {
  const f = Math.round(Math.min(5, Math.max(0, r)));
  return "★".repeat(f) + "☆".repeat(5 - f);
}
