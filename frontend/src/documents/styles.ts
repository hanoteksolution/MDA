import { DOC } from "./tokens";

export const A4_PRINT_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.mda-doc {
  font-family: ${DOC.font};
  color: ${DOC.primary};
  background: ${DOC.bg};
  font-size: 11px;
  line-height: 1.5;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.mda-doc * { box-sizing: border-box; }

.mda-doc-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 32px 22px;
  background: linear-gradient(135deg, ${DOC.primary} 0%, ${DOC.secondary} 100%);
  color: #fff;
  border-radius: 0 0 20px 20px;
  position: relative;
  overflow: hidden;
}
.mda-doc-header::after {
  content: "";
  position: absolute;
  right: -40px;
  top: -40px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: rgba(37,99,235,0.15);
}
.mda-brand { display: flex; gap: 16px; align-items: flex-start; position: relative; z-index: 1; }
.mda-logo {
  width: 52px; height: 52px; border-radius: 14px;
  background: rgba(255,255,255,0.12);
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 22px; color: #fff;
  border: 1px solid rgba(255,255,255,0.2);
  overflow: hidden;
}
.mda-logo img { width: 100%; height: 100%; object-fit: contain; }
.mda-brand h1 { margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.02em; }
.mda-brand .tagline { margin: 2px 0 0; font-size: 10px; opacity: 0.75; letter-spacing: 0.12em; text-transform: uppercase; }
.mda-brand .meta-line { margin: 2px 0 0; font-size: 10px; opacity: 0.85; }
.mda-doc-meta { text-align: right; position: relative; z-index: 1; min-width: 200px; }
.mda-doc-title { margin: 0; font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; opacity: 0.7; }
.mda-doc-number {
  display: inline-block; margin-top: 6px; padding: 6px 14px;
  background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
  border-radius: 999px; font-size: 13px; font-weight: 700; font-family: ui-monospace, monospace;
}
.mda-meta-grid { margin-top: 12px; font-size: 10px; opacity: 0.9; }
.mda-meta-grid div { margin-top: 3px; }
.mda-status-badge {
  display: inline-block; margin-top: 10px; padding: 5px 12px;
  border-radius: 999px; font-size: 10px; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase;
}
.mda-header-codes { margin-top: 10px; display: flex; gap: 8px; justify-content: flex-end; align-items: center; }
.mda-header-codes img { background: #fff; border-radius: 6px; padding: 2px; }

.mda-doc-body { padding: 24px 32px 8px; }

.mda-parties { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.mda-party {
  background: ${DOC.card}; border: 1px solid ${DOC.border};
  border-radius: 14px; padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(15,23,42,0.04);
}
.mda-party h3 {
  margin: 0 0 8px; font-size: 9px; font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase; color: ${DOC.muted};
}
.mda-party .name { font-size: 14px; font-weight: 700; margin-bottom: 4px; }
.mda-party .line { font-size: 10px; color: ${DOC.muted}; margin-top: 2px; }

.mda-kpi-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
  margin-bottom: 20px;
}
.mda-kpi {
  background: ${DOC.card}; border: 1px solid ${DOC.border};
  border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 4px 14px rgba(15,23,42,0.05);
  position: relative; overflow: hidden;
}
.mda-kpi::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: var(--kpi-accent, ${DOC.accent});
}
.mda-kpi .label { font-size: 9px; font-weight: 600; color: ${DOC.muted}; text-transform: uppercase; letter-spacing: 0.08em; }
.mda-kpi .value { margin-top: 6px; font-size: 18px; font-weight: 800; letter-spacing: -0.02em; }

