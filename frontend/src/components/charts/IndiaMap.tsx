"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import * as echarts from "echarts";
import { fmtUSD } from "@/lib/format";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
});

const MAP_NAME = "india";
const NAME_PROPERTY = "ST_NM";

const STATE_NAME_ALIASES: Record<string, string> = {
  "Jammu and Kashmir": "Jammu & Kashmir",
  "Andaman and Nicobar": "Andaman & Nicobar",
  "Andaman and Nicobar Islands": "Andaman & Nicobar",
  "Dadra and Nagar Haveli": "Dadra and Nagar Haveli and Daman and Diu",
  "Daman and Diu": "Dadra and Nagar Haveli and Daman and Diu",
  Delhi: "NCT of Delhi",
};

interface StateValue {
  label: string;
  code?: string;
  value: number;
}

interface IndiaMapProps {
  states: StateValue[];
  height?: number;
  onStateClick?: (state: StateValue | null, geoName: string) => void;
}

let mapRegistered = false;

function niceMax(value: number) {
  if (!value || value <= 0) return 1;
  const power = Math.pow(10, Math.floor(Math.log10(value)));
  return Math.ceil(value / power) * power;
}

export default function IndiaMap({
  states = [],
  height = 560,
  onStateClick,
}: IndiaMapProps) {
  const [ready, setReady] = useState(mapRegistered);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMap() {
      try {
        if (mapRegistered || echarts.getMap(MAP_NAME)) {
          mapRegistered = true;
          if (!cancelled) setReady(true);
          return;
        }

        const response = await fetch("/india-states.geojson");
        if (!response.ok) {
          throw new Error(`Failed to load /india-states.geojson (${response.status})`);
        }

        const geojson = await response.json();
        if (!geojson || !Array.isArray(geojson.features)) {
          throw new Error("Invalid India GeoJSON. Expected FeatureCollection with features array.");
        }

        echarts.registerMap(MAP_NAME, geojson as any);
        mapRegistered = true;

        if (!cancelled) {
          setReady(true);
          setLoadError(null);
        }
      } catch (error: any) {
        console.error("[IndiaMap] map load failed", error);
        if (!cancelled) setLoadError(error?.message || "India map failed to load");
      }
    }

    loadMap();

    return () => {
      cancelled = true;
    };
  }, []);

  const mappedData = useMemo(
    () =>
      (states || [])
        .filter((s) => Number(s.value || 0) > 0)
        .map((s) => ({
          name: STATE_NAME_ALIASES[s.label] ?? s.label,
          value: Number(s.value || 0),
          _origLabel: s.label,
          _code: s.code,
        })),
    [states]
  );

  const maxValue = niceMax(Math.max(...mappedData.map((s) => s.value), 1));

  const option = useMemo(
    () => ({
      tooltip: {
        trigger: "item",
        formatter: (p: any) => {
          if (p.value == null || Number.isNaN(Number(p.value))) {
            return `<b>${p.name}</b><br/>No data`;
          }
          return `<b>${p.name}</b><br/>Value: ${fmtUSD(Number(p.value))}`;
        },
      },
      visualMap: {
        left: 20,
        bottom: 18,
        min: 0,
        max: maxValue,
        text: ["High", "Low"],
        calculable: false,
        itemHeight: 130,
        itemWidth: 14,
        formatter: (v: number) => fmtUSD(v),
        inRange: {
          color: ["#eaf2fb", "#c8ddf0", "#91bee0", "#4f93c8", "#174a7c"],
        },
        textStyle: {
          fontSize: 11,
          color: "#475569",
        },
      },
      series: [
        {
          name: "India States",
          type: "map",
          map: MAP_NAME,
          nameProperty: NAME_PROPERTY,
          roam: true,
          zoom: 1.0,
          layoutCenter: ["50%", "52%"],
          layoutSize: "82%",
          scaleLimit: {
            min: 1,
            max: 6,
          },
          label: {
            show: false,
          },
          emphasis: {
            focus: "self",
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 700,
              color: "#111827",
              backgroundColor: "rgba(255,255,255,0.85)",
              padding: [2, 4],
              borderRadius: 4,
            },
            itemStyle: {
              areaColor: "#facc15",
              borderColor: "#92400e",
              borderWidth: 1.2,
            },
          },
          itemStyle: {
            areaColor: "#eef0f2",
            borderColor: "#ffffff",
            borderWidth: 0.9,
          },
          select: {
            itemStyle: {
              areaColor: "#facc15",
              borderColor: "#92400e",
            },
          },
          data: mappedData,
        },
      ],
    }),
    [mappedData, maxValue]
  );

  if (loadError) {
    return (
      <div
        style={{ height, width: "100%" }}
        className="flex items-center justify-center text-red-600 text-sm text-center px-4"
      >
        {loadError}
        <br />
        Check this file: frontend/public/india-states.geojson
      </div>
    );
  }

  if (!ready) {
    return (
      <div
        style={{ height, width: "100%" }}
        className="flex items-center justify-center text-gray-400 text-sm"
      >
        Loading India map…
      </div>
    );
  }

  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%" }}
      notMerge={true}
      lazyUpdate={true}
      onEvents={{
        click: (params: any) => {
          if (!onStateClick) return;

          const origLabel =
            params.data?._origLabel ??
            Object.entries(STATE_NAME_ALIASES).find(
              ([_orig, mapped]) => mapped === params.name
            )?.[0] ??
            params.name;

          const found = states.find((s) => s.label === origLabel) || null;
          onStateClick(found, params.name);
        },
      }}
    />
  );
}
