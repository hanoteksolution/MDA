import type { ApiListResponse } from "@/types/models/catalog";
import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface TravelSummary { total_bookings: number; draft_bookings: number; confirmed_bookings: number; completed_bookings: number; total_revenue: number; paid_amount: number; outstanding_amount: number; travelers: number; pending_visas: number; }
export interface TravelMobileSummary { todays_bookings: number; open_visas: number; pending_commissions: number; }
export interface TravelRecord { id: string; status?: string; name?: string; code?: string; booking_code?: string; full_name?: string; [key: string]: unknown; }
export interface TravelDestination extends TravelRecord { country: string; city: string; name: string; code: string; }
export interface TravelPackage extends TravelRecord { name: string; code: string; }
export interface Traveler extends TravelRecord { full_name: string; }
export interface TravelBooking extends TravelRecord { booking_code: string; }
export interface VisaApplication extends TravelRecord { visa_type?: string; }
export interface TravelQuotation extends TravelRecord { quote_number: string; total_amount: number; }

const list = <T>(resource: string, page = 1, branchId?: string, status?: string, search?: string) => apiRequest<ApiListResponse<T>>(`/travel/${resource}/${qs({ page, branch_id: branchId, status, search })}`);
const detail = <T>(resource: string, id: string) => apiRequest<ApiResponse<T>>(`/travel/${resource}/${id}/`);
const create = <T>(resource: string, data: Record<string, unknown>) => apiRequest<ApiResponse<T>>(`/travel/${resource}/`, { method: "POST", body: JSON.stringify(data) });
const update = <T>(resource: string, id: string, data: Record<string, unknown>) => apiRequest<ApiResponse<T>>(`/travel/${resource}/${id}/`, { method: "PATCH", body: JSON.stringify(data) });

