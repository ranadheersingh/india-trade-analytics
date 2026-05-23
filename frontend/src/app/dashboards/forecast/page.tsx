"use client";
import { useQuery } from "@tanstack/react-query";
import { useState, Suspense } from "react";
import { api } from "@/lib/api";
import { fmtUSD, PALETTE } from "@/lib/format";
import Shell from "@/components/layout/Shell";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import EChart from "@/components/charts/EChart";

type ForecastPoint = { period: string; value: number; lower?: number; upper?: number; type: string };

function buildChartOption(historical: ForecastPoint[], forecast: ForecastPoint[]) {
  const allPeriods = [...historical.map(p => p.period), ...forecast.map(p => p.period)];
  const histValues = historical.map(p => p.value);
  const forecastValues = forecast.map(p => p.value);
  const upperBand = forecast.map(p => p.upper ?? p.value);
  const lowerBand = forecast.map(p => p.lower ?? p.value);

  // Confidence band as stack: lower + (upper-lower) shaded area
  const bandBase = forecast.map(p => p.lower ?? p.value);
  const bandTop  = forecast.map((p, i) => (p.upper ?? p.value) - (p.lower ?? p.value));

  return {
    tooltip: {
      trigger: "axis",
      valueFormatter: (v: number) => (v == null ? "" : fmtUSD(v)),
    },
    legend: { data: ["Historical", "Forecast"], bottom: 0 },
    grid: { left: 70, right: 20, top: 20, bottom: 50 },
    xAxis: {
      type: "category",
      data: allPeriods,
      axisLabel: { rotate: 35, fontSize: 11 },
      // Mark the split
      markLine: {
        data: [{ xAxis: historical.length - 1, lineStyle: { type: "dashed", color: "#94a3b8" } }],
      },
    },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series: [
      {
        name: "Historical",
        type: "line",
        smooth: true,
        data: [...histValues, ...Array(forecastValues.length).fill(null)],
        color: "#1f4e78",
        lineStyle: { width: 2 },
        symbol: "none",
      },
      {
        name: "Forecast",
        type: "line",
        smooth: true,
        data: [...Array(histValues.length - 1).fill(null), histValues[histValues.length - 1], ...forecastValues],
        color: "#f59e0b",
        lineStyle: { width: 2, type: "dashed" },
        symbol: "none",
      },
      // Confidence band — invisible base
      {
        name: "CI Base",
        type: "line",
        data: [...Array(histValues.length).fill(null), ...bandBase],
        lineStyle: { opacity: 0 },
        stack: "ci",
        symbol: "none",
        legend: { show: false },
        tooltip: { show: false },
      },
      // Confidence band — filled top
      {
        name: "CI Band",
        type: "line",
        data: [...Array(histValues.length).fill(null), ...bandTop],
        lineStyle: { opacity: 0 },
        areaStyle: { color: "#f59e0b", opacity: 0.15 },
        stack: "ci",
        symbol: "none",
        legend: { show: false },
        tooltip: { show: false },
      },
    ],
  };
}

function buildTableRows(forecast: ForecastPoint[]) {
  return forecast.map(p => ({
    period: p.period,
    value: p.value,
    lower: p.lower ?? p.value,
    upper: p.upper ?? p.value,
  }));
}

export default function ForecastPage() {
  const [direction, setDirection] = useState<"EXPORT" | "IMPORT">("EXPORT");
  const [countryIso, setCountryIso] = useState("");
  const [hsCode, setHsCode] = useState("");

  const { data: countries } = useQuery({
    queryKey: ["countries"],
    queryFn: async () => (await api().get("meta/countries?limit=500")).data,
  });

  const { data: hsCodes } = useQuery({
    queryKey: ["hs2"],
    queryFn: async () => (await api().get("meta/hs?level=2&limit=200")).data,
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["forecast", direction, countryIso, hsCode],
    queryFn: async () =>
      (await api().get("analytics/forecast", {
        params: {
          direction,
          ...(countryIso && { country_iso: countryIso }),
          ...(hsCode && { hs_code: hsCode }),
        },
      })).data,
    retry: false,
  });

  const hist: ForecastPoint[] = data?.historical ?? [];
  const fcst: ForecastPoint[] = data?.forecast ?? [];

  return (
    <Shell>
      <div className="p-8 max-w-[1500px] mx-auto">
        <PageHeader
          title="Trade Forecast"
          subtitle="12-month ahead forecast using Holt-Winters seasonal smoothing"
        />

        {/* Controls */}
        <div className="flex flex-wrap gap-3 mb-6">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Direction</label>
            <select
              value={direction}
              onChange={e => setDirection(e.target.value as any)}
              className="border rounded px-3 py-1.5 text-sm"
            >
              <option value="EXPORT">Exports</option>
              <option value="IMPORT">Imports</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Partner country (optional)</label>
            <select
              value={countryIso}
              onChange={e => setCountryIso(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm min-w-[200px]"
            >
              <option value="">All countries</option>
              {(countries ?? []).map((c: any) => (
                <option key={c.iso_alpha_3} value={c.iso_alpha_3}>{c.country_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">HS chapter (optional)</label>
            <select
              value={hsCode}
              onChange={e => setHsCode(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm min-w-[240px]"
            >
              <option value="">All products</option>
              {(hsCodes ?? []).map((h: any) => (
                <option key={h.hs_code} value={h.hs_code}>
                  {h.hs_code} — {h.description?.slice(0, 45)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {isLoading && <div className="text-gray-400 text-sm py-8 text-center">Running forecast model…</div>}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 text-sm">
            {(error as any)?.response?.data?.detail ?? "Forecast failed — try different filters."}
          </div>
        )}

        {data && !isLoading && (
          <>
            {/* Summary KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">12-month forecast total</p>
                <p className="text-xl font-bold text-amber-600">{fmtUSD(data.annual_forecast_usd)}</p>
              </div>
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Last historical month</p>
                <p className="text-xl font-bold">{fmtUSD(hist[hist.length - 1]?.value)}</p>
              </div>
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">First forecast month</p>
                <p className="text-xl font-bold text-amber-500">{fmtUSD(fcst[0]?.value)}</p>
              </div>
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Confidence interval</p>
                <p className="text-xl font-bold">±{data.ci_pct}%</p>
              </div>
            </div>

            {/* Chart */}
            <Card title={`${direction === "EXPORT" ? "Export" : "Import"} forecast — next 12 months`} className="mb-6">
              <EChart height={420} option={buildChartOption(hist, fcst)} />
              <p className="text-xs text-gray-400 mt-2">
                Model: Holt-Winters additive (trend + seasonality) · {data.history_months} months of training data · shaded area = ±{data.ci_pct}% confidence band
              </p>
            </Card>

            {/* Forecast table */}
            <Card title="Month-by-month forecast">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b text-xs text-gray-500 uppercase">
                    <tr>
                      <th className="py-2 text-left">Month</th>
                      <th className="py-2 text-right">Forecast</th>
                      <th className="py-2 text-right">Lower bound</th>
                      <th className="py-2 text-right">Upper bound</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {buildTableRows(fcst).map(row => (
                      <tr key={row.period} className="hover:bg-gray-50">
                        <td className="py-2 font-mono">{row.period}</td>
                        <td className="py-2 text-right font-semibold text-amber-700">{fmtUSD(row.value)}</td>
                        <td className="py-2 text-right text-gray-500">{fmtUSD(row.lower)}</td>
                        <td className="py-2 text-right text-gray-500">{fmtUSD(row.upper)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}
      </div>
    </Shell>
  );
}
