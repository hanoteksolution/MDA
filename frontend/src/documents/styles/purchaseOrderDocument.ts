import { MDA_BASE_DOCUMENT_CSS } from "./baseDocument";

/** Purchase order — unified base + PO-specific blocks. */
export const PURCHASE_ORDER_CSS = MDA_BASE_DOCUMENT_CSS + `
.po-doc { font-size: 11px; line-height: 1.55; }
.po-mid {
  display: grid; grid-template-columns: 1fr 260px;
  gap: 16px; margin-top: 18px; align-items: start;
}
.po-totals-box {
  border: 1px solid var(--mda-border); border-radius: 8px;
  overflow: hidden; background: var(--mda-stripe);
}
.po-totals-body { padding: 12px 14px; }
.po-totals-body .row {
  display: flex; justify-content: space-between;
  padding: 5px 0; font-size: 10.5px; color: var(--mda-muted);
}
.po-totals-body .row span:last-child { font-weight: 600; color: #0F172A; }
.po-grand {
  background: var(--mda-navy); color: #fff;
  padding: 11px 14px; display: flex; justify-content: space-between; align-items: center;
}
.po-grand .label { font-size: 11px; font-weight: 700; }
.po-grand .value { font-size: 16px; font-weight: 800; }
.po-bottom {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 16px; margin-top: 16px; margin-bottom: 24px;
}
.po-side-box p, .po-side-box li {
  font-size: 10px; color: #475569; margin: 4px 0; line-height: 1.5;
}
.po-side-box ul { margin: 0; padding-left: 14px; }
.po-signature { display: flex; flex-direction: column; justify-content: flex-end; min-height: 100%; }
.po-signature .sig-label {
  margin: 0 0 8px; font-size: 10px; color: var(--mda-muted); text-align: center;
}
.po-signature .sig-line { border-top: 1px solid #94A3B8; margin-top: 40px; }
.po-table .item-name { font-weight: 600; color: #0F172A; }
`;
