import { resolveMediaUrl } from "@/config/api";
import { settingsApi } from "@/services/api/admin";
import type { DocumentBranding } from "./types";

let cached: DocumentBranding | null = null;

const DEFAULT_BRANDING: DocumentBranding = {
  companyName: "Your Company",
  legalName: "",
  tagline: "ERP & POS System",
  address: "",
  phone: "",
  email: "",
  website: "",
  taxId: "",
};

export async function getDocumentBranding(branch?: {
  name?: string;
  code?: string;
  address?: string;
  phone?: string;
}): Promise<DocumentBranding> {
  if (!cached) {
    try {
      const res = await settingsApi.company();
      const c = res.data;
      if (c) {
        cached = {
          companyName: c.name,
          legalName: c.legal_name || undefined,
          tagline: "ERP & POS System",
          address: c.address || DEFAULT_BRANDING.address,
          phone: c.phone || DEFAULT_BRANDING.phone,
          email: c.email || DEFAULT_BRANDING.email,
          website: DEFAULT_BRANDING.website,
          taxId: c.tax_id || undefined,
          logoUrl: resolveMediaUrl(c.logo),
        };
      } else {
        cached = { ...DEFAULT_BRANDING };
      }
    } catch {
      cached = { ...DEFAULT_BRANDING };
    }
  }

  return {
    ...cached,
    branchName: branch?.name ?? cached.branchName,
    branchCode: branch?.code ?? cached.branchCode,
    address: branch?.address || cached.address,
    phone: branch?.phone || cached.phone,
  };
}

export function brandingFromReceiptCompany(company: {
  name: string;
  legal_name?: string;
  address: string;
  phone: string;
  email?: string;
  tax_id?: string;
  logo?: string;
}, branch?: { name: string; code: string; address?: string; phone?: string }): DocumentBranding {
  return {
    companyName: company.name,
    legalName: company.legal_name,
    tagline: "ERP & POS System",
    branchName: branch?.name,
    branchCode: branch?.code,
    address: company.address || branch?.address || "",
    phone: company.phone || branch?.phone || "",
    email: company.email,
    website: "",
    taxId: company.tax_id,
    logoUrl: resolveMediaUrl(company.logo),
  };
}

export function clearBrandingCache() {
  cached = null;
}
