"use client";
/**
 * NEW FILE: frontend/src/app/dashboards/states/[stateCode]/page.tsx
 *
 * State drill-in: shown when user clicks a state on the India map.
 * Path: /dashboards/states/MH for Maharashtra, etc.
 */
import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { fmtUSD, fmtPct, PALETTE } from "@/lib/format";
import Shell from "@/components/layout/Shell";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import KpiCard from "@/components/ui/KpiCard";
import EChart from "@/components/charts/EChart";

export default function StateDetailPage() {
  const router = useRouter();
  const params = useParams<{ stateCode: string }>();
  const search = useSearchParams();
  const fy = Number(search.get("fiscal_year") || 2026);
  const stateCode = (params.stateCode || "").toUpperCase();

  const { data, isLoading, error } = useQuery({
    queryKey: ["state-detail", stateCode, fy],
    queryFn: async () =>
      (await api().get(`/dashboards/states/${stateCode}?fiscal_year=${fy}`)).data,
    enabled: !!stateCode,
  });

  return (
    <Shell>
      <div className="p-8 max-w-[1500px] mx-auto">
        <button
          onClick={() => router.push("/dashboards/states")}
          className="text-sm text-blue-600 mb-3 flex items-center gap-1"
        >
          <ArrowLeft size={14} /> Back to State Performance
        </button>

        <PageHeader
          title={data ? data.state_name : stateCode}
          subtitle={
            data
              ? `${data.region || "India"} · FY${String(fy).slice(-2)} ${
                  data.is_coastal ? "· Coastal" : ""
                }`
              : "Loading…"
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
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              {data.kpis.map((k: any) => (
                <KpiCard key={k.label} kpi={k} />
              ))}
            </div>

            {/* Trend + 5-yr history */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <Card title="Monthly trend">
                <EChart height={320} option={monthlyOption(data.monthly_trend)} />
              </Card>
              <Card title="5-year history">
                <EChart height={320} option={yearlyOption(data.yoy_history)} />
              </Card>
            </div>

            {/* Top products */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <Card title="Top export products">
                <CategoryTable items={data.top_export_products} />
              </Card>
              <Card title="Top import products">
                <CategoryTable items={data.top_import_products} />
              </Card>
            </div>

            {/* Top trade partners */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <Card title="Top export destinations">
                <CategoryTable items={data.top_export_destinations} />
              </Card>
              <Card title="Top import sources">
                <CategoryTable items={data.top_import_sources} />
              </Card>
            </div>
          </>
        )}
      </div>
    </Shell>
  );
}

function CategoryTable({ items }: { items: any[] }) {
  if (!items?.length) {
    return <div className="text-gray-400 text-sm">No data</div>;
  }
  return (
    <table className="w-full text-sm">
      <tbody>
        {items.map((item) => (
          <tr key={item.code || item.label} className="border-b border-gray-100">
            <td className="py-1.5 pr-2">{item.label}</td>
            <td className="py-1.5 pr-2 text-right whitespace-nowrap">
              {fmtUSD(item.value)}
            </td>
            <td className="py-1.5 text-right text-gray-500 w-16">
              {fmtPct(item.pct_of_total)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function monthlyOption(rows: any[]) {
  const periods = Array.from(new Set(rows.map((r) => r.period)));
  const exp = periods.map(
    (p) => rows.find((r) => r.period === p && r.direction === "EXPORT")?.value || 0
  );
  const imp = periods.map(
    (p) => rows.find((r) => r.period === p && r.direction === "IMPORT")?.value || 0
  );
  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    legend: { top: 0 },
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
    xAxis: { type: "category", data: periods },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series: [
      { name: "Exports", type: "line", smooth: true, data: exp, color: "#1f4e78" },
      { name: "Imports", type: "line", smooth: true, data: imp, color: "#dc2626" },
    ],
  };
}

function yearlyOption(rows: any[]) {
  const periods = Array.from(new Set(rows.map((r) => r.period)));
  const exp = periods.map(
    (p) => rows.find((r) => r.period === p && r.direction === "EXPORT")?.value || 0
  );
  const imp = periods.map(
    (p) => rows.find((r) => r.period === p && r.direction === "IMPORT")?.value || 0
  );
  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    legend: { top: 0 },
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
    xAxis: { type: "category", data: periods },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series: [
      { name: "Exports", type: "bar", data: exp, color: "#1f4e78" },
      { name: "Imports", type: "bar", data: imp, color: "#dc2626" },
    ],
  };
}
