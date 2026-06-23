export const DOC = {
  primary: "#0F172A",
  secondary: "#1E293B",
  accent: "#2563EB",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  bg: "#F8FAFC",
  card: "#FFFFFF",
  border: "#E2E8F0",
  muted: "#64748B",
  font:
    "'Inter', 'SF Pro Display', 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
} as const;

export const STATUS_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  paid: { bg: "linear-gradient(135deg,#10B981,#059669)", color: "#fff", label: "Paid" },
  unpaid: { bg: "linear-gradient(135deg,#EF4444,#DC2626)", color: "#fff", label: "Unpaid" },
  pending: { bg: "linear-gradient(135deg,#F59E0B,#D97706)", color: "#fff", label: "Pending" },
  draft: { bg: "linear-gradient(135deg,#2563EB,#1D4ED8)", color: "#fff", label: "Draft" },
  completed: { bg: "linear-gradient(135deg,#10B981,#047857)", color: "#fff", label: "Completed" },
  cancelled: { bg: "linear-gradient(135deg,#7F1D1D,#991B1B)", color: "#fff", label: "Cancelled" },
  out_of_stock: { bg: "linear-gradient(135deg,#EF4444,#B91C1C)", color: "#fff", label: "Out of Stock" },
  low_stock: { bg: "linear-gradient(135deg,#F59E0B,#B45309)", color: "#fff", label: "Low Stock" },
  active: { bg: "linear-gradient(135deg,#10B981,#059669)", color: "#fff", label: "Active" },
  sent: { bg: "linear-gradient(135deg,#2563EB,#1D4ED8)", color: "#fff", label: "Sent" },
  accepted: { bg: "linear-gradient(135deg,#10B981,#059669)", color: "#fff", label: "Accepted" },
  overdue: { bg: "linear-gradient(135deg,#EF4444,#DC2626)", color: "#fff", label: "Overdue" },
};

export const KPI_ACCENTS: Record<string, string> = {
  primary: "linear-gradient(135deg,#2563EB 0%,#1D4ED8 100%)",
  success: "linear-gradient(135deg,#10B981 0%,#059669 100%)",
  warning: "linear-gradient(135deg,#F59E0B 0%,#D97706 100%)",
  danger: "linear-gradient(135deg,#EF4444 0%,#DC2626 100%)",
  neutral: "linear-gradient(135deg,#0F172A 0%,#1E293B 100%)",
};
