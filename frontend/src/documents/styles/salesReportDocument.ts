import { MDA_BASE_DOCUMENT_CSS } from "./baseDocument";

/** Sales analytics report — unified base + chart/summary styles. */
export const SALES_REPORT_CSS = MDA_BASE_DOCUMENT_CSS + `
.sales-report-doc { font-size: 10.5px; }
.mda-kpi .icon-wrap {
  width: 28px; height: 28px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 8px; color: #fff;
  background: var(--mda-kpi-accent, var(--mda-blue));
}
.sr-line-chart { width: 100%; height: 130px; }
.sr-line-chart svg { width: 100%; height: 100%; }
.sr-donut-wrap { display: flex; align-items: center; gap: 14px; }
.sr-donut {
  width: 100px; height: 100px; border-radius: 50%; flex-shrink: 0; position: relative;
}
.sr-donut-hole {
  position: absolute; inset: 20px; background: #fff; border-radius: 50%;
}
.sr-legend { flex: 1; font-size: 9px; }
.sr-legend .item { display: flex; align-items: flex-start; gap: 6px; margin-bottom: 5px; }
.sr-legend .dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 3px; flex-shrink: 0; }
.sr-legend .lbl { flex: 1; color: #334155; line-height: 1.35; }
.sr-legend .amt { font-weight: 700; color: #0F172A; white-space: nowrap; }
.sr-bottom {
  display: grid; grid-template-columns: 1fr 220px;
  gap: 14px; margin-bottom: 22px;
}
.sr-table .name { font-weight: 600; }
.sr-summary { border: 1px solid var(--mda-border); border-radius: 8px; overflow: hidden; }
.sr-summary-head {
  background: var(--mda-navy); color: #fff; padding: 9px 12px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.sr-summary-body { padding: 10px 12px; }
.sr-summary .row {
  display: flex; justify-content: space-between;
  padding: 5px 0; font-size: 9.5px; color: var(--mda-muted);
  border-bottom: 1px solid #F1F5F9;
}
.sr-summary .row:last-child { border-bottom: none; }
.sr-summary .row span:last-child { font-weight: 600; color: #0F172A; }
.sr-summary .row.green span:last-child { color: var(--mda-green); font-weight: 800; }
`;
