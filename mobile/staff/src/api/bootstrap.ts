import { apiRequest } from "./client";

export interface MobileNavScreen {
  id: string;
  label: string;
  route: string;
  workspace: string;
  module: string;
  sort_order: number;
}

export interface MobileNavWorkspace {
  id: string;
  label: string;
  module: string;
  audience: string;
  screens: MobileNavScreen[];
}

export interface MobileNav {
  enabled_modules: string[];
  audience?: string;
  workspaces: MobileNavWorkspace[];
  screens: MobileNavScreen[];
}

export interface MobileBootstrap {
  user?: { username?: string; enabled_modules?: string[] };
  enabled_modules?: string[];
  mobile_nav?: MobileNav;
  entitlements?: { phase?: string; can_write?: boolean } | null;
}

export function fetchStaffBootstrap() {
  return apiRequest<MobileBootstrap>("/mobile/bootstrap/?audience=staff");
}

export function fetchGymSummary() {
  return apiRequest<Record<string, unknown>>("/gym/summary/");
}

export function fetchPharmacySummary() {
  return apiRequest<Record<string, unknown>>("/pharmacy/summary/");
}

export function fetchHotelSummary() {
  return apiRequest<Record<string, unknown>>("/hotel/summary/");
}

export function fetchRestaurantSummary() {
  return apiRequest<Record<string, unknown>>("/restaurant/summary/");
}

export function fetchPropertySummary() {
  return apiRequest<Record<string, unknown>>("/property/summary/");
}

export function fetchHousingSummary() {
  return apiRequest<Record<string, unknown>>("/housing/summary/");
}

export function fetchOfficeSummary() {
  return apiRequest<Record<string, unknown>>("/office/summary/");
}
