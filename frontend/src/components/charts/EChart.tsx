"use client";
import dynamic from "next/dynamic";
import type { CSSProperties } from "react";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface EChartProps {
  option: any;
  style?: CSSProperties;
  height?: number | string;
  onEvents?: Record<string, (params: any) => void>;
}

export default function EChart({ option, style, height = 320, onEvents }: EChartProps) {
  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%", ...style }}
      notMerge={true}
      lazyUpdate={true}
      onEvents={onEvents}
    />
  );
}
