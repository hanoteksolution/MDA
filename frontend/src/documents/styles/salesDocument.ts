import { MDA_BASE_DOCUMENT_CSS } from "./baseDocument";

/** Invoice & quotation — unified base + sales-specific blocks. */
export const SALES_DOCUMENT_CSS = MDA_BASE_DOCUMENT_CSS + `
:root {
  --sd-navy: var(--mda-navy);
  --sd-blue: var(--mda-blue);
  --sd-green: #2E9D62;
  --sd-muted: var(--mda-muted);
  --sd-border: var(--mda-border);
  --sd-stripe: var(--mda-stripe);
}
.sales-doc { font-size: 11px; line-height: 1.55; padding-bottom: 24px; }
.sd-doc-badge.quote .number {
  background: transparent; color: rgba(255,255,255,0.92);
  padding: 4px 0 0;
}
.sd-doc-badge.quote .title { padding-bottom: 12px; }
.sd-doc-badge.quote .number-wrap {
  background: var(--sd-navy); border-radius: 0 0 10px 10px;
  margin-top: -10px; padding: 0 20px 10px;
}
.sd-meta-table { border-collapse: collapse; }
.sd-table .item-name { font-weight: 600; color: #0F172A; font-size: 10.5px; }
.sd-table .item-sku { font-size: 9px; color: #94A3B8; margin-top: 2px; }

/* ── Bottom section ── */
.sd-bottom {
  display: grid; grid-template-columns: 1fr 260px;
  gap: 20px; margin-top: 18px; align-items: start;
}
.sd-side-box {
  background: var(--sd-stripe); border: 1px solid var(--sd-border);
  border-radius: 8px; padding: 14px 16px;
}
.sd-side-box h4 {
  margin: 0 0 8px; font-size: 11px; font-weight: 700; color: var(--sd-navy);
}
.sd-side-box p, .sd-side-box li {
  font-size: 10px; color: #475569; margin: 3px 0; line-height: 1.5;
}
.sd-side-box ul { margin: 0; padding-left: 14px; }
.sd-side-box strong { color: #0F172A; font-weight: 700; }
.sd-pay-block { margin-bottom: 10px; }
.sd-pay-block:last-child { margin-bottom: 0; }
.sd-amount-words { margin-top: 14px; }
.sd-amount-words .label {
  font-size: 10.5px; font-weight: 700; color: var(--sd-blue); margin-bottom: 4px;
}
.sd-amount-words .value { font-size: 10px; color: #475569; line-height: 1.5; }

.sd-totals { font-size: 10.5px; padding-top: 4px; }
.sd-totals .row {
  display: flex; justify-content: space-between;
  padding: 5px 0; color: var(--sd-muted);
}
.sd-totals .row span:last-child { font-weight: 600; color: #0F172A; }
.sd-grand {
  margin-top: 8px; border-radius: 8px; padding: 11px 14px;
  display: flex; justify-content: space-between; align-items: center;
}
.sd-grand.invoice { background: var(--sd-navy); }
.sd-grand.quotation { background: var(--sd-green); }
.sd-grand .label { font-size: 11px; font-weight: 700; color: #fff; }
.sd-grand .value { font-size: 18px; font-weight: 800; color: #fff; letter-spacing: -0.02em; }

/* ── Footer ── */
.sd-footer {
  margin-top: 28px; padding-top: 18px;
  border-top: 1px solid var(--sd-border);
  display: grid; grid-template-columns: 1fr 1.4fr 72px;
  gap: 16px; align-items: end;
}
.sd-signature .line {
  border-top: 1px solid #94A3B8; padding-top: 5px;
  font-size: 9.5px; color: var(--sd-muted); text-align: center; margin-top: 36px;
}
.sd-signature .sign-img {
  font-family: 'Segoe Script', 'Brush Script MT', cursive; font-size: 16px;
  color: #1E293B; text-align: center; margin-bottom: -28px;
}
.sd-footer-center { text-align: center; }
.sd-footer-center .thanks {
  font-size: 11px; font-weight: 700; color: var(--sd-navy); margin-bottom: 8px;
}
.sd-contact-row {
  display: flex; justify-content: center; gap: 16px;
  font-size: 9.5px; color: var(--sd-muted); flex-wrap: wrap;
}
.sd-contact-row span { display: inline-flex; align-items: center; gap: 4px; }
.sd-qr { text-align: right; }
.sd-qr img { width: 68px; height: 68px; border-radius: 4px; border: 1px solid var(--sd-border); }

.sd-signatures-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 48px;
  margin-top: 24px;
}
.sd-signatures-row .sd-signature .line { margin-top: 44px; }
.sd-quote-footer {
  margin-top: 16px; padding-top: 14px;
  border-top: 1px solid var(--sd-border);
  display: flex; justify-content: space-between; align-items: flex-end;
}
.sd-quote-footer .sd-contact-row { justify-content: flex-start; }

@media print {
  .sales-doc { padding: 20px 28px; width: 100%; }
  body { margin: 0; background: #fff; }
}
`;
