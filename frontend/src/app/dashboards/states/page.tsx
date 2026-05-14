"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { fmtUSD, fmtPct, PALETTE } from "@/lib/format";
import Shell from "@/components/layout/Shell";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import KpiCard from "@/components/ui/KpiCard";
import EChart from "@/components/charts/EChart";
import IndiaMap from "@/components/charts/IndiaMap";

function normalizeStateKpis(kpis: any[] = [], data: any) {
  const hasImportRanking = (data?.top_import_states || []).length > 0;
  const availableDataType = String(
    data?.kpis?.find((k: any) =>
      String(k.label || "").toLowerCase().includes("available data type")
    )?.unit || ""
  ).toUpperCase();

  return kpis.map((k: any) => {
    const label = String(k.label || "").toLowerCase();

    if (label.includes("import") && Number(k.value || 0) === 0 && !hasImportRanking) {
      return {
        ...k,
        label: "State imports",
        value: 0,
        unit: "NA",
        yoy_change: null,
        yoy_pct: null,
        helper_text:
          availableDataType === "TOTAL"
            ? "Import split is not available for selected FY"
            : "Not available in current state-level source",
      };
    }

    if (label.includes("export") && !hasImportRanking) {
      return {
        ...k,
        label: availableDataType === "TOTAL" ? "State trade value" : "State exports",
      };
    }

    return k;
  });
}

