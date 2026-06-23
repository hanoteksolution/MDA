import { MDA_BASE_DOCUMENT_CSS } from "./baseDocument";

/** Product list — unified base + catalog-specific styles. */
export const PRODUCT_LIST_CSS = MDA_BASE_DOCUMENT_CSS + `
.product-list-doc { font-size: 10.5px; }
.pl-table .sku { font-family: ui-monospace, monospace; font-size: 9px; color: #334155; }
.pl-table .product-cell { display: flex; align-items: center; gap: 8px; }
.pl-table .product-img {
  width: 32px; height: 32px; border-radius: 6px; object-fit: cover;
  border: 1px solid var(--mda-border); background: var(--mda-stripe); flex-shrink: 0;
}
.pl-table .product-img-ph {
  width: 32px; height: 32px; border-radius: 6px; background: #E2E8F0;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; color: var(--mda-muted); flex-shrink: 0;
}
.pl-table .product-name { font-weight: 600; color: #0F172A; font-size: 10px; }
.pl-badge {
  display: inline-block; padding: 2px 8px; border-radius: 999px;
  font-size: 8.5px; font-weight: 700; text-transform: capitalize;
}
.pl-badge.active { background: #DCFCE7; color: #15803D; }
.pl-badge.out_of_stock { background: #FEE2E2; color: #B91C1C; }
.pl-badge.inactive { background: #F1F5F9; color: #64748B; }
.pl-badge.low_stock { background: #FEF3C7; color: #B45309; }
.pl-cat-table { width: 100%; border-collapse: collapse; font-size: 9.5px; }
.pl-cat-table th {
  text-align: left; padding: 6px 4px; color: var(--mda-muted);
  font-weight: 600; border-bottom: 1px solid var(--mda-border);
  font-size: 8.5px; text-transform: uppercase; letter-spacing: 0.05em;
}
.pl-cat-table th.right, .pl-cat-table td.right { text-align: right; }
.pl-cat-table td { padding: 6px 4px; border-bottom: 1px solid #F1F5F9; }
.pl-cat-table tr.total td {
  font-weight: 800; border-top: 2px solid var(--mda-navy);
  border-bottom: none; padding-top: 8px; color: #0F172A;
}
.pl-chart-wrap { display: flex; align-items: center; gap: 16px; }
.pl-donut {
  width: 110px; height: 110px; border-radius: 50%; flex-shrink: 0; position: relative;
}
.pl-donut-hole {
  position: absolute; inset: 22px; background: #fff; border-radius: 50%;
}
.pl-legend { flex: 1; font-size: 9.5px; }
.pl-legend .item { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.pl-legend .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.pl-legend .lbl { flex: 1; color: #334155; }
.pl-legend .pct { font-weight: 700; color: #0F172A; }
`;
