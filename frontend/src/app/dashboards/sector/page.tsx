"use client";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { fmtUSD } from "@/lib/format";
import Shell from "@/components/layout/Shell";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import KpiCard from "@/components/ui/KpiCard";
import EChart from "@/components/charts/EChart";

export const dynamic = "force-dynamic";

export default function SectorPageWrapper() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-brand-600">Loading…</div>}>
      <SectorPage />
    </Suspense>
  );
}

function SectorPage() {
  const searchParams = useSearchParams();
  const [hs, setHs] = useState<string>(searchParams.get("hs") || "27");
  const [fy, setFy] = useState(2026);
  const [search, setSearch] = useState("");

  const { data: hsList } = useQuery({
    queryKey: ["hs"],
    queryFn: async () => (await api().get("/meta/hs?level=2&limit=200")).data,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["sector", hs, fy],
    queryFn: async () => (await api().get(`/dashboards/sector/${hs}?fiscal_year=${fy}`)).data,
    enabled: !!hs,
  });

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("hs", hs);
    window.history.replaceState({}, "", url.toString());
  }, [hs]);

  const filtered = (hsList || []).filter((h: any) =>
    !search || h.description.toLowerCase().includes(search.toLowerCase()) || h.hs_code.includes(search)
  );

  return (
    <Shell>
      <div className="p-8 max-w-[1500px] mx-auto">
        <PageHeader
          title="Sector Deep-dive"
          subtitle="HS-2 product chapter analysis"
          right={
            <select
              value={fy}
              onChange={e => setFy(Number(e.target.value))}
              className="bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              {[2022, 2023, 2024, 2025, 2026].map(y => <option key={y} value={y}>FY{String(y).slice(-2)}</option>)}
            </select>
          }
        />

        <Card className="mb-6">
          <div className="flex flex-col gap-3">
            <input
              type="text"
              placeholder="Search HS chapters…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-full max-w-md"
            />
            <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
              {filtered.slice(0, 60).map((h: any) => (
                <button
                  key={h.hs_code}
                  onClick={() => setHs(h.hs_code)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition ${
                    hs === h.hs_code
                      ? "bg-brand-600 text-white border-brand-600"
                      : "bg-white text-gray-700 border-gray-200 hover:border-brand-400"
                  }`}
                  title={h.description}
                >
                  HS-{h.hs_code} {h.description.slice(0, 30)}
                </button>
              ))}
            </div>
          </div>
        </Card>

        {isLoading && <div className="text-gray-500">Loading…</div>}
        {error && <div className="text-red-600">Failed: {String((error as any).message)}</div>}

        {data && (
          <>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm mb-6">
              <div className="text-xs text-gray-500 uppercase">HS-{data.hs_2}</div>
              <div className="text-lg font-semibold">{data.hs_2_name}</div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {data.kpis.map((k: any) => (
                <KpiCard key={k.label} label={k.label} value={k.value} yoy_pct={k.yoy_pct} />
              ))}
            </div>

            <Card title="Monthly trend (last 5 FYs)" className="mb-6">
              <EChart height={360} option={buildTrendOption(data.monthly_trend)} />
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card title="Top export destinations">
                {data.top_export_destinations.length === 0
                  ? <div className="text-sm text-gray-500">No data.</div>
                  : <EChart height={420} option={buildHorizBarOption(data.top_export_destinations, "#1f4e78")} />
                }
              </Card>
              <Card title="Top import sources">
                {data.top_import_sources.length === 0
                  ? <div className="text-sm text-gray-500">No data.</div>
                  : <EChart height={420} option={buildHorizBarOption(data.top_import_sources, "#f59e0b")} />
                }
              </Card>
            </div>
          </>
        )}
      </div>
    </Shell>
  );
}

function buildTrendOption(points: any[]) {
  const months = Array.from(new Set(points.map(p => p.period))).sort();
  const exp = months.map(m => points.find(p => p.period === m && p.direction === "EXPORT")?.value || 0);
  const imp = months.map(m => points.find(p => p.period === m && p.direction === "IMPORT")?.value || 0);
  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    legend: { data: ["Exports", "Imports"], bottom: 0 },
    grid: { left: 60, right: 20, top: 20, bottom: 50 },
    xAxis: { type: "category", data: months, axisLabel: { rotate: 30, interval: Math.max(1, Math.floor(months.length / 12)) } },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series: [
      { name: "Exports", type: "line", smooth: true, data: exp, color: "#1f4e78" },
      { name: "Imports", type: "line", smooth: true, data: imp, color: "#f59e0b" },
    ],
  };
}

function buildHorizBarOption(items: any[], color: string) {
  const sorted = [...items].sort((a, b) => a.value - b.value);
  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    grid: { left: 160, right: 30, top: 10, bottom: 30 },
    xAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    yAxis: { type: "category", data: sorted.map(i => i.label) },
    series: [{
      type: "bar",
      data: sorted.map(i => i.value),
      color,
      label: { show: true, position: "right", formatter: (p: any) => fmtUSD(p.value) },
    }],
  };
}
