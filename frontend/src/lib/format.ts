export function fmtUSD(v: number): string {
  if (v == null || isNaN(v)) return "$0";
  const abs = Math.abs(v);
  let out: string;
  if (abs >= 1e12) out = `${(v / 1e12).toFixed(2)}T`;
  else if (abs >= 1e9) out = `${(v / 1e9).toFixed(2)}B`;
  else if (abs >= 1e6) out = `${(v / 1e6).toFixed(2)}M`;
  else if (abs >= 1e3) out = `${(v / 1e3).toFixed(1)}K`;
  else out = v.toFixed(0);
  return `$${out}`;
}

export function fmtPct(v: number | null | undefined): string {
  if (v == null || isNaN(v as number)) return "—";
  const sign = (v as number) >= 0 ? "+" : "";
  return `${sign}${((v as number) * 100).toFixed(1)}%`;
}

export const PALETTE = [
  "#1f4e78", "#2482d7", "#7cb4e7", "#f59e0b", "#10b981",
  "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316",
  "#6366f1", "#84cc16",
];
