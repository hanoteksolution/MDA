import { MDA_BASE_DOCUMENT_CSS } from "./baseDocument";

/** Delivery note — unified base + DN-specific blocks. */
export const DELIVERY_NOTE_CSS = MDA_BASE_DOCUMENT_CSS + `
.dn-doc { font-size: 11px; line-height: 1.55; padding-bottom: 0; }
.dn-table tbody td { background: #fff; }
.dn-table .item-name { font-weight: 600; color: #0F172A; }
.dn-table .unit { text-align: right; color: var(--mda-muted); }
.dn-received-box {
  margin-top: 18px;
  border: 1px solid var(--mda-border); border-radius: 8px;
  padding: 16px 18px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: center;
}
.dn-received-box h4 {
  margin: 0 0 12px; font-size: 11px; font-weight: 700; color: #0F172A;
}
.dn-field {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 10px; margin-bottom: 10px;
}
.dn-field .label { font-weight: 600; color: #334155; white-space: nowrap; }
.dn-field .dots {
  flex: 1; border-bottom: 1px dotted #94A3B8; min-height: 14px;
}
.dn-thanks {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; gap: 10px;
}
.dn-thanks .truck { width: 56px; height: 56px; }
.dn-thanks p {
  margin: 0; font-size: 13px; font-weight: 700; color: var(--mda-blue);
}
`;
