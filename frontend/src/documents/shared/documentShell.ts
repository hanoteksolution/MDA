import type { DocumentBranding } from "../types";
import { esc } from "../utils";

export const LOGO_HEX = `
<svg class="mda-logo" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M26 3L45 14.5V37.5L26 49L7 37.5V14.5L26 3Z" fill="#001B3D"/>
  <path d="M26 9L39 17V35L26 43L13 35V17L26 9Z" fill="#2563EB"/>
  <text x="26" y="32" text-anchor="middle" fill="#fff" font-family="Inter,sans-serif" font-size="17" font-weight="800">M</text>
</svg>`;

export function contactIcon(type: "phone" | "email" | "web", color = "#fff"): string {
  const paths = {
    phone: '<path fill="' + color + '" d="M6.6 10.8c1.4 2.8 3.8 5.2 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C9.6 21 3 14.4 3 6c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1L6.6 10.8z"/>',
    email: '<path fill="' + color + '" d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4-8 5L4 8V6l8 5 8-5v2z"/>',
    web: '<path fill="' + color + '" d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm7.9 6H15.9c-.3-1.5-.8-2.9-1.4-4 2 .6 3.7 2 5.4 4z"/>',
  };
  return `<svg width="11" height="11" viewBox="0 0 24 24">${paths[type]}</svg>`;
}

export function renderMdaBrand(branding: DocumentBranding, logoClass = "mda-logo"): string {
  const company = branding.companyName.toUpperCase();
  const tagline = (branding.tagline ?? "ERP & POS SYSTEM").toUpperCase();
  const logo = LOGO_HEX.replace('class="mda-logo"', `class="${logoClass}"`);
  return `
    <div class="mda-brand">
      ${logo}
      <div>
        <h1 class="mda-company">${esc(company)}</h1>
        <p class="mda-tag">${esc(tagline)}</p>
      </div>
    </div>`;
}

export function renderMdaDocBadge(title: string, ref: string, metaHtml?: string): string {
  return `
    <div class="mda-doc-badge tr-doc-badge">
      <p class="title">${esc(title)}</p>
      <p class="number">${esc(ref)}</p>
      ${metaHtml ? `<div class="meta">${metaHtml}</div>` : ""}
    </div>`;
}

export function renderMdaHeader(
  branding: DocumentBranding,
  title: string,
  ref: string,
  metaRows?: { label: string; value: string }[]
): string {
  const metaTable = metaRows?.length
    ? `<table class="mda-meta-table" style="margin-top:10px;margin-left:auto"><tbody>${metaRows
        .map((r) => `<tr><td>${esc(r.label)} :</td><td>${esc(r.value)}</td></tr>`)
        .join("")}</tbody></table>`
    : "";

  return `
    <div class="mda-top">
      ${renderMdaBrand(branding)}
      <div style="text-align:right;min-width:200px">
        ${renderMdaDocBadge(title, ref)}
        ${metaTable}
      </div>
    </div>`;
}

export function renderMdaKpiGrid(
  kpis: { label: string; value: string; accent?: string; sub?: string; icon?: string }[],
  className = ""
): string {
  if (!kpis.length) return "";
  return `
    <div class="mda-kpi-grid tr-kpi-grid ${className}">
      ${kpis
        .map(
          (k) => `
        <div class="mda-kpi tr-kpi" style="--mda-kpi-accent:${k.accent ?? "#2563EB"}">
          ${k.icon ? `<div class="icon">${k.icon}</div>` : ""}
          <div class="label">${esc(k.label)}</div>
          <div class="value">${esc(k.value)}</div>
          ${k.sub ? `<div class="sub">${esc(k.sub)}</div>` : ""}
        </div>`
        )
        .join("")}
    </div>`;
}

export function renderMdaSectionLabel(text: string): string {
  return `<div class="mda-section-label">${esc(text)}</div>`;
}

export function renderMdaFooterBar(
  branding: DocumentBranding,
  title: string,
  options?: { thanks?: string; page?: string; center?: boolean }
): string {
  const contact = [branding.website, branding.email].filter(Boolean).join(" | ");
  if (options?.center || options?.thanks) {
    return `
      <footer class="mda-footer-bar pl-footer sr-footer">
        <span></span>
        <span class="thanks">${esc(options.thanks ?? "Thank you for using MDA Retail ERP & POS")}</span>
        <span class="page">${options.page ?? ""}</span>
      </footer>`;
  }
  return `
    <footer class="mda-footer-bar tr-footer">
      <span class="title">${esc(title)}</span>
      <span class="contact">${esc(contact)}</span>
    </footer>`;
}

export function renderMdaContactRow(branding: DocumentBranding, iconColor = "#94A3B8"): string {
  return `
    ${branding.phone ? `<span>${contactIcon("phone", iconColor)} ${esc(branding.phone)}</span>` : ""}
    ${branding.email ? `<span>${contactIcon("email", iconColor)} ${esc(branding.email)}</span>` : ""}
    ${branding.website ? `<span>${contactIcon("web", iconColor)} ${esc(branding.website)}</span>` : ""}`;
}