.mda-table-wrap {
  background: ${DOC.card}; border: 1px solid ${DOC.border};
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 4px 18px rgba(15,23,42,0.05);
  margin-bottom: 20px;
}
.mda-table { width: 100%; border-collapse: collapse; font-size: 10px; }
.mda-table thead th {
  background: linear-gradient(180deg, ${DOC.primary} 0%, ${DOC.secondary} 100%);
  color: #fff; padding: 12px 14px; text-align: left;
  font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
}
.mda-table thead th.center { text-align: center; }
.mda-table thead th.right { text-align: right; }
.mda-table tbody td { padding: 12px 14px; border-bottom: 1px solid ${DOC.border}; vertical-align: top; }
.mda-table tbody tr:nth-child(even) td { background: #FAFBFC; }
.mda-table tbody tr:last-child td { border-bottom: none; }
.mda-table .item-name { font-weight: 700; font-size: 11px; color: ${DOC.primary}; }
.mda-table .item-sub { font-size: 9px; color: ${DOC.muted}; margin-top: 3px; }
.mda-table .item-img {
  width: 36px; height: 36px; border-radius: 8px; object-fit: cover;
  border: 1px solid ${DOC.border}; background: ${DOC.bg};
}
.mda-table .cell-badge {
  display: inline-block; padding: 3px 8px; border-radius: 999px;
  font-size: 8px; font-weight: 700; text-transform: uppercase;
}

.mda-bottom { display: grid; grid-template-columns: 1fr 300px; gap: 20px; margin-bottom: 20px; }
.mda-analytics {
  background: ${DOC.card}; border: 1px solid ${DOC.border};
  border-radius: 14px; padding: 16px 18px;
}
.mda-analytics h4 { margin: 0 0 12px; font-size: 11px; font-weight: 700; }
.mda-analytics-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-bottom: 1px dashed ${DOC.border}; font-size: 10px;
}
.mda-analytics-row:last-child { border-bottom: none; }

.mda-financial {
  background: ${DOC.card}; border: 1px solid ${DOC.border};
  border-radius: 16px; padding: 18px 20px;
  box-shadow: 0 8px 24px rgba(15,23,42,0.06);
}
.mda-financial .row {
  display: flex; justify-content: space-between; padding: 6px 0;
  font-size: 10px; color: ${DOC.muted};
}
.mda-financial .row strong { color: ${DOC.primary}; font-weight: 600; }
.mda-financial .grand {
  margin-top: 10px; padding-top: 12px; border-top: 2px solid ${DOC.primary};
  display: flex; justify-content: space-between; align-items: baseline;
}
.mda-financial .grand span:first-child { font-size: 12px; font-weight: 800; color: ${DOC.primary}; }
.mda-financial .grand span:last-child {
  font-size: 22px; font-weight: 800; color: ${DOC.accent}; letter-spacing: -0.03em;
}
.mda-financial .row.highlight strong { color: ${DOC.success}; }

.mda-notes {
  background: #F1F5F9; border-radius: 12px; padding: 14px 16px;
  font-size: 10px; color: ${DOC.muted}; margin-bottom: 16px;
}
.mda-notes strong { color: ${DOC.primary}; display: block; margin-bottom: 4px; }

.mda-signatures {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
  margin: 20px 0;
}
.mda-signature {
  border: 1px dashed ${DOC.border}; border-radius: 12px;
  padding: 14px; min-height: 80px; background: ${DOC.card};
}
.mda-signature .label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: ${DOC.muted}; }
.mda-signature .line { margin-top: 36px; border-top: 1px solid ${DOC.border}; padding-top: 6px; font-size: 10px; }

.mda-doc-footer {
  margin-top: 8px; padding: 18px 32px;
  background: linear-gradient(135deg, ${DOC.primary} 0%, ${DOC.secondary} 100%);
  color: rgba(255,255,255,0.9); font-size: 9px;
  display: flex; justify-content: space-between; align-items: center; gap: 16px;
}
.mda-doc-footer .thanks { font-size: 11px; font-weight: 700; color: #fff; }
.mda-doc-footer .confidential { opacity: 0.65; font-style: italic; margin-top: 4px; }
.mda-watermark {
  position: fixed; top: 40%; left: 50%; transform: translate(-50%,-50%) rotate(-24deg);
  font-size: 72px; font-weight: 800; color: rgba(15,23,42,0.04);
  pointer-events: none; z-index: 0; letter-spacing: 0.2em;
}

@media print {
  .mda-doc { background: #fff; }
  .mda-doc-header { border-radius: 0; }
}
`;

export { THERMAL_RECEIPT_CSS as THERMAL_PRINT_CSS } from "./styles/thermalReceipt";

export { MDA_BASE_DOCUMENT_CSS } from "./styles/baseDocument";
export { SALES_DOCUMENT_CSS } from "./styles/salesDocument";
export { PRODUCT_LIST_CSS } from "./styles/productListDocument";
export { SALES_REPORT_CSS } from "./styles/salesReportDocument";
export { PURCHASE_ORDER_CSS } from "./styles/purchaseOrderDocument";
export { DELIVERY_NOTE_CSS } from "./styles/deliveryNoteDocument";
export { TABLE_REPORT_CSS } from "./styles/tableReportDocument";
export { CUSTOMER_REPORT_CSS } from "./styles/customerReportDocument";
