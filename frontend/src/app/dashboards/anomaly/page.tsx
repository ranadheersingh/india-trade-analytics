"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { fmtUSD } from "@/lib/format";
import Shell from "@/components/layout/Shell";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import EChart from "@/components/charts/EChart";

type AnomalyPoint = {
  period: string;
  value: number;
  z_score: number | null;
  is_anomaly: boolean;
  anomaly_type: "spike" | "dip" | null;
};

function buildChartOption(points: AnomalyPoint[]) {
  const periods = points.map(p => p.period);
  const normalValues = points.map(p => (p.is_anomaly ? null : p.value));
  const anomalyValues = points.map(p => (p.is_anomaly ? p.value : null));

  return {
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        const p = params[0] ?? params[1];
        if (!p) return "";
        const pt = points[p.dataIndex];
        const anomalyTag = pt.is_anomaly
          ? `<br/><span style="color:${pt.anomaly_type === "spike" ? "#dc2626" : "#7c3aed"}">⚠ ${pt.anomaly_type?.toUpperCase()} (Z=${pt.z_score})</span>`
          : "";
        return `${pt.period}<br/>${fmtUSD(pt.value)}${anomalyTag}`;
      },
    },
    legend: { data: ["Normal", "Anomaly"], bottom: 0 },
    grid: { left: 70, right: 20, top: 20, bottom: 50 },
    xAxis: {
      type: "category",
      data: periods,
      axisLabel: { rotate: 35, fontSize: 10, interval: Math.max(1, Math.floor(periods.length / 16)) },
    },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtUSD(v) } },
    series: [
      {
        name: "Normal",
        type: "line",
        smooth: true,
        data: normalValues,
        color: "#1f4e78",
        lineStyle: { width: 2 },
        symbol: "circle",
        symbolSize: 4,
        connectNulls: true,
      },
      {
        name: "Anomaly",
        type: "scatter",
        data: anomalyValues,
        symbolSize: 14,
        itemStyle: {
          color: (p: any) => {
            const pt = points[p.dataIndex];
            return pt.anomaly_type === "spike" ? "#dc2626" : "#7c3aed";
          },
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: {
          show: true,
          position: "top",
          formatter: (p: any) => {
            const pt = points[p.dataIndex];
            return pt.anomaly_type === "spike" ? "▲" : "▼";
          },
          fontSize: 10,
        },
        z: 10,
      },
    ],
  };
}

export default function AnomalyPage() {
  const [direction, setDirection] = useState<"EXPORT" | "IMPORT">("EXPORT");
  const [countryIso, setCountryIso] = useState("");
  const [hsCode, setHsCode] = useState("");
  const [historyYears, setHistoryYears] = useState(5);

  const { data: countries } = useQuery({
    queryKey: ["countries"],
    queryFn: async () => (await api().get("meta/countries?limit=500")).data,
  });

  const { data: hsCodes } = useQuery({
    queryKey: ["hs2"],
    queryFn: async () => (await api().get("meta/hs?level=2&limit=200")).data,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["anomaly", direction, countryIso, hsCode, historyYears],
    queryFn: async () =>
      (await api().get("analytics/anomalies", {
        params: {
          direction,
          history_years: historyYears,
          ...(countryIso && { country_iso: countryIso }),
          ...(hsCode && { hs_code: hsCode }),
        },
      })).data,
    retry: false,
  });

  const points: AnomalyPoint[] = data?.points ?? [];
  const anomalies: AnomalyPoint[] = data?.anomalies ?? [];

  return (
    <Shell>
      <div className="p-8 max-w-[1500px] mx-auto">
        <PageHeader
          title="Anomaly Detection"
          subtitle="Statistical outlier detection using rolling Z-score and IQR methods"
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
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">History window</label>
            <select
              value={historyYears}
              onChange={e => setHistoryYears(Number(e.target.value))}
              className="border rounded px-3 py-1.5 text-sm"
            >
              {[2, 3, 5, 7, 10].map(y => (
                <option key={y} value={y}>{y} years</option>
              ))}
            </select>
          </div>
        </div>

        {isLoading && <div className="text-gray-400 text-sm py-8 text-center">Scanning for anomalies…</div>}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 text-sm">
            {(error as any)?.response?.data?.detail ?? "Detection failed — try different filters."}
          </div>
        )}

        {data && !isLoading && (
          <>
            {/* Summary KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Months analysed</p>
                <p className="text-2xl font-bold">{data.total_months}</p>
              </div>
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Anomalies found</p>
                <p className="text-2xl font-bold text-red-600">{data.anomaly_count}</p>
              </div>
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Anomaly rate</p>
                <p className="text-2xl font-bold text-amber-600">{data.anomaly_rate_pct}%</p>
              </div>
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Z-score threshold</p>
                <p className="text-2xl font-bold">±{data.z_threshold}</p>
              </div>
            </div>

            {/* Chart */}
            <Card
              title={`${direction === "EXPORT" ? "Export" : "Import"} anomaly scan — ${data.total_months} months`}
              className="mb-6"
            >
              <EChart height={400} option={buildChartOption(points)} />
              <p className="text-xs text-gray-400 mt-2">
                Method: rolling Z-score (12-month window, threshold ±{data.z_threshold}) + IQR outlier check ·
                <span className="text-red-500 ml-1">▲ spike</span>
                <span className="text-purple-500 ml-2">▼ dip</span>
              </p>
            </Card>

            {/* Anomaly table */}
            {anomalies.length > 0 ? (
              <Card title={`Detected anomalies (${anomalies.length})`}>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b text-xs text-gray-500 uppercase">
                      <tr>
                        <th className="py-2 text-left">Month</th>
                        <th className="py-2 text-right">Value</th>
                        <th className="py-2 text-right">Z-score</th>
                        <th className="py-2 text-center">Type</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {anomalies.map(row => (
                        <tr key={row.period} className="hover:bg-gray-50">
                          <td className="py-2 font-mono">{row.period}</td>
                          <td className="py-2 text-right font-semibold">{fmtUSD(row.value)}</td>
                          <td className={`py-2 text-right font-mono font-semibold ${
                            row.anomaly_type === "spike" ? "text-red-600" : "text-purple-600"
                          }`}>
                            {row.z_score != null ? (row.z_score > 0 ? "+" : "") + row.z_score : "—"}
                          </td>
                          <td className="py-2 text-center">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                              row.anomaly_type === "spike"
                                ? "bg-red-100 text-red-700"
                                : "bg-purple-100 text-purple-700"
                            }`}>
                              {row.anomaly_type === "spike" ? "▲ Spike" : "▼ Dip"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            ) : (
              <div className="bg-green-50 border border-green-200 text-green-800 rounded-lg p-4 text-sm text-center">
                No anomalies detected in the selected window — trade pattern appears normal.
              </div>
            )}
          </>
        )}
      </div>
    </Shell>
  );
}
