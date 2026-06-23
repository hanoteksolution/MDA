/** Screen preview — includes web font. */
export const THERMAL_RECEIPT_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.mda-thermal {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  color: #0F172A;
  background: #fff;
  font-size: 11px;
  line-height: 1.45;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.mda-thermal * { box-sizing: border-box; }

.th-brand {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 10px;
}
.th-logo { width: 36px; height: 36px; flex-shrink: 0; }
.th-company {
  margin: 0; font-size: 13px; font-weight: 800;
  color: #0F172A; letter-spacing: 0.02em; text-transform: uppercase;
}
.th-tag {
  margin: 1px 0 0; font-size: 8px; font-weight: 600;
  color: #2563EB; letter-spacing: 0.12em; text-transform: uppercase;
}

.th-store { text-align: center; font-size: 9.5px; color: #334155; margin-bottom: 10px; line-height: 1.5; }
.th-store p { margin: 0; }

.th-title {
  text-align: center; font-size: 12px; font-weight: 800;
  letter-spacing: 0.14em; text-transform: uppercase;
  margin: 0 0 10px; color: #0F172A;
}

.th-dash { border: none; border-top: 1px dashed #0F172A; margin: 10px 0; opacity: 0.35; }

.th-meta .row {
  display: flex; justify-content: space-between; gap: 8px;
  font-size: 10px; margin: 3px 0;
}
.th-meta .label { color: #334155; font-weight: 600; }
.th-meta .value { text-align: right; font-weight: 600; color: #0F172A; }

.th-table { width: 100%; border-collapse: collapse; font-size: 10px; }
.th-table thead th {
  font-weight: 800; font-size: 9px; text-transform: uppercase;
  letter-spacing: 0.04em; padding: 4px 0 6px; border-bottom: 1px solid #0F172A;
  color: #0F172A;
}
.th-table thead th.left { text-align: left; }
.th-table thead th.right { text-align: right; }
.th-table thead th.center { text-align: center; }
.th-table tbody td {
  padding: 5px 0; vertical-align: top; border-bottom: 1px dotted #E2E8F0;
  font-size: 10px;
}
.th-table tbody tr:last-child td { border-bottom: none; }
.th-table .item-name { font-weight: 600; color: #0F172A; }
.th-table .num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
.th-table .qty { text-align: center; }

.th-totals .row {
  display: flex; justify-content: space-between;
  font-size: 10px; margin: 3px 0; color: #334155;
}
.th-totals .row span:last-child { font-weight: 600; color: #0F172A; }
.th-totals .grand {
  font-size: 13px; font-weight: 800; color: #0F172A;
  margin: 2px 0;
}
.th-totals .grand span:last-child { font-size: 14px; }

.th-thanks {
  text-align: center; font-size: 10px; font-weight: 600;
  color: #334155; margin: 10px 0 12px;
}
.th-barcode { text-align: center; margin-top: 4px; }
.th-barcode img { max-width: 100%; height: 44px; object-fit: contain; }

/* 58mm narrow */
.mda-thermal.narrow { font-size: 10px; }
.mda-thermal.narrow .th-company { font-size: 11px; }
.mda-thermal.narrow .th-table { font-size: 9px; }
.mda-thermal.narrow .th-totals .grand { font-size: 12px; }
`;

/** Print-only — system fonts, sized for POS thermal rolls (no web font import). */
export const THERMAL_RECEIPT_PRINT_CSS = `
.mda-thermal {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  color: #000;
  background: #fff;
  line-height: 1.4;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.mda-thermal * { box-sizing: border-box; }
.th-brand { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.th-logo { width: 32px; height: 32px; flex-shrink: 0; }
.th-company { margin: 0; font-size: 14px; font-weight: 800; text-transform: uppercase; }
.th-tag { margin: 1px 0 0; font-size: 8px; font-weight: 600; color: #2563EB; letter-spacing: 0.1em; text-transform: uppercase; }
.th-store { text-align: center; font-size: 10px; color: #333; margin-bottom: 8px; line-height: 1.4; }
.th-store p { margin: 0; }
.th-title { text-align: center; font-size: 13px; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0 0 8px; }
.th-dash { border: none; border-top: 1px dashed #000; margin: 8px 0; opacity: 0.4; }
.th-meta .row { display: flex; justify-content: space-between; gap: 6px; font-size: 11px; margin: 2px 0; }
.th-meta .label { font-weight: 600; }
.th-meta .value { text-align: right; font-weight: 700; }
.th-table { width: 100%; border-collapse: collapse; font-size: 11px; table-layout: fixed; }
.th-table thead th { font-weight: 800; font-size: 9px; text-transform: uppercase; padding: 3px 0 5px; border-bottom: 1px solid #000; }
.th-table thead th.left { text-align: left; }
.th-table thead th.right { text-align: right; }
.th-table thead th.center { text-align: center; }
.th-table tbody td { padding: 4px 0; vertical-align: top; border-bottom: 1px dotted #ccc; font-size: 11px; }
.th-table tbody tr:last-child td { border-bottom: none; }
.th-table .item-name { font-weight: 600; word-break: break-word; }
.th-table .num { text-align: right; white-space: nowrap; }
.th-table .qty { text-align: center; }
.th-totals .row { display: flex; justify-content: space-between; font-size: 11px; margin: 2px 0; }
.th-totals .row span:last-child { font-weight: 700; }
.th-totals .grand { font-size: 14px; font-weight: 800; margin: 2px 0; }
.th-totals .grand span:last-child { font-size: 15px; }
.th-thanks { text-align: center; font-size: 11px; font-weight: 600; margin: 8px 0 10px; }
.th-barcode { text-align: center; }
.th-barcode img { max-width: 100%; height: auto; }
.mda-thermal.narrow { font-size: 10px; }
.mda-thermal.narrow .th-company { font-size: 12px; }
.mda-thermal.narrow .th-table { font-size: 10px; }
.mda-thermal.narrow .th-totals .grand { font-size: 13px; }
body.thermal-58 .mda-thermal { font-size: 10px; }
body.thermal-58 .th-company { font-size: 12px; }
body.thermal-58 .th-table { font-size: 10px; }
`;
