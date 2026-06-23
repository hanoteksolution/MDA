/**
 * MDA unified print design system — shared by invoices, reports, lists, and module documents.
 * Module-specific CSS files append overrides after this base.
 */
export const MDA_BASE_DOCUMENT_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --mda-navy: #001B3D;
  --mda-blue: #2563EB;
  --mda-green: #16A34A;
  --mda-border: #E2E8F0;
  --mda-muted: #64748B;
  --mda-stripe: #F8FAFC;
}

.mda-doc, .sales-doc, .table-report-doc, .product-list-doc, .sales-report-doc,
.customer-report-doc, .po-doc, .dn-doc {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  color: #0F172A;
  background: #fff;
  font-size: 10.5px;
  line-height: 1.5;
  padding: 32px 36px 0;
  width: 794px;
  max-width: 100%;
  margin: 0 auto;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.mda-doc *, .sales-doc *, .table-report-doc *, .product-list-doc *, .sales-report-doc *,
.customer-report-doc *, .po-doc *, .dn-doc * { box-sizing: border-box; }

/* ── Header (matches Tax Invoice / Quotation) ── */
.mda-top, .sd-top, .tr-top, .pl-top, .sr-top, .cr-header, .po-top, .dn-top {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 22px;
}
.mda-brand, .sd-brand, .tr-brand, .pl-brand, .sr-brand, .po-brand, .dn-brand {
  display: flex; align-items: center; gap: 12px;
}
.mda-logo, .sd-logo-hex, .tr-logo, .pl-logo, .sr-logo, .cr-logo, .po-logo, .dn-logo {
  width: 52px; height: 52px; flex-shrink: 0;
}
.mda-company, .sd-company-name, .tr-company, .pl-company, .sr-company, .cr-company, .po-company, .dn-company {
  margin: 0; font-size: 20px; font-weight: 800;
  color: var(--mda-navy); letter-spacing: 0.03em; text-transform: uppercase;
}
.mda-tag, .sd-company-tag, .tr-tag, .pl-tag, .sr-tag, .po-tag, .dn-tag, .cr-tag {
  margin: 3px 0 0; font-size: 10px; font-weight: 600;
  color: var(--mda-blue); letter-spacing: 0.16em; text-transform: uppercase;
}

.mda-doc-badge, .sd-doc-badge, .tr-doc-badge {
  text-align: center; min-width: 190px;
}
.mda-doc-badge .title, .sd-doc-badge .title, .tr-doc-badge .title {
  margin: 0; background: var(--mda-navy); border-radius: 10px;
  padding: 10px 20px; font-size: 11px; font-weight: 800;
  color: #fff; letter-spacing: 0.12em; text-transform: uppercase;
}
.mda-doc-badge .number, .sd-doc-badge .number, .tr-doc-badge .number {
  margin: 8px 0 0; font-size: 10px; font-weight: 600;
  font-family: ui-monospace, 'Consolas', monospace;
  padding: 6px 14px; border-radius: 8px;
  background: #EFF6FF; color: var(--mda-blue);
  display: inline-block;
}
.mda-doc-badge .meta, .tr-doc-badge .meta {
  margin: 6px 0 0; font-size: 9.5px; color: var(--mda-muted); line-height: 1.5;
}

/* ── Meta / info rows ── */
.mda-info-row, .sd-info-row, .po-info-row, .dn-info-row {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 28px; margin-bottom: 20px;
}
.mda-meta-table, .sd-meta-table, .po-meta-table, .dn-meta-table, .cr-meta-table {
  width: 100%; font-size: 10px;
}
.mda-meta-table td, .sd-meta-table td, .po-meta-table td, .dn-meta-table td, .cr-meta-table td {
  padding: 4px 0; vertical-align: top;
}
.mda-meta-table td:first-child, .sd-meta-table td:first-child, .po-meta-table td:first-child,
.dn-meta-table td:first-child, .cr-meta-table td:first-child {
  color: #334155; font-weight: 600; white-space: nowrap; padding-right: 8px;
}
.mda-meta-table td:last-child, .sd-meta-table td:last-child, .po-meta-table td:last-child,
.dn-meta-table td:last-child, .cr-meta-table td:last-child {
  font-weight: 600; text-align: right; color: #0F172A;
}

.mda-party-label, .sd-party-label, .po-party-label, .dn-party-label {
  font-size: 11px; font-weight: 700; color: var(--mda-navy); margin-bottom: 6px;
}
.mda-party-name, .sd-party-name, .po-party-name, .dn-party-name {
  font-size: 12px; font-weight: 700; margin-bottom: 6px;
}
.mda-party-line, .sd-party-line, .po-party-line, .dn-party-line {
  font-size: 10px; color: var(--mda-muted); margin-top: 3px; line-height: 1.45;
}

/* ── Section labels ── */
.mda-section-label, .cr-section-label {
  font-size: 8.5px; font-weight: 700; color: var(--mda-muted);
  text-transform: uppercase; letter-spacing: 0.1em;
  background: var(--mda-stripe); border: 1px solid var(--mda-border);
  border-radius: 6px; padding: 6px 10px; margin-bottom: 10px;
}

/* ── KPI cards ── */
.mda-kpi-grid, .tr-kpi-grid, .pl-kpi-grid, .sr-kpi-grid, .cr-kpi-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 12px; margin-bottom: 20px;
}
.mda-kpi-grid.eight, .cr-kpi-grid.eight { grid-template-columns: repeat(4, 1fr); }
.mda-kpi, .tr-kpi, .pl-kpi, .sr-kpi, .cr-kpi {
  border: 1px solid var(--mda-border); border-radius: 10px;
  padding: 12px 14px; background: #fff;
  border-top: 3px solid var(--mda-kpi-accent, var(--mda-blue));
}
.mda-kpi .label, .tr-kpi .label, .pl-kpi .label, .sr-kpi .label, .cr-kpi .label {
  font-size: 9px; font-weight: 600; color: var(--mda-muted);
  text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px;
}
.mda-kpi .value, .tr-kpi .value, .pl-kpi .value, .sr-kpi .value, .cr-kpi .value {
  font-size: 16px; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;
  word-break: break-word;
}
.mda-kpi .sub, .cr-kpi .sub { font-size: 8px; color: var(--mda-muted); margin-top: 2px; }
.mda-kpi .icon, .pl-kpi .icon, .sr-kpi .icon-wrap, .cr-kpi .icon {
  margin-bottom: 6px; color: var(--mda-kpi-accent, var(--mda-blue));
}

