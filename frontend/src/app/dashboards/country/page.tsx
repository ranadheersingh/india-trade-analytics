"use client";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { fmtUSD } from "@/lib/format";
import Shell from "@/components/layout/Shell";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import KpiCard from "@/components/ui/KpiCard";
import EChart from "@/components/charts/EChart";

export const dynamic = "force-dynamic";

export default function CountryPageWrapper() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-brand-600">Loading…</div>}>
      <CountryPage />
    </Suspense>
  );
}

function CountryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [iso, setIso] = useState<string>(searchParams.get("iso") || "USA");
  const [fy, setFy] = useState(2026);
  const [search, setSearch] = useState("");

  const { data: countries } = useQuery({
    queryKey: ["countries"],
    queryFn: async () => (await api().get("meta/countries?limit=500")).data,
  });

  const { data: availableYears = [2022, 2023, 2024, 2025, 2026] } = useQuery({
    queryKey: ["available-years"],
    queryFn: async () => (await api().get("meta/available-years")).data as number[],
    staleTime: 60_000,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["country", iso, fy],
    queryFn: async () => (await api().get(`dashboards/country/${iso}?fiscal_year=${fy}`)).data,
    enabled: !!iso,
  });

  // Update URL when iso changes
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("iso", iso);
    window.history.replaceState({}, "", url.toString());
  }, [iso]);

  const filteredCountries = (countries || []).filter((c: any) =>
    !search || c.country_name.toLowerCase().includes(search.toLowerCase()) ||
    c.iso_alpha_3.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Shell>
      <div className="p-8 max-w-[1500px] mx-auto">
        <PageHeader
          title="Country Analysis"
          subtitle="Bilateral trade with a specific partner"
          right={
            <div className="flex gap-2 items-center">
              <select
                value={fy}
                onChange={e => setFy(Number(e.target.value))}
                className="bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                {availableYears.map(y => <option key={y} value={y}>FY{String(y).slice(-2)}</option>)}
              </select>
            </div>
          }
        />

        {/* Country picker */}
        <Card className="mb-6">
          <div className="flex flex-col gap-3">
            <input
              type="text"
              placeholder="Search countries…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-full max-w-md"
            />
            <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
              {filteredCountries.slice(0, 60).map((c: any) => (
                <button
                  key={c.iso_alpha_3}
                  onClick={() => setIso(c.iso_alpha_3)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition ${
                    iso === c.iso_alpha_3
                      ? "bg-brand-600 text-white border-brand-600"
                      : "bg-white text-gray-700 border-gray-200 hover:border-brand-400"
                  }`}
                >
                  {c.iso_alpha_3} {c.country_name}
                </button>
              ))}
            </div>
          </div>
        </Card>

        {isLoading && <div className="text-gray-500">Loading…</div>}
        {error && <div className="text-red-600">Failed: {String((error as any).message)}</div>}

        {data && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {data.kpis.map((k: any) => (
                <KpiCard key={k.label} label={k.label} value={k.value} yoy_pct={k.yoy_pct} />
              ))}
            </div>

            <Card title={`Monthly Trade with ${data.country.country_name} (last 5 FYs)`} className="mb-6">
              <EChart height={360} option={buildAreaOption(data.monthly_trend)} />
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card title={`Top Exports to ${data.country.country_name}`}>
                {data.top_export_products.length === 0
                  ? <div className="text-sm text-gray-500">No data for this period.</div>
                  : <EChart height={420} option={buildHorizBarOption(data.top_export_products, "#1f4e78")} />
                }
              </Card>
              <Card title={`Top Imports from ${data.country.country_name}`}>
                {data.top_import_products.length === 0
                  ? <div className="text-sm text-gray-500">No data for this period.</div>
                  : <EChart height={420} option={buildHorizBarOption(data.top_import_products, "#f59e0b")} />
                }
              </Card>
            </div>
          </>
        )}
      </div>
    </Shell>
  );
}

function buildAreaOption(points: any[]) {
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
      { name: "Exports", type: "line", smooth: true, data: exp, color: "#1f4e78", areaStyle: { opacity: 0.2 } },
      { name: "Imports", type: "line", smooth: true, data: imp, color: "#f59e0b", areaStyle: { opacity: 0.2 } },
    ],
  };
}

function buildHorizBarOption(items: any[], color: string) {
  const sorted = [...items].sort((a, b) => a.value - b.value);
  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    grid: { left: 200, right: 30, top: 10, bottom: 30 },
    xAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    yAxis: {
      type: "category",
      data: sorted.map(i => i.label.length > 30 ? i.label.slice(0, 30) + "…" : i.label),
    },
    series: [{
      type: "bar",
      data: sorted.map(i => ({ value: i.value, code: i.code, name: i.label })),
      color,
      label: { show: true, position: "right", formatter: (p: any) => fmtUSD(p.value) },
    }],
  };
}
