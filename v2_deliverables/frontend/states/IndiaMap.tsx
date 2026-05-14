"use client";
/**
 * Place at: frontend/src/components/charts/IndiaMap.tsx
 *
 * Choropleth map of Indian states. Loads GeoJSON from /public on first
 * render and registers it with ECharts. Supports clicking a state.
 *
 * SETUP — you need an India states GeoJSON file:
 *   1. Download from a reliable source, e.g.:
 *      https://gist.github.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112
 *      (raw URL: https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/india_states.geojson)
 *   2. Save to: frontend/public/india-states.geojson
 *   3. Make sure the property name in the GeoJSON for state name is "ST_NM"
 *      (the most common India geoJSON files use this). If yours uses a
 *      different key, update NAME_PROPERTY below.
 */
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import * as echarts from "echarts/core";
import { fmtUSD } from "@/lib/format";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

const NAME_PROPERTY = "ST_NM";  // change if your geoJSON uses a different key
const MAP_NAME = "india";

// Map of state names that may differ between our DB and the GeoJSON.
// Add entries here if you see "no data" for states that should have data.
const STATE_NAME_ALIASES: Record<string, string> = {
  "Jammu and Kashmir": "Jammu & Kashmir",
  "Andaman and Nicobar": "Andaman & Nicobar",
  "Dadra and Nagar Haveli": "Dadra and Nagar Haveli and Daman and Diu",
  "Daman and Diu": "Dadra and Nagar Haveli and Daman and Diu",
  "Telangana": "Telangana",
  "Delhi": "NCT of Delhi",
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

export default function IndiaMap({ states, height = 520, onStateClick }: IndiaMapProps) {
  const [ready, setReady] = useState(mapRegistered);

  useEffect(() => {
    if (mapRegistered) return;
    fetch("/india-states.geojson")
      .then((r) => {
        if (!r.ok) throw new Error("Failed to fetch india-states.geojson");
        return r.json();
      })
      .then((geojson) => {
        echarts.registerMap(MAP_NAME, geojson as any);
        mapRegistered = true;
        setReady(true);
      })
      .catch((e) => {
        console.error("[IndiaMap] could not load geojson:", e);
      });
  }, []);

  // Translate our state list to map names, applying aliases
  const mappedData = states.map((s) => ({
    name: STATE_NAME_ALIASES[s.label] ?? s.label,
    value: s.value,
    _origLabel: s.label,
    _code: s.code,
  }));

  const maxValue = Math.max(...states.map((s) => s.value), 1);

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (p: any) => {
        if (p.value == null || isNaN(p.value)) {
          return `<b>${p.name}</b><br/>No data`;
        }
        return `<b>${p.name}</b><br/>Exports: ${fmtUSD(p.value)}`;
      },
    },
    visualMap: {
      left: 16,
      bottom: 16,
      min: 0,
      max: maxValue,
      text: ["High", "Low"],
      calculable: true,
      inRange: {
        // sequential blue-green palette - ~5 stops
        color: ["#eef5fb", "#c0d8eb", "#7faecf", "#3a82b3", "#1f4e78"],
      },
      textStyle: { fontSize: 11 },
    },
    series: [
      {
        type: "map",
        map: MAP_NAME,
        roam: false,
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 11, fontWeight: 600 },
          itemStyle: { areaColor: "#fde68a", borderColor: "#92400e" },
        },
        select: {
          itemStyle: { areaColor: "#f59e0b" },
        },
        data: mappedData,
        nameProperty: NAME_PROPERTY,
        itemStyle: {
          borderColor: "#fff",
          borderWidth: 0.5,
        },
      },
    ],
  };

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
      notMerge
      lazyUpdate
      onEvents={{
        click: (params: any) => {
          if (!onStateClick) return;
          // Find original state from our data using aliases reverse lookup
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
