/** Screen preview — includes web font. */
export const THERMAL_RECEIPT_CSS = `
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

.mda-thermal {
  font-family: 'IBM Plex Mono', 'Consolas', 'Courier New', monospace;
  color: #111;
  background: #fff;
  font-size: 11px;
  line-height: 1.35;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.mda-thermal * { box-sizing: border-box; }

/* ── Kisima-style short receipt ── */
.mda-thermal.kisima { font-size: 10.5px; padding: 0 2px; }
.th-kisima-head { text-align: center; margin-bottom: 6px; padding: 0 2px; }
.th-kisima-head .th-company {
  margin: 0; font-size: 14px; font-weight: 700;
  letter-spacing: 0.04em; text-transform: uppercase;
}
.th-brand-logo {
  display: block;
  max-width: 72px;
  max-height: 48px;
  width: auto;
  height: auto;
  margin: 0 auto 4px;
  object-fit: contain;
}
.th-tel { margin: 2px 0 0; font-size: 10px; }
.th-receipt-ref {
  text-align: center;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin: 4px 0 0;
  color: #333;
}

.th-guide {
  border: 1.5px solid #111;
  padding: 5px 7px;
  margin: 6px 0 4px;
}
.th-guide-row {
  display: flex; justify-content: space-between; gap: 6px;
  font-size: 9.5px; font-weight: 600; margin: 2px 0;
}
.th-guide-row span:last-child { font-weight: 700; text-align: right; word-break: break-all; }

.th-sep {
  border: none; border-top: 1px dashed #111;
  margin: 6px 0; height: 0;
}
.th-sep-dbl {
  border-top-style: solid;
  border-top-width: 2px;
  border-bottom: 1px solid #111;
  padding-bottom: 1px;
  margin: 7px 0;
}

.th-meta .row {
  display: flex; justify-content: space-between; gap: 8px;
  font-size: 10px; margin: 2px 0; padding: 0 2px;
}
.th-meta .label { font-weight: 500; }
.th-meta .value { text-align: right; font-weight: 600; }

.th-table { width: 100%; border-collapse: collapse; font-size: 10px; table-layout: fixed; }
.th-table-kisima thead th {
  font-weight: 700; font-size: 9px; text-transform: uppercase;
  padding: 2px 2px 4px; border-bottom: 1px dashed #111;
}
.th-table thead th.left { text-align: left; }
.th-table thead th.right { text-align: right; }
.th-table thead th.center { text-align: center; }
.th-table tbody td {
  padding: 3px 2px; vertical-align: top; font-size: 10px;
}
.th-table .idx { width: 14px; color: #444; }
.th-table .item-name { font-weight: 600; word-break: break-word; }
.th-table .num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
.th-table .qty { text-align: center; }

.th-totals .row {
  display: flex; justify-content: space-between;
  font-size: 10px; margin: 2px 0; padding: 0 2px;
}
.th-totals .row span:last-child { font-weight: 600; }
.th-totals .grand {
  font-size: 13px; font-weight: 800; margin-top: 3px;
}
.th-totals .grand span:last-child { font-size: 14px; }

.th-paid-banner {
  text-align: center;
  border: 1.5px solid #111;
  padding: 5px 6px;
  margin: 7px 0 4px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
}
.th-paid-banner.unpaid { border-style: dashed; }

.th-thanks {
  text-align: center; font-size: 10px; font-weight: 600;
  margin: 6px 0 2px;
}
.th-credit {
  text-align: center; font-size: 9px; margin: 0 0 2px; color: #333;
}
.th-notes-inline {
  font-size: 9px; text-align: center; margin-top: 4px; color: #333;
}

.mda-thermal.narrow .th-kisima-head .th-company { font-size: 12px; }
.mda-thermal.narrow .th-table { font-size: 9px; }
.mda-thermal.narrow .th-totals .grand { font-size: 12px; }
`;

/** Print-only — monospace for POS thermal rolls. */
export const THERMAL_RECEIPT_PRINT_CSS = `
.mda-thermal {
  font-family: 'Consolas', 'Courier New', monospace;
  color: #000;
  background: #fff;
  line-height: 1.3;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.mda-thermal * { box-sizing: border-box; }
.mda-thermal.kisima { font-size: 11px; padding: 0 2px; }
.th-kisima-head { text-align: center; margin-bottom: 4px; padding: 0 2px; }
.th-kisima-head .th-company {
  margin: 0; font-size: 15px; font-weight: 800;
  letter-spacing: 0.03em; text-transform: uppercase;
}
.th-brand-logo {
  display: block;
  max-width: 70px;
  max-height: 44px;
  width: auto;
  height: auto;
  margin: 0 auto 3px;
  object-fit: contain;
}
.th-tel { margin: 2px 0 0; font-size: 10px; }
.th-receipt-ref {
  text-align: center;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin: 3px 0 0;
}
.th-guide {
  border: 1.5px solid #000;
  padding: 4px 6px;
  margin: 5px 0 3px;
}
.th-guide-row {
  display: flex; justify-content: space-between; gap: 4px;
  font-size: 10px; font-weight: 700; margin: 1px 0;
}
.th-guide-row span:last-child { text-align: right; word-break: break-all; }
.th-sep {
  border: none; border-top: 1px dashed #000;
  margin: 5px 0; height: 0;
}
.th-sep-dbl {
  border-top: 2px solid #000;
  border-bottom: 1px solid #000;
  padding-bottom: 1px;
  margin: 6px 0;
  height: 0;
}
.th-meta .row {
  display: flex; justify-content: space-between; gap: 6px;
  font-size: 10px; margin: 1px 0; padding: 0 2px;
}
.th-meta .label { font-weight: 600; }
.th-meta .value { text-align: right; font-weight: 700; }
.th-table { width: 100%; border-collapse: collapse; font-size: 10px; table-layout: fixed; }
.th-table-kisima thead th {
  font-weight: 800; font-size: 9px; text-transform: uppercase;
  padding: 1px 2px 3px; border-bottom: 1px dashed #000;
}
.th-table thead th.left { text-align: left; }
.th-table thead th.right { text-align: right; }
.th-table thead th.center { text-align: center; }
.th-table tbody td { padding: 2px 2px; vertical-align: top; font-size: 10px; }
.th-table .idx { width: 14px; }
.th-table .item-name { font-weight: 600; word-break: break-word; overflow-wrap: anywhere; }
.th-table .num { text-align: right; white-space: nowrap; }
.th-table .qty { text-align: center; }
.th-totals .row {
  display: flex; justify-content: space-between;
  font-size: 10px; margin: 1px 0; padding: 0 2px;
}
.th-totals .row span:last-child { font-weight: 700; }
.th-totals .grand { font-size: 13px; font-weight: 800; margin-top: 2px; }
.th-totals .grand span:last-child { font-size: 14px; }
.th-paid-banner {
  text-align: center;
  border: 1.5px solid #000;
  padding: 4px 5px;
  margin: 6px 0 3px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.05em;
}
.th-paid-banner.unpaid { border-style: dashed; }
.th-thanks { text-align: center; font-size: 10px; font-weight: 700; margin: 5px 0 1px; }
.th-credit { text-align: center; font-size: 9px; margin: 0; }
.th-notes-inline { font-size: 9px; text-align: center; margin-top: 3px; }
.mda-thermal.narrow .th-kisima-head .th-company { font-size: 13px; }
.mda-thermal.narrow .th-table { font-size: 9px; }
body.thermal-58 .mda-thermal { font-size: 10px; }
`;