export const travelApi = {
  summary: (branchId?: string) => apiRequest<ApiResponse<TravelSummary>>(`/travel/summary/${qs({ branch_id: branchId })}`),
  destinations: (page = 1, search?: string) => list<TravelDestination>("destinations", page, undefined, undefined, search),
  destination: (id: string) => detail<TravelDestination>("destinations", id),
  createDestination: (data: Record<string, unknown>) => create<TravelDestination>("destinations", data),
  updateDestination: (id: string, data: Record<string, unknown>) => update<TravelDestination>("destinations", id, data),
  packages: (page = 1, search?: string) => list<TravelPackage>("packages", page, undefined, undefined, search),
  package: (id: string) => detail<TravelPackage>("packages", id),
  createPackage: (data: Record<string, unknown>) => create<TravelPackage>("packages", data),
  updatePackage: (id: string, data: Record<string, unknown>) => update<TravelPackage>("packages", id, data),
  travelers: (page = 1, search?: string) => list<Traveler>("travelers", page, undefined, undefined, search),
  traveler: (id: string) => detail<Traveler>("travelers", id),
  createTraveler: (data: Record<string, unknown>) => create<Traveler>("travelers", data),
  updateTraveler: (id: string, data: Record<string, unknown>) => update<Traveler>("travelers", id, data),
  bookings: (page = 1, branchId?: string, status?: string) => list<TravelBooking>("bookings", page, branchId, status),
  booking: (id: string) => detail<TravelBooking>("bookings", id),
  createBooking: (data: Record<string, unknown>) => create<TravelBooking>("bookings", data),
  updateBooking: (id: string, data: Record<string, unknown>) => update<TravelBooking>("bookings", id, data),
  setBookingStatus: (id: string, status: string) => apiRequest<ApiResponse<TravelBooking>>(`/travel/bookings/${id}/status/`, { method: "POST", body: JSON.stringify({ status }) }),
  visas: (page = 1, search?: string) => list<VisaApplication>("visas", page, undefined, undefined, search),
  visa: (id: string) => detail<VisaApplication>("visas", id),
  createVisa: (data: Record<string, unknown>) => create<VisaApplication>("visas", data),
  updateVisa: (id: string, data: Record<string, unknown>) => update<VisaApplication>("visas", id, data),
  insurance: (page = 1, search?: string) => list<TravelRecord>("insurance", page, undefined, undefined, search),
  insurancePolicy: (id: string) => detail<TravelRecord>("insurance", id),
  createInsurance: (data: Record<string, unknown>) => create<TravelRecord>("insurance", data),
  updateInsurance: (id: string, data: Record<string, unknown>) => update<TravelRecord>("insurance", id, data),
  vehicles: (page = 1, search?: string) => list<TravelRecord>("vehicles", page, undefined, undefined, search),
  vehicle: (id: string) => detail<TravelRecord>("vehicles", id),
  createVehicle: (data: Record<string, unknown>) => create<TravelRecord>("vehicles", data),
  updateVehicle: (id: string, data: Record<string, unknown>) => update<TravelRecord>("vehicles", id, data),
  drivers: (page = 1, search?: string) => list<TravelRecord>("drivers", page, undefined, undefined, search),
  driver: (id: string) => detail<TravelRecord>("drivers", id),
  createDriver: (data: Record<string, unknown>) => create<TravelRecord>("drivers", data),
  updateDriver: (id: string, data: Record<string, unknown>) => update<TravelRecord>("drivers", id, data),
  transfers: (page = 1, search?: string) => list<TravelRecord>("transfers", page, undefined, undefined, search),
  transfer: (id: string) => detail<TravelRecord>("transfers", id),
  createTransfer: (data: Record<string, unknown>) => create<TravelRecord>("transfers", data),
  updateTransfer: (id: string, data: Record<string, unknown>) => update<TravelRecord>("transfers", id, data),
  itineraries: (page = 1, search?: string) => list<TravelRecord>("itineraries", page, undefined, undefined, search),
  itinerary: (id: string) => detail<TravelRecord>("itineraries", id),
  createItinerary: (data: Record<string, unknown>) => create<TravelRecord>("itineraries", data),
  updateItinerary: (id: string, data: Record<string, unknown>) => update<TravelRecord>("itineraries", id, data),
  activities: (page = 1, search?: string) => list<TravelRecord>("activities", page, undefined, undefined, search),
  activity: (id: string) => detail<TravelRecord>("activities", id),
  createActivity: (data: Record<string, unknown>) => create<TravelRecord>("activities", data),
  updateActivity: (id: string, data: Record<string, unknown>) => update<TravelRecord>("activities", id, data),
  quotations: (page = 1, search?: string) => list<TravelQuotation>("quotations", page, undefined, undefined, search),
  quotation: (id: string) => detail<TravelQuotation>("quotations", id),
  createQuotation: (data: Record<string, unknown>) => create<TravelQuotation>("quotations", data),
  updateQuotation: (id: string, data: Record<string, unknown>) => update<TravelQuotation>("quotations", id, data),
  setQuotationStatus: (id: string, status: string) => apiRequest<ApiResponse<TravelQuotation>>(`/travel/quotations/${id}/status/`, { method: "POST", body: JSON.stringify({ status }) }),
  convertQuotation: (id: string) => apiRequest<ApiResponse<TravelBooking>>(`/travel/quotations/${id}/convert/`, { method: "POST" }),
  documents: (page = 1, search?: string) => list<TravelRecord>("documents", page, undefined, undefined, search),
  document: (id: string) => detail<TravelRecord>("documents", id),
  createDocument: (data: Record<string, unknown>) => create<TravelRecord>("documents", data),
  updateDocument: (id: string, data: Record<string, unknown>) => update<TravelRecord>("documents", id, data),
  payments: (page = 1, search?: string) => list<TravelRecord>("payments", page, undefined, undefined, search),
  payment: (id: string) => detail<TravelRecord>("payments", id),
  createPayment: (data: Record<string, unknown>) => create<TravelRecord>("payments", data),
  updatePayment: (id: string, data: Record<string, unknown>) => update<TravelRecord>("payments", id, data),
  postPaymentAccounting: (id: string) => apiRequest<ApiResponse<TravelRecord>>(`/travel/payments/${id}/post-accounting/`, { method: "POST" }),
  refunds: (page = 1, search?: string) => list<TravelRecord>("refunds", page, undefined, undefined, search),
  refund: (id: string) => detail<TravelRecord>("refunds", id),
  createRefund: (data: Record<string, unknown>) => create<TravelRecord>("refunds", data),
  updateRefund: (id: string, data: Record<string, unknown>) => update<TravelRecord>("refunds", id, data),
  postRefundAccounting: (id: string) => apiRequest<ApiResponse<TravelRecord>>(`/travel/refunds/${id}/post-accounting/`, { method: "POST" }),
  expenses: (page = 1, search?: string) => list<TravelRecord>("expenses", page, undefined, undefined, search),
  expense: (id: string) => detail<TravelRecord>("expenses", id),
  createExpense: (data: Record<string, unknown>) => create<TravelRecord>("expenses", data),
  updateExpense: (id: string, data: Record<string, unknown>) => update<TravelRecord>("expenses", id, data),
  mobileSummary: () => apiRequest<ApiResponse<TravelMobileSummary>>("/travel/mobile/summary/"),
  mobileBookings: (page = 1) => apiRequest<ApiListResponse<TravelBooking>>(`/travel/mobile/bookings/${qs({ page })}`),
  bookingAccountingPreview: (id: string) => apiRequest<ApiResponse<TravelRecord>>(`/travel/bookings/${id}/accounting-preview/`),
  postBookingAccounting: (id: string) => apiRequest<ApiResponse<TravelBooking>>(`/travel/bookings/${id}/post-accounting/`, { method: "POST" }),
};
