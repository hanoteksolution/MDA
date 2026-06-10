import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { chartColors } from "@/design-system";

const tooltipStyle = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "12px",
  fontSize: "12px",
  boxShadow: "0 12px 32px -12px rgb(0 0 0 / 0.15)",
  padding: "10px 12px",
};

interface SalesTrendChartProps {
  data: { month: string; sales: number; revenue: number }[];
}

export function SalesTrendChart({ data }: SalesTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={chartColors.primary} stopOpacity={0.35} />
            <stop offset="100%" stopColor={chartColors.primary} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="4 4" stroke="hsl(var(--border))" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `$${v / 1000}k`}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(v) => [`$${Number(v).toLocaleString()}`, "Sales"]}
        />
        <Area
          type="monotone"
          dataKey="sales"
          stroke={chartColors.primary}
          strokeWidth={2.5}
          fill="url(#salesGradient)"
          animationDuration={900}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

interface RevenueChartProps {
  data: { month: string; revenue: number }[];
}

export function RevenueChart({ data }: RevenueChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="revenueBar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={chartColors.primary} stopOpacity={1} />
            <stop offset="100%" stopColor={chartColors.primary} stopOpacity={0.55} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="4 4" stroke="hsl(var(--border))" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `$${v / 1000}k`}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(v) => [`$${Number(v).toLocaleString()}`, "Revenue"]}
        />
        <Bar
          dataKey="revenue"
          fill="url(#revenueBar)"
          radius={[8, 8, 0, 0]}
          maxBarSize={36}
          animationDuration={900}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

interface ProfitChartProps {
  data: { month: string; profit: number; expenses: number }[];
}

export function ProfitChart({ data }: ProfitChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="4 4" stroke="hsl(var(--border))" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `$${v / 1000}k`}
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Line
          type="monotone"
          dataKey="profit"
          stroke="hsl(var(--chart-2))"
          strokeWidth={2.5}
          dot={false}
          name="Profit"
          animationDuration={900}
        />
        <Line
          type="monotone"
          dataKey="expenses"
          stroke="hsl(var(--chart-4))"
          strokeWidth={2.5}
          dot={false}
          name="Expenses"
          animationDuration={900}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
