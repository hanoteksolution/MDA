import { MDA_BASE_DOCUMENT_CSS } from "./baseDocument";

/** Customers report — unified base + analytics-specific styles. */
export const CUSTOMER_REPORT_CSS = MDA_BASE_DOCUMENT_CSS + `
@import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600&display=swap');

:root {
  --cr-purple: #8B5CF6;
  --cr-orange: #F59E0B;
  --cr-red: #DC2626;
}
.customer-report-doc { font-size: 10px; line-height: 1.45; padding: 28px 32px 0; }
.cr-header-extra {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin: -8px 0 16px; padding-bottom: 12px;
  border-bottom: 1px solid var(--mda-border);
}
.cr-contact {
  font-size: 8.5px; color: var(--mda-muted); line-height: 1.6; flex: 1;
}
.cr-contact div { margin-bottom: 2px; }
.cr-qr { width: 64px; height: 64px; border: 1px solid var(--mda-border); border-radius: 6px; padding: 3px; }
.cr-kpi-grid.eight .mda-kpi .value { font-size: 15px; }
.cr-kpi-grid.eight .mda-kpi .label { font-size: 7.5px; }
.cr-panel-head {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
}
.cr-year-badge {
  font-size: 8px; font-weight: 600; color: var(--mda-blue);
  border: 1px solid var(--mda-border); border-radius: 4px; padding: 2px 6px;
}
.cr-donut-wrap { display: flex; align-items: center; gap: 12px; }
.cr-donut {
  width: 90px; height: 90px; border-radius: 50%; flex-shrink: 0; position: relative;
}
.cr-donut-hole {
  position: absolute; inset: 18px; background: #fff; border-radius: 50%;
}
.cr-legend { flex: 1; font-size: 8.5px; }
.cr-legend .item { display: flex; align-items: center; gap: 5px; margin-bottom: 5px; }
.cr-legend .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.cr-legend .lbl { flex: 1; color: #334155; }
.cr-legend .pct { font-weight: 700; }
.cr-total-box {
  margin-top: 8px; padding-top: 6px; border-top: 1px solid var(--mda-border);
  font-size: 8.5px; font-weight: 700; color: var(--mda-navy);
}
.cr-line-chart svg { width: 100%; height: 100px; display: block; }
.cr-table { font-size: 8.5px; }
.cr-customer-cell { display: flex; align-items: center; gap: 6px; }
.cr-avatar {
  width: 24px; height: 24px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 800; color: #fff;
}
.cr-badge {
  display: inline-block; padding: 2px 7px; border-radius: 999px;
  font-size: 7.5px; font-weight: 700; text-transform: capitalize;
}
.cr-badge.retail { background: #DCFCE7; color: #15803D; }
.cr-badge.corporate { background: #DBEAFE; color: #1D4ED8; }
.cr-badge.wholesale { background: #EDE9FE; color: #6D28D9; }
.cr-status.active { color: var(--mda-green); font-weight: 700; }
.cr-status.inactive { color: var(--mda-muted); }
.cr-table-foot {
  font-size: 8px; color: var(--mda-muted); padding: 6px 8px;
  border-top: 1px solid var(--mda-border); background: var(--mda-stripe);
}
.cr-mid-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 12px; margin-bottom: 14px;
}
.cr-mini-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.cr-mini-card {
  border: 1px solid var(--mda-border); border-radius: 8px;
  padding: 10px; background: #fff;
}
.cr-mini-card .label { font-size: 8px; color: var(--mda-muted); font-weight: 600; }
.cr-mini-card .value { font-size: 14px; font-weight: 800; margin-top: 4px; }
.cr-mini-card.warn .value { color: var(--cr-red); }
.cr-top-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 10px; margin-bottom: 16px;
}
.cr-top-list { font-size: 8.5px; }
.cr-top-list .row {
  display: grid; grid-template-columns: 18px 1fr auto auto;
  gap: 6px; align-items: center; padding: 5px 0;
  border-bottom: 1px solid #F1F5F9;
}
.cr-top-list .rank { font-weight: 800; color: var(--mda-muted); }
.cr-top-list .amt { font-weight: 700; text-align: right; }
.cr-top-list .pct { color: var(--mda-muted); font-size: 8px; text-align: right; min-width: 28px; }
.cr-signoff {
  display: grid; grid-template-columns: 1.2fr 1fr 1fr;
  gap: 16px; align-items: end; margin-bottom: 16px; padding-top: 8px;
}
.cr-thanks .script {
  font-family: 'Dancing Script', cursive; font-size: 22px;
  color: var(--mda-navy); margin: 0 0 4px;
}
.cr-thanks p { margin: 0; font-size: 8.5px; color: var(--mda-muted); line-height: 1.5; }
.cr-sign-box .label { font-size: 8.5px; color: var(--mda-muted); text-align: center; margin-bottom: 4px; }
.cr-sign-box .line { border-top: 1px solid #94A3B8; padding-top: 6px; min-height: 36px; }
.cr-page-meta { text-align: right; font-size: 8px; color: var(--mda-muted); }
.cr-footer { text-align: center; font-weight: 600; letter-spacing: 0.04em; }
@media print {
  .customer-report-doc { padding: 18px 24px 0; }
  .cr-footer { margin-left: -24px; margin-right: -24px; padding: 8px 24px; }
}
`;
