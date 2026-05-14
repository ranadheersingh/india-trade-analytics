"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { fmtUSD, PALETTE } from "@/lib/format";
import Shell from "@/components/layout/Shell";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import KpiCard from "@/components/ui/KpiCard";
import EChart from "@/components/charts/EChart";

function FYSelect({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const years = [2022, 2023, 2024, 2025, 2026];
  return (
    <select
      value={value}
      onChange={e => onChange(Number(e.target.value))}
      className="bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm"
    >
      {years.map(y => <option key={y} value={y}>FY{String(y).slice(-2)}</option>)}
    </select>
  );
}

export default function ExecutivePage() {
  const router = useRouter();
  const [fy, setFy] = useState(2026);
  const { data, isLoading, error } = useQuery({
    queryKey: ["exec", fy],
    queryFn: async () => (await api().get(`/dashboards/executive?fiscal_year=${fy}`)).data,
  });

  return (
    <Shell>
      <div className="p-8 max-w-[1500px] mx-auto">
        <PageHeader
          title="Executive Overview"
          subtitle="High-level summary of India's merchandise trade"
          right={<FYSelect value={fy} onChange={setFy} />}
        />

        {isLoading && <div className="text-gray-500">Loading…</div>}
        {error && <div className="text-red-600">Failed to load: {String((error as any).message)}</div>}

        {data && (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {data.kpis.map((k: any) => (
                <KpiCard key={k.label} label={k.label} value={k.value} yoy_pct={k.yoy_pct}/>
              ))}
            </div>

            {/* Monthly trend */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
              <Card title="Monthly Trade Trend (Exports vs Imports)" className="lg:col-span-2">
                <EChart
                  height={340}
                  option={buildMonthlyTrendOption(data.monthly_trend)}
                />
              </Card>
              <Card title="Region Split (Exports)">
                <EChart
                  height={340}
                  option={buildRegionDonutOption(data.region_split_export)}
                />
              </Card>
            </div>

            {/* Partners + Categories */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <Card title="Top 10 Export Partners">
                <EChart
                  height={420}
                  option={buildHorizBarOption(data.top_partners_export, "#1f4e78")}
                  onEvents={{
                    click: (p: any) => router.push(`/dashboards/country?iso=${p.data.code}`)
                  }}
                />
              </Card>
              <Card title="Top 10 Import Partners">
                <EChart
                  height={420}
                  option={buildHorizBarOption(data.top_partners_import, "#f59e0b")}
                  onEvents={{
                    click: (p: any) => router.push(`/dashboards/country?iso=${p.data.code}`)
                  }}
                />
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <Card title="Top 10 Export Categories (HS-2)">
                <EChart
                  height={420}
                  option={buildHorizBarOption(data.top_categories_export, "#10b981")}
                  onEvents={{
                    click: (p: any) => router.push(`/dashboards/sector?hs=${p.data.code}`)
                  }}
                />
              </Card>
              <Card title="Top 10 Import Categories (HS-2)">
                <EChart
                  height={420}
                  option={buildHorizBarOption(data.top_categories_import, "#8b5cf6")}
                  onEvents={{
                    click: (p: any) => router.push(`/dashboards/sector?hs=${p.data.code}`)
                  }}
                />
              </Card>
            </div>
          </>
        )}
      </div>
    </Shell>
  );
}

// ---- Chart options ----

function buildMonthlyTrendOption(points: any[]) {
  const months = Array.from(new Set(points.map(p => p.period))).sort();
  const exp = months.map(m => points.find(p => p.period === m && p.direction === "EXPORT")?.value || 0);
  const imp = months.map(m => points.find(p => p.period === m && p.direction === "IMPORT")?.value || 0);
  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    legend: { data: ["Exports", "Imports"], bottom: 0 },
    grid: { left: 60, right: 20, top: 20, bottom: 50 },
    xAxis: { type: "category", data: months, axisLabel: { rotate: 30 } },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series: [
      { name: "Exports", type: "line", smooth: true, data: exp, color: "#1f4e78", lineStyle: { width: 3 } },
      { name: "Imports", type: "line", smooth: true, data: imp, color: "#f59e0b", lineStyle: { width: 3 } },
    ],
  };
}

function buildHorizBarOption(items: any[], color: string) {
  const sorted = [...items].sort((a, b) => a.value - b.value);
  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    grid: { left: 180, right: 30, top: 10, bottom: 30 },
    xAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    yAxis: {
      type: "category",
      data: sorted.map(i => i.label.length > 28 ? i.label.slice(0, 28) + "…" : i.label),
    },
    series: [{
      type: "bar",
      data: sorted.map(i => ({ value: i.value, code: i.code, name: i.label })),
      color,
      label: { show: true, position: "right", formatter: (p: any) => fmtUSD(p.value) },
      cursor: "pointer",
    }],
  };
}

function buildRegionDonutOption(items: any[]) {
  return {
    tooltip: { trigger: "item", valueFormatter: (v: number) => fmtUSD(v) },
    legend: { bottom: 0, type: "scroll" },
    series: [{
      type: "pie",
      radius: ["40%", "70%"],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
      data: items.map((i, idx) => ({ name: i.label, value: i.value, itemStyle: { color: PALETTE[idx % PALETTE.length] } })),
      label: { formatter: "{b}: {d}%" },
    }],
  };
}
