/** Screen preview — includes web font. */
export const THERMAL_RECEIPT_CSS = `
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

.mda-thermal {
  font-family: 'IBM Plex Mono', 'Consolas', 'Courier New', monospace;
  color: #111;
  background: #fff;
  font-size: 11px;
  line-height: 1.22;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.mda-thermal * { box-sizing: border-box; }

/* Compact roll — no wasted margins */
.mda-thermal.kisima,
.mda-thermal.compact {
  font-size: 10.5px;
  padding: 0;
  margin: 0;
  width: 100%;
}

.th-kisima-head {
  text-align: center;
  margin: 0 0 2px;
  padding: 0;
}
.th-kisima-head .th-company {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.02em;
  line-height: 1.15;
}
.th-brand-logo {
  display: block;
  max-width: 56px;
  max-height: 36px;
  width: auto;
  height: auto;
  margin: 0 auto 2px;
  object-fit: contain;
}
.th-address {
  margin: 1px 0 0;
  font-size: 9.5px;
  font-weight: 500;
  line-height: 1.2;
  color: #111;
}
.th-tel { margin: 1px 0 0; font-size: 9.5px; }

/* Merchants under header — centered like company name */
.th-merchants {
  margin: 3px 0 2px;
  padding: 0;
  text-align: center;
}
.th-merchant-row {
  font-size: 10px;
  font-weight: 600;
  line-height: 1.25;
  margin: 0;
  word-break: break-all;
  text-align: center;
}
.th-merchant-row .m-label { font-weight: 700; }
.th-merchant-row .m-code { font-weight: 700; }

.th-sep {
  border: none;
  border-top: 1px solid #111;
  margin: 3px 0;
  height: 0;
}
.th-sep-dbl {
  border-top: 1px solid #111;
  border-bottom: none;
  margin: 3px 0;
  height: 0;
  padding: 0;
}

.th-meta .row {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  font-size: 10px;
  margin: 0;
  padding: 0;
  line-height: 1.25;
}
.th-meta .label { font-weight: 600; }
.th-meta .value { text-align: right; font-weight: 700; }

/* Products — NO cell / grid borders */
.th-table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  font-size: 10px;
  table-layout: fixed;
  border: none !important;
}
.th-table-kisima thead th {
  font-weight: 700;
  font-size: 9px;
  text-transform: none;
  padding: 1px 1px 2px;
  border: none !important;
  border-bottom: 1px solid #111 !important;
}
.th-table thead th.left { text-align: left; }
.th-table thead th.right { text-align: right; }
.th-table thead th.center { text-align: center; width: 28px; }
.th-table tbody td {
  padding: 1px 1px;
  vertical-align: top;
  font-size: 10px;
  border: none !important;
  line-height: 1.22;
}
.th-table .item-name {
  font-weight: 600;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.th-table .num {
  text-align: right;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  width: 44px;
}
.th-table .qty {
  text-align: center;
  width: 28px;
}

.th-totals .row {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  margin: 0;
  padding: 0;
  line-height: 1.25;
}
.th-totals .row span:last-child { font-weight: 700; }
.th-totals .grand {
  font-size: 12px;
  font-weight: 800;
  margin-top: 1px;
}
.th-totals .grand span:last-child { font-size: 12px; }

.th-footer-block {
  text-align: center;
  margin: 2px 0 0;
  padding: 0;
}
.th-contact {
  margin: 0;
  font-size: 9.5px;
  font-weight: 600;
  line-height: 1.2;
}
.th-thanks {
  text-align: center;
  font-size: 10px;
  font-weight: 600;
  margin: 2px 0 0;
  line-height: 1.2;
}
.th-credit {
  text-align: center;
  font-size: 9px;
  margin: 0;
}
.th-notes-inline {
  font-size: 9px;
  text-align: center;
  margin: 2px 0 0;
  color: #333;
}
.th-receipt-ref { display: none; }
.th-paid-banner { display: none; }
.th-guide { display: none; }

.mda-thermal.narrow .th-kisima-head .th-company { font-size: 13px; }
.mda-thermal.narrow .th-table { font-size: 9px; }
.mda-thermal.narrow .th-totals .grand { font-size: 11px; }
`;

/** Print-only — monospace for POS thermal rolls. */
export const THERMAL_RECEIPT_PRINT_CSS = `
.mda-thermal {
  font-family: 'Consolas', 'Courier New', monospace;
  color: #000;
  background: #fff;
  line-height: 1.18;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.mda-thermal * { box-sizing: border-box; }
.mda-thermal.kisima,
.mda-thermal.compact { font-size: 11px; padding: 0; margin: 0; width: 100%; }
.th-kisima-head { text-align: center; margin: 0 0 1px; padding: 0; }
.th-kisima-head .th-company {
  margin: 0; font-size: 15px; font-weight: 800;
  letter-spacing: 0.02em; line-height: 1.1;
}
.th-brand-logo {
  display: block; max-width: 52px; max-height: 32px;
  width: auto; height: auto; margin: 0 auto 1px; object-fit: contain;
}
.th-address { margin: 1px 0 0; font-size: 10px; font-weight: 600; line-height: 1.15; }
.th-merchants { margin: 2px 0 1px; padding: 0; text-align: center; }
.th-merchant-row {
  font-size: 10px; font-weight: 700; line-height: 1.2; margin: 0; word-break: break-all; text-align: center;
}
.th-sep {
  border: none; border-top: 1px solid #000; margin: 2px 0; height: 0;
}
.th-meta .row {
  display: flex; justify-content: space-between; gap: 4px;
  font-size: 10px; margin: 0; padding: 0; line-height: 1.2;
}
.th-meta .label { font-weight: 700; }
.th-meta .value { text-align: right; font-weight: 700; }
.th-table {
  width: 100%; border-collapse: collapse; border-spacing: 0;
  font-size: 10px; table-layout: fixed; border: none !important;
}
.th-table-kisima thead th {
  font-weight: 800; font-size: 9px; text-transform: none;
  padding: 0 1px 1px; border: none !important; border-bottom: 1px solid #000 !important;
}
.th-table thead th.left { text-align: left; }
.th-table thead th.right { text-align: right; }
.th-table thead th.center { text-align: center; width: 26px; }
.th-table tbody td {
  padding: 0 1px; vertical-align: top; font-size: 10px;
  border: none !important; line-height: 1.18;
}
.th-table .item-name { font-weight: 700; word-break: break-word; overflow-wrap: anywhere; }
.th-table .num { text-align: right; white-space: nowrap; width: 42px; }
.th-table .qty { text-align: center; width: 26px; }
.th-totals .row {
  display: flex; justify-content: space-between;
  font-size: 10px; margin: 0; padding: 0; line-height: 1.2;
}
.th-totals .row span:last-child { font-weight: 700; }
.th-totals .grand { font-size: 12px; font-weight: 800; margin-top: 1px; }
.th-totals .grand span:last-child { font-size: 12px; }
.th-footer-block { text-align: center; margin: 1px 0 0; padding: 0; }
.th-contact { margin: 0; font-size: 10px; font-weight: 700; line-height: 1.15; }
.th-thanks { text-align: center; font-size: 10px; font-weight: 700; margin: 1px 0 0; }
.th-notes-inline { font-size: 9px; text-align: center; margin-top: 1px; }
.th-receipt-ref, .th-paid-banner, .th-guide { display: none; }
.mda-thermal.narrow .th-kisima-head .th-company { font-size: 13px; }
.mda-thermal.narrow .th-table { font-size: 9px; }
body.thermal-58 .mda-thermal { font-size: 10px; }
`;
