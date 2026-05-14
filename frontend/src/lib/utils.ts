import { twMerge } from "tailwind-merge";

export function cn(...classes: (string | undefined | false | null)[]): string {
  return twMerge(classes.filter(Boolean).join(" "));
}

export function fmtUSD(v: number, options?: { compact?: boolean }): string {
  if (v == null || isNaN(v)) return "—";
  if (options?.compact) {
    if (Math.abs(v) >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
    if (Math.abs(v) >= 1e9)  return `$${(v / 1e9).toFixed(2)}B`;
    if (Math.abs(v) >= 1e6)  return `$${(v / 1e6).toFixed(2)}M`;
    if (Math.abs(v) >= 1e3)  return `$${(v / 1e3).toFixed(1)}K`;
    return `$${v.toFixed(0)}`;
  }
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v);
}

export function fmtPct(v: number | null | undefined, signed = true): string {
  if (v == null || isNaN(v)) return "—";
  const pct = v * 100;
  const sign = signed ? (pct >= 0 ? "+" : "") : "";
  return `${sign}${pct.toFixed(1)}%`;
}

export function fmtCompactNumber(v: number): string {
  if (Math.abs(v) >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (Math.abs(v) >= 1e9)  return `${(v / 1e9).toFixed(2)}B`;
  if (Math.abs(v) >= 1e6)  return `${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3)  return `${(v / 1e3).toFixed(1)}K`;
  return v.toFixed(0);
}
