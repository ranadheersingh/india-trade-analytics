"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { fmtUSD, fmtPct } from "@/lib/format";
import Shell from "@/components/layout/Shell";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import KpiCard from "@/components/ui/KpiCard";
import EChart from "@/components/charts/EChart";

function normalizeDetailKpis(kpis: any[] = [], data: any) {
  const hasImportSplit =
    (data?.top_import_products || []).length > 0 ||
    (data?.top_import_sources || []).length > 0 ||
    (data?.monthly_trend || []).some((r: any) => r.direction === "IMPORT");

  return kpis.map((k: any) => {
    const label = String(k.label || "").toLowerCase();

    if (label.includes("import") && Number(k.value || 0) === 0 && !hasImportSplit) {
      return {
        ...k,
        label: "Imports",
        value: 0,
        unit: "NA",
        yoy_change: null,
        yoy_pct: null,
      };
    }

    if (label.includes("export") && !hasImportSplit) {
      return {
        ...k,
        label: "Exports / state trade",
      };
    }

    return k;
  });
}

export default function StateDetailPage() {
  const router = useRouter();
  const params = useParams<{ stateCode: string }>();
  const search = useSearchParams();

  const requestedFy = Number(search.get("fiscal_year") || 2025);
  const stateCode = (params.stateCode || "").toUpperCase();

  const { data, isLoading, error } = useQuery({
    queryKey: ["state-detail", stateCode, requestedFy],
    queryFn: async () =>
      (await api().get(`dashboards/states/${stateCode}?fiscal_year=${requestedFy}`)).data,
    enabled: !!stateCode,
  });

  const displayedFy = data?.fiscal_year ?? requestedFy;
  const fallbackApplied = data && data.fiscal_year !== requestedFy;
  const kpis = normalizeDetailKpis(data?.kpis || [], data);
  const hasImportSplit =
    (data?.top_import_products || []).length > 0 ||
    (data?.top_import_sources || []).length > 0 ||
    (data?.monthly_trend || []).some((r: any) => r.direction === "IMPORT");

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
              ? `${data.region || "India"} · FY${String(displayedFy).slice(-2)} ${
                  data.is_coastal ? "· Coastal" : ""
                }`
              : "Loading…"
          }
        />

        {fallbackApplied && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
            FY{String(requestedFy).slice(-2)} state data was not available, so the latest available
            FY{String(displayedFy).slice(-2)} data is shown.
          </div>
        )}

        {data && !hasImportSplit && (
          <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-800">
            Import split is not available in the current state-level source. Export/trade values are shown where available.
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
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              {kpis.map((k: any) => (
                <KpiCard key={k.label} kpi={k} />
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <Card title="Monthly trend">
                <EChart height={340} option={monthlyOption(data.monthly_trend || [], hasImportSplit)} />
              </Card>
              <Card title="5-year history">
                <EChart height={340} option={yearlyOption(data.yoy_history || [], hasImportSplit)} />
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <Card title={hasImportSplit ? "Top export products" : "Top trade products"}>
                <CategoryTable items={data.top_export_products || []} />
              </Card>
              <Card title="Top import products">
                {data.top_import_products?.length ? (
                  <CategoryTable items={data.top_import_products} />
                ) : (
                  <NoData message="Import product split is not available for this state/year." />
                )}
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <Card title={hasImportSplit ? "Top export destinations" : "Top trade destinations"}>
                <CategoryTable items={data.top_export_destinations || []} />
              </Card>
              <Card title="Top import sources">
                {data.top_import_sources?.length ? (
                  <CategoryTable items={data.top_import_sources} />
                ) : (
                  <NoData message="Import source split is not available for this state/year." />
                )}
              </Card>
            </div>
          </>
        )}
      </div>
    </Shell>
  );
}

function NoData({ message }: { message: string }) {
  return <div className="text-gray-400 text-sm">{message}</div>;
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

function monthlyOption(rows: any[], hasImportSplit: boolean) {
  const safeRows = rows || [];
  const periods = Array.from(new Set(safeRows.map((r) => r.period)));

  const hasExport = safeRows.some((r) => r.direction === "EXPORT");
  const hasImport = safeRows.some((r) => r.direction === "IMPORT");
  const hasTotal = safeRows.some((r) => r.direction === "TOTAL");

  const series: any[] = [];

  if (hasExport) {
    series.push({
      name: hasImportSplit ? "Exports" : "Exports / state trade",
      type: "line",
      smooth: true,
      symbolSize: 6,
      data: periods.map(
        (p) => safeRows.find((r) => r.period === p && r.direction === "EXPORT")?.value || 0
      ),
      color: "#1f4e78",
    });
  }

  if (hasImport) {
    series.push({
      name: "Imports",
      type: "line",
      smooth: true,
      symbolSize: 6,
      data: periods.map(
        (p) => safeRows.find((r) => r.period === p && r.direction === "IMPORT")?.value || 0
      ),
      color: "#dc2626",
    });
  }

  if (!hasExport && !hasImport && hasTotal) {
    series.push({
      name: "Total trade",
      type: "line",
      smooth: true,
      symbolSize: 6,
      data: periods.map(
        (p) => safeRows.find((r) => r.period === p && r.direction === "TOTAL")?.value || 0
      ),
      color: "#1f4e78",
    });
  }

  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    legend: { top: 0 },
    grid: { left: 82, right: 24, top: 45, bottom: 40 },
    xAxis: { type: "category", data: periods },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series,
  };
}

function yearlyOption(rows: any[], hasImportSplit: boolean) {
  const safeRows = rows || [];
  const periods = Array.from(new Set(safeRows.map((r) => r.period)));

  const hasExport = safeRows.some((r) => r.direction === "EXPORT");
  const hasImport = safeRows.some((r) => r.direction === "IMPORT");
  const hasTotal = safeRows.some((r) => r.direction === "TOTAL");

  const series: any[] = [];

  if (hasExport) {
    series.push({
      name: hasImportSplit ? "Exports" : "Exports / state trade",
      type: "bar",
      data: periods.map(
        (p) => safeRows.find((r) => r.period === p && r.direction === "EXPORT")?.value || 0
      ),
      color: "#1f4e78",
    });
  }

  if (hasImport) {
    series.push({
      name: "Imports",
      type: "bar",
      data: periods.map(
        (p) => safeRows.find((r) => r.period === p && r.direction === "IMPORT")?.value || 0
      ),
      color: "#dc2626",
    });
  }

  if (!hasExport && !hasImport && hasTotal) {
    series.push({
      name: "Total trade",
      type: "bar",
      data: periods.map(
        (p) => safeRows.find((r) => r.period === p && r.direction === "TOTAL")?.value || 0
      ),
      color: "#1f4e78",
    });
  }

  return {
    tooltip: { trigger: "axis", valueFormatter: (v: number) => fmtUSD(v) },
    legend: { top: 0 },
    grid: { left: 82, right: 24, top: 45, bottom: 40 },
    xAxis: { type: "category", data: periods },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series,
  };
}