/* ── Data tables ── */
.mda-table-wrap, .sd-table-wrap, .tr-table-wrap, .pl-table-wrap, .sr-table-wrap, .po-table-wrap, .dn-table-wrap {
  border: 1px solid var(--mda-border); border-radius: 8px; overflow: hidden;
  margin-bottom: 20px;
}
.mda-table, .sd-table, .tr-table, .pl-table, .sr-table, .po-table, .dn-table, .cr-table {
  width: 100%; border-collapse: collapse; font-size: 10px;
}
.mda-table thead th, .sd-table thead th, .tr-table thead th, .pl-table thead th,
.sr-table thead th, .po-table thead th, .dn-table thead th, .cr-table thead th {
  background: var(--mda-navy); color: #fff;
  padding: 10px 12px; font-size: 8.5px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase; text-align: left;
}
.mda-table thead th:first-child, .sd-table thead th:first-child, .tr-table thead th:first-child,
.pl-table thead th:first-child, .po-table thead th:first-child, .dn-table thead th:first-child,
.cr-table thead th:first-child { border-radius: 8px 0 0 0; }
.mda-table thead th:last-child, .sd-table thead th:last-child, .tr-table thead th:last-child,
.pl-table thead th:last-child, .po-table thead th:last-child, .dn-table thead th:last-child,
.cr-table thead th:last-child { border-radius: 0 8px 0 0; }
.mda-table thead th.center, .sd-table thead th.center, .tr-table thead th.center,
.pl-table thead th.center, .sr-table thead th.center, .po-table thead th.center,
.dn-table thead th.center, .cr-table thead th.center { text-align: center; }
.mda-table thead th.right, .sd-table thead th.right, .tr-table thead th.right,
.pl-table thead th.right, .sr-table thead th.right, .po-table thead th.right,
.dn-table thead th.right, .cr-table thead th.right { text-align: right; }
.mda-table tbody td, .sd-table tbody td, .tr-table tbody td, .pl-table tbody td,
.sr-table tbody td, .po-table tbody td, .dn-table tbody td, .cr-table tbody td {
  padding: 9px 12px; border-bottom: 1px solid var(--mda-border); vertical-align: middle;
}
.mda-table tbody tr:nth-child(even) td, .sd-table tbody tr:nth-child(even) td,
.tr-table tbody tr:nth-child(even) td, .pl-table tbody tr:nth-child(even) td,
.sr-table tbody tr:nth-child(even) td, .po-table tbody tr:nth-child(even) td,
.cr-table tbody tr:nth-child(even) td { background: var(--mda-stripe); }
.mda-table tbody tr:nth-child(odd) td, .sd-table tbody tr:nth-child(odd) td,
.tr-table tbody tr:nth-child(odd) td, .pl-table tbody tr:nth-child(odd) td,
.sr-table tbody tr:nth-child(odd) td, .po-table tbody tr:nth-child(odd) td,
.cr-table tbody tr:nth-child(odd) td { background: #fff; }
.mda-table tbody tr:last-child td, .sd-table tbody tr:last-child td,
.tr-table tbody tr:last-child td, .pl-table tbody tr:last-child td,
.sr-table tbody tr:last-child td, .po-table tbody tr:last-child td,
.cr-table tbody tr:last-child td { border-bottom: none; }
.mda-table .idx, .sd-table .idx, .tr-table .idx, .pl-table .idx, .sr-table .idx,
.cr-table .idx { color: var(--mda-muted); font-weight: 600; text-align: center; font-size: 9px; }
.mda-table .num, .sd-table .num, .tr-table .num, .pl-table .num, .sr-table .num,
.po-table .num, .dn-table .num, .cr-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.mda-table .qty, .sd-table .qty, .po-table .qty, .dn-table .qty { text-align: center; }

/* ── Panels / charts grid ── */
.mda-charts, .sr-charts, .cr-charts, .pl-analytics {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 16px; margin-bottom: 20px;
}
.mda-panel, .sr-panel, .cr-panel, .pl-panel, .po-side-box, .dn-side-box {
  border: 1px solid var(--mda-border); border-radius: 8px;
  padding: 14px 16px; background: #fff;
}
.mda-panel h3, .sr-panel h3, .cr-panel h3, .pl-panel h3, .po-side-box h4, .dn-side-box h4 {
  margin: 0 0 10px; font-size: 10px; font-weight: 700; color: var(--mda-navy);
  text-transform: uppercase; letter-spacing: 0.06em;
}

/* ── Navy footer bar ── */
.mda-footer-bar, .tr-footer, .pl-footer, .sr-footer, .cr-footer, .po-footer {
  margin-top: auto; margin-left: -36px; margin-right: -36px;
  background: var(--mda-navy); color: #fff;
  padding: 14px 36px; display: flex;
  justify-content: space-between; align-items: center;
  font-size: 9.5px;
}
.mda-footer-bar .thanks, .sr-footer .thanks, .pl-footer .thanks { font-weight: 600; flex: 1; text-align: center; }
.mda-footer-bar .contact, .tr-footer .contact { opacity: 0.9; }
.mda-footer-bar .page, .sr-footer .page, .pl-footer .page { opacity: 0.85; font-size: 9px; }

.mda-contact-row, .sd-contact-row, .po-contact-row, .dn-contact-row {
  display: flex; justify-content: center; gap: 20px;
  font-size: 9.5px; flex-wrap: wrap;
}
.mda-contact-row span, .sd-contact-row span, .po-contact-row span, .dn-contact-row span {
  display: inline-flex; align-items: center; gap: 5px;
}

@media print {
  .mda-doc, .sales-doc, .table-report-doc, .product-list-doc, .sales-report-doc,
  .customer-report-doc, .po-doc, .dn-doc { padding: 20px 28px 0; width: 100%; }
  .mda-footer-bar, .tr-footer, .pl-footer, .sr-footer, .cr-footer, .po-footer {
    margin-left: -28px; margin-right: -28px; padding: 12px 28px;
  }
}
`;
