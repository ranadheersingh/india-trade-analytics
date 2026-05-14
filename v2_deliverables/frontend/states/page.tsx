"use client";
/**
 * Replace contents of: frontend/src/app/dashboards/states/page.tsx
 *
 * State Performance v2:
 *  - KPI cards across the top
 *  - India choropleth map (left) + Top states bar (right)
 *  - YoY trend (export vs import)
 *  - Region split (NORTH/SOUTH/EAST/WEST/CENTRAL)
 *  - State rankings table with click-to-drill
 */
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

export default function StatesPage() {
  const router = useRouter();
  const [fy, setFy] = useState(2026);

  const { data, isLoading, error } = useQuery({
    queryKey: ["states", fy],
    queryFn: async () =>
      (await api().get(`/dashboards/states?fiscal_year=${fy}`)).data,
  });

  const goToState = (code?: string) => {
    if (!code) return;
    router.push(`/dashboards/states/${code}?fiscal_year=${fy}`);
  };

  return (
    <Shell>
      <div className="p-8 max-w-[1500px] mx-auto">
        <PageHeader
          title="State Performance"
          subtitle="Indian state-wise contribution to merchandise trade. Click a state on the map for details."
          right={
            <select
              value={fy}
              onChange={(e) => setFy(Number(e.target.value))}
              className="bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              {[2022, 2023, 2024, 2025, 2026].map((y) => (
                <option key={y} value={y}>
                  FY{String(y).slice(-2)}
                </option>
              ))}
            </select>
          }
        />

        {isLoading && <div className="text-gray-500">Loading…</div>}
        {error && (
          <div className="text-red-600">
            Failed: {String((error as any).message)}
          </div>
        )}

        {data && (
          <>
            {/* KPI cards */}
            {data.kpis && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                {data.kpis.map((k: any) => (
                  <KpiCard key={k.label} kpi={k} />
                ))}
              </div>
            )}

            {/* Map + top states bar */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
              <Card title="India exports by state" className="lg:col-span-2">
                <IndiaMap
                  states={data.top_export_states || data.states}
                  height={520}
                  onStateClick={(state) => goToState(state?.code)}
                />
              </Card>
              <Card title="Top 10 states (exports)">
                <EChart
                  height={520}
                  option={buildBarOption(
                    (data.top_export_states || data.states).slice(0, 10)
                  )}
                  onEvents={{
                    click: (p: any) => {
                      const code = (data.top_export_states || data.states).find(
                        (s: any) => s.label === p.name
                      )?.code;
                      goToState(code);
                    },
                  }}
                />
              </Card>
            </div>

            {/* YoY trend + region split */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              {data.yoy_trend?.length > 0 && (
                <Card title="State trade trend (last 5 FYs)">
                  <EChart height={320} option={buildYoyOption(data.yoy_trend)} />
                </Card>
              )}
              {data.region_split?.length > 0 && (
                <Card title="Exports by Indian region (zone)">
                  <EChart
                    height={320}
                    option={buildRegionOption(data.region_split)}
                  />
                </Card>
              )}
            </div>

            {/* Rankings table */}
            <Card title={`State rankings — FY${String(fy).slice(-2)}`}>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-gray-200">
                    <tr className="text-left text-gray-500 text-xs uppercase tracking-wide">
                      <th className="py-2 pr-4">#</th>
                      <th className="py-2 pr-4">State</th>
                      <th className="py-2 pr-4 text-right">Export Value</th>
                      <th className="py-2 pr-4 text-right">Share</th>
                      <th className="py-2 pr-4"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.top_export_states || data.states).map(
                      (s: any, i: number) => (
                        <tr
                          key={s.code || s.label}
                          className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                          onClick={() => goToState(s.code)}
                        >
                          <td className="py-2 pr-4 text-gray-500">{i + 1}</td>
                          <td className="py-2 pr-4 font-medium">{s.label}</td>
                          <td className="py-2 pr-4 text-right">
                            {fmtUSD(s.value)}
                          </td>
                          <td className="py-2 pr-4 text-right text-gray-500">
                            {fmtPct(s.pct_of_total)}
                          </td>
                          <td className="py-2 pr-4 text-right text-blue-600 text-xs">
                            View →
                          </td>
                        </tr>
                      )
                    )}
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
  const sorted = [...top].sort((a, b) => a.value - b.value);
  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    grid: { left: 140, right: 30, top: 10, bottom: 30 },
    xAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    yAxis: { type: "category", data: sorted.map((s) => s.label) },
    series: [
      {
        type: "bar",
        data: sorted.map((s) => s.value),
        color: "#1f4e78",
        label: {
          show: true,
          position: "right",
          formatter: (p: any) => fmtUSD(p.value),
        },
      },
    ],
  };
}

function buildYoyOption(trend: any[]) {
  const periods = Array.from(new Set(trend.map((t) => t.period)));
  const exportSeries = periods.map(
    (p) =>
      trend.find((t) => t.period === p && t.direction === "EXPORT")?.value || 0
  );
  const importSeries = periods.map(
    (p) =>
      trend.find((t) => t.period === p && t.direction === "IMPORT")?.value || 0
  );
  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    legend: { top: 0 },
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
    xAxis: { type: "category", data: periods },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series: [
      {
        name: "Exports",
        type: "bar",
        data: exportSeries,
        color: "#1f4e78",
      },
      {
        name: "Imports",
        type: "bar",
        data: importSeries,
        color: "#dc2626",
      },
    ],
  };
}

function buildRegionOption(regions: any[]) {
  return {
    tooltip: {
      trigger: "item",
      formatter: (p: any) =>
        `${p.name}<br/>${fmtUSD(p.value)} (${(p.percent || 0).toFixed(1)}%)`,
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        avoidLabelOverlap: true,
        label: {
          formatter: (p: any) => `${p.name}\n${(p.percent || 0).toFixed(1)}%`,
        },
        data: regions.map((r, i) => ({
          name: r.label,
          value: r.value,
          itemStyle: { color: PALETTE[i % PALETTE.length] },
        })),
      },
    ],
  };
}
