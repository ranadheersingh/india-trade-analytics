"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { fmtUSD, fmtPct } from "@/lib/format";

type Kpi = {
  label: string;
  value: number;
  unit?: string;
  yoy_change?: number | null;
  yoy_pct?: number | null;
};

type KpiCardProps = {
  kpi?: Kpi;
  label?: string;
  value?: number;
  unit?: string;
  yoy_change?: number | null;
  yoy_pct?: number | null;
};

function formatKpiValue(value: number, unit?: string) {
  const safeValue = Number(value || 0);
  const u = (unit || "USD").toUpperCase();

  if (u === "NA" || u === "N/A") return "N/A";
  if (u === "USD") return fmtUSD(safeValue);
  if (u === "FY") return `FY${String(Math.round(safeValue)).slice(-2)}`;
  if (u === "TOTAL") return "TOTAL";
  if (u === "STATES" || unit === "states") return `${Math.round(safeValue)} states`;
  if (u === "%" || u === "PCT") return fmtPct(safeValue);

  return `${safeValue.toLocaleString()} ${unit || ""}`.trim();
}

export default function KpiCard(props: KpiCardProps) {
  const kpi = props.kpi || {
    label: props.label || "",
    value: props.value || 0,
    unit: props.unit,
    yoy_change: props.yoy_change,
    yoy_pct: props.yoy_pct,
  };

  const unit = (kpi.unit || "USD").toUpperCase();
  const isNA = unit === "NA" || unit === "N/A";
  const positive = !isNA && (kpi.yoy_pct ?? 0) > 0;
  const negative = !isNA && (kpi.yoy_pct ?? 0) < 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow transition">
      <div className="text-xs text-gray-500 uppercase tracking-wide">
        {kpi.label}
      </div>

      <div className={`text-2xl font-semibold mt-2 ${isNA ? "text-gray-400" : "text-gray-900"}`}>
        {formatKpiValue(kpi.value, kpi.unit)}
      </div>

      {isNA && (
        <div className="mt-2 text-sm text-gray-400">
          Not available in state-level source
        </div>
      )}

      {!isNA && kpi.yoy_pct != null && (
        <div
          className={`mt-2 text-sm flex items-center gap-1 ${
            positive ? "text-emerald-600" : negative ? "text-red-600" : "text-gray-500"
          }`}
        >
          {positive ? (
            <TrendingUp size={14} />
          ) : negative ? (
            <TrendingDown size={14} />
          ) : (
            <Minus size={14} />
          )}
          {fmtPct(kpi.yoy_pct)} YoY
        </div>
      )}
    </div>
  );
}
