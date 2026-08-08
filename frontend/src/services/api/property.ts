import type { ApiListResponse } from "@/types/models/catalog";
import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface PropertySummary {
  properties: number;
  buildings: number;
  units: number;
  units_vacant: number;
  units_occupied: number;
  units_maintenance: number;
  owners: number;
  maintenance_open: number;
  documents: number;
}

export interface PropertyOwner {
  id: string;
  branch_id: string | null;
  full_name: string;
  phone: string;
  email: string;
  notes: string;
  is_active: boolean;
}

export interface PropertyAsset {
  id: string;
  branch_id: string;
  branch_name: string;
  owner_id: string | null;
  owner_name: string;
  name: string;
  code: string;
  kind: string;
  address: string;
  city: string;
  notes: string;
  is_active: boolean;
}

export interface PropertyBuilding {
  id: string;
  branch_id: string;
  property_id: string;
  property_name: string;
  name: string;
  code: string;
  floors: number;
  notes: string;
  is_active: boolean;
}

export interface PropertyUnit {
  id: string;
  branch_id: string;
  building_id: string;
  building_name: string;
  property_id: string | null;
  property_name: string;
  code: string;
  label: string;
  floor: string;
  kind: string;
  status: string;
  bedrooms: number;
  bathrooms: number;
  area_sqm: number | null;
  rent_amount: number;
  deposit_amount: number;
  notes: string;
  is_active: boolean;
}

export interface MaintenanceTicket {
  id: string;
  branch_id: string;
  unit_id: string;
  unit_code: string;
  building_name: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  reported_by: string;
  completed_at: string | null;
  created_at: string | null;
}

export const propertyApi = {
  summary: (branchId?: string) =>
    apiRequest<ApiResponse<PropertySummary>>(
      `/property/summary/${qs({ branch_id: branchId })}`
    ),

  owners: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<PropertyOwner>>(
      `/property/owners/${qs({ page, branch_id: branchId })}`
    ),

  createOwner: (data: { full_name: string; branch_id?: string; phone?: string; email?: string }) =>
    apiRequest<ApiResponse<PropertyOwner>>("/property/owners/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  properties: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<PropertyAsset>>(
      `/property/properties/${qs({ page, branch_id: branchId })}`
    ),

  createProperty: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<PropertyAsset>>("/property/properties/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  buildings: (page = 1, branchId?: string, propertyId?: string) =>
    apiRequest<ApiListResponse<PropertyBuilding>>(
      `/property/buildings/${qs({ page, branch_id: branchId, property_id: propertyId })}`
    ),

  createBuilding: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<PropertyBuilding>>("/property/buildings/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  units: (page = 1, branchId?: string, status?: string) =>
    apiRequest<ApiListResponse<PropertyUnit>>(
      `/property/units/${qs({ page, branch_id: branchId, status })}`
    ),

  createUnit: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<PropertyUnit>>("/property/units/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  setUnitStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<PropertyUnit>>(`/property/units/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  maintenance: (page = 1, branchId?: string, status?: string) =>
    apiRequest<ApiListResponse<MaintenanceTicket>>(
      `/property/maintenance/${qs({ page, branch_id: branchId, status })}`
    ),

  createMaintenance: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<MaintenanceTicket>>("/property/maintenance/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateMaintenanceStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<MaintenanceTicket>>(`/property/maintenance/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
};