export default function StatesPage() {
  const router = useRouter();

  // FY25 has TRADESTAT export/import split. FY26 currently has DGCIS TOTAL only.
  const [fy, setFy] = useState(2025);

  const { data, isLoading, error } = useQuery({
    queryKey: ["states", fy],
    queryFn: async () =>
      (await api().get(`/dashboards/states?fiscal_year=${fy}`)).data,
  });

  const displayedFy = data?.fiscal_year ?? fy;
  const fallbackApplied = data && data.fiscal_year !== fy;
  const rankingStates =
    data?.top_export_states?.length > 0 ? data.top_export_states : data?.states || [];
  const kpis = normalizeStateKpis(data?.kpis || [], data);

  const goToState = (code?: string) => {
    if (!code) return;
    router.push(`/dashboards/states/${code}?fiscal_year=${displayedFy}`);
  };

  return (
    <Shell>
      <div className="p-8 max-w-[1600px] mx-auto">
        <PageHeader
          title="State Performance"
          subtitle="Indian state-wise trade contribution. Click a state on the map for details."
          right={
            <select
              value={fy}
              onChange={(e) => setFy(Number(e.target.value))}
              className="bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              {[2021, 2022, 2023, 2024, 2025, 2026].map((y) => (
                <option key={y} value={y}>
                  FY{String(y).slice(-2)}
                </option>
              ))}
            </select>
          }
        />

        {fallbackApplied && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
            FY{String(fy).slice(-2)} state data was not available, so the latest available
            FY{String(displayedFy).slice(-2)} data is shown.
          </div>
        )}

        {fy === 2026 && (
          <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-800">
            FY26 currently uses DGCIS TOTAL state data. For export/import split,
            select FY25 or earlier.
          </div>
        )}

        {isLoading && <div className="text-gray-500">Loading…</div>}
        {error && (
          <div className="text-red-600">
            Failed: {String((error as any).message)}
          </div>
        )}

        {data && (
          <>
            {kpis.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                {kpis.map((k: any) => (
                  <KpiCard key={k.label} kpi={k} />
                ))}
              </div>
            )}

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-6">
              <Card title="India trade by state" className="xl:col-span-2 min-h-[760px]">
                <div className="w-full h-[700px]">
                  <IndiaMap
                    states={rankingStates}
                    height={700}
                    onStateClick={(state) => goToState(state?.code)}
                  />
                </div>
              </Card>

              <Card title="Top 10 states" className="min-h-[760px]">
                <EChart
                  height={700}
                  option={buildBarOption(rankingStates.slice(0, 10))}
                  onEvents={{
                    click: (p: any) => {
                      const code = rankingStates.find((s: any) => s.label === p.name)?.code;
                      goToState(code);
                    },
                  }}
                />
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              {data.yoy_trend?.length > 0 && (
                <Card title="State trade trend (last 5 FYs)">
                  <EChart height={360} option={buildYoyOption(data.yoy_trend)} />
                </Card>
              )}

              {data.region_split?.length > 0 && (
                <Card title="Trade by Indian region (zone)">
                  <EChart height={360} option={buildRegionOption(data.region_split)} />
                </Card>
              )}
            </div>

            <Card title={`State rankings — FY${String(displayedFy).slice(-2)}`}>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-gray-200">
                    <tr className="text-left text-gray-500 text-xs uppercase tracking-wide">
                      <th className="py-2 pr-4">#</th>
                      <th className="py-2 pr-4">State</th>
                      <th className="py-2 pr-4 text-right">Value</th>
                      <th className="py-2 pr-4 text-right">Share</th>
                      <th className="py-2 pr-4"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rankingStates.map((s: any, i: number) => (
                      <tr
                        key={s.code || s.label}
                        className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                        onClick={() => goToState(s.code)}
                      >
                        <td className="py-2 pr-4 text-gray-500">{i + 1}</td>
                        <td className="py-2 pr-4 font-medium">{s.label}</td>
                        <td className="py-2 pr-4 text-right">{fmtUSD(s.value)}</td>
                        <td className="py-2 pr-4 text-right text-gray-500">
                          {fmtPct(s.pct_of_total)}
                        </td>
                        <td className="py-2 pr-4 text-right text-blue-600 text-xs">
                          View →
                        </td>
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

function buildBarOption(top: any[]) {
  const sorted = [...(top || [])].sort((a, b) => a.value - b.value);

  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    grid: { left: 150, right: 90, top: 30, bottom: 55, containLabel: true },
    xAxis: {
      type: "value",
      axisLabel: { formatter: (v: number) => fmtUSD(v), fontSize: 10 },
      splitLine: { lineStyle: { color: "#eef2f7" } },
    },
    yAxis: {
      type: "category",
      data: sorted.map((s) => s.label),
      axisLabel: { fontSize: 11, width: 135, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        data: sorted.map((s) => s.value),
        color: "#1f4e78",
        barWidth: 20,
        label: {
          show: true,
          position: "right",
          formatter: (p: any) => fmtUSD(p.value),
          fontSize: 10,
        },
      },
    ],
  };
}

function buildYoyOption(trend: any[]) {
  const safeTrend = trend || [];
  const periods = Array.from(new Set(safeTrend.map((t) => t.period))).filter((p) => {
    const exportValue = safeTrend.find((t) => t.period === p && t.direction === "EXPORT")?.value || 0;
    const importValue = safeTrend.find((t) => t.period === p && t.direction === "IMPORT")?.value || 0;
    const totalValue = safeTrend.find((t) => t.period === p && t.direction === "TOTAL")?.value || 0;
    return exportValue > 0 || importValue > 0 || totalValue > 0;
  });

  const hasExport = safeTrend.some((t) => t.direction === "EXPORT");
  const hasImport = safeTrend.some((t) => t.direction === "IMPORT");
  const hasTotal = safeTrend.some((t) => t.direction === "TOTAL");

  const series: any[] = [];

  if (hasExport) {
    series.push({
      name: "Exports / State trade",
      type: "bar",
      data: periods.map((p) => safeTrend.find((t) => t.period === p && t.direction === "EXPORT")?.value || 0),
      color: "#1f4e78",
    });
  }

  if (hasImport) {
    series.push({
      name: "Imports",
      type: "bar",
      data: periods.map((p) => safeTrend.find((t) => t.period === p && t.direction === "IMPORT")?.value || 0),
      color: "#dc2626",
    });
  }

  if (!hasExport && !hasImport && hasTotal) {
    series.push({
      name: "Total trade",
      type: "bar",
      data: periods.map((p) => safeTrend.find((t) => t.period === p && t.direction === "TOTAL")?.value || 0),
      color: "#1f4e78",
    });
  }

  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    legend: { top: 0 },
    grid: { left: 85, right: 28, top: 48, bottom: 45, containLabel: true },
    xAxis: { type: "category", data: periods },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series,
  };
}

function buildRegionOption(regions: any[]) {
  return {
    tooltip: {
      trigger: "item",
      formatter: (p: any) =>
        `${p.name}<br/>${fmtUSD(p.value)} (${(p.percent || 0).toFixed(1)}%)`,
    },
    legend: { bottom: 0, type: "scroll" },
    series: [
      {
        type: "pie",
        radius: ["42%", "68%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: true,
        label: {
          formatter: (p: any) => `${p.name}\n${(p.percent || 0).toFixed(1)}%`,
          fontSize: 10,
        },
        data: (regions || []).map((r, i) => ({
          name: r.label,
          value: r.value,
          itemStyle: { color: PALETTE[i % PALETTE.length] },
        })),
      },
    ],
  };
}
