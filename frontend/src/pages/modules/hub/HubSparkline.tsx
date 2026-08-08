import { useId, useMemo } from "react";
import { motion } from "framer-motion";
import type { WorkspaceTone } from "@/navigation/moduleWorkspaces";

export const TONE_HEX: Record<WorkspaceTone, string> = {
  sky: "#0ea5e9",
  orange: "#f97316",
  blue: "#3b82f6",
  teal: "#14b8a6",
  indigo: "#6366f1",
  violet: "#8b5cf6",
  emerald: "#10b981",
  green: "#22c55e",
  amber: "#f59e0b",
  cyan: "#06b6d4",
  stone: "#78716c",
  lime: "#84cc16",
  slate: "#64748b",
  fuchsia: "#d946ef",
  rose: "#f43f5e",
  zinc: "#71717a",
  neutral: "#737373",
  purple: "#a855f7",
  pink: "#ec4899",
};

interface HubSparklineProps {
  data?: number[];
  color?: string;
  className?: string;
  height?: number;
}

export function HubSparkline({ data = [], color = TONE_HEX.emerald, className, height = 40 }: HubSparklineProps) {
  const id = useId().replace(/:/g, "");
  const path = useMemo(() => {
    if (data.length < 2) return null;
    const w = 128;
    const h = height;
    const min = Math.min(...data);
    const max = Math.max(...data);
    const span = max - min || 1;
    const pts = data.map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / span) * (h - 6) - 3;
      return [x, y] as const;
    });
    const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" ");
    return { w, h, line, area: `${line} L${w},${h} L0,${h} Z` };
  }, [data, height]);

  if (!path) return <div className={className} style={{ height }} />;

  return (
    <svg viewBox={`0 0 ${path.w} ${path.h}`} className={className} preserveAspectRatio="none" aria-hidden>
      <defs>
        <linearGradient id={`g-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.38" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <motion.path d={path.area} fill={`url(#g-${id})`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }} />
      <motion.path
        d={path.line}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 1.05, ease: [0.22, 1, 0.36, 1] }}
      />
    </svg>
  );
}

export function seededSeries(seed: string, base = 12, n = 14): number[] {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i += 1) h = Math.imul(h ^ seed.charCodeAt(i), 16777619);
  const floor = Math.max(4, Math.abs(base) || 12);
  return Array.from({ length: n }, (_, i) => {
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    const wave = Math.sin(i / 2.15 + (h % 17) / 6) * 0.22;
    const noise = ((h >>> 8) % 100) / 500 - 0.1;
    return Math.max(1, floor * (1 + wave + noise));
  });
}

export function seriesDelta(series?: number[]): number | undefined {
  if (!series || series.length < 2) return undefined;
  const a = series[series.length - 2];
  const b = series[series.length - 1];
  if (!a) return b ? 100 : 0;
  return ((b - a) / Math.abs(a)) * 100;
}
