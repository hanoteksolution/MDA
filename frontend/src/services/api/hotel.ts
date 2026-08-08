import type { ApiListResponse } from "@/types/models/catalog";
import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface HotelSummary {
  room_types: number;
  rooms: number;
  rooms_vacant: number;
  rooms_occupied: number;
  rooms_dirty: number;
  reservations_booked: number;
  in_house: number;
  arrivals_today: number;
  departures_today: number;
  guests: number;
}

export interface HotelRoomType {
  id: string;
  branch_id: string;
  branch_name: string;
  name: string;
  code: string;
  base_rate: number;
  capacity: number;
  description: string;
  is_active: boolean;
  sort_order: number;
}

export interface HotelRoom {
  id: string;
  branch_id: string;
  branch_name: string;
  room_type_id: string;
  room_type_name: string;
  code: string;
  floor: string;
  status: "vacant" | "occupied" | "dirty" | "ooo" | "reserved";
  is_active: boolean;
  notes: string;
}

export interface HotelGuest {
  id: string;
  branch_id: string | null;
  full_name: string;
  phone: string;
  email: string;
  id_number: string;
  notes: string;
  is_active: boolean;
}

export interface FolioLine {
  id: string;
  line_type: string;
  description: string;
  amount: number;
  quantity: number;
  posted_at: string | null;
  notes: string;
}

export interface HotelFolio {
  id: string;
  reservation_id: string;
  branch_id: string;
  status: string;
  balance: number;
  amount_paid?: number;
  outstanding?: number;
  payment_method?: string;
  settled_at?: string | null;
  opened_at: string | null;
  closed_at: string | null;
  notes: string;
  lines?: FolioLine[];
  line_count?: number;
}

export interface HotelReservation {
  id: string;
  reservation_number: string;
  branch_id: string;
  guest_id: string;
  guest_name: string;
  guest_phone: string;
  room_type_id: string;
  room_type_name: string;
  room_id: string | null;
  room_code: string | null;
  status: string;
  check_in_date: string | null;
  check_out_date: string | null;
  nights: number;
  adults: number;
  children: number;
  rate_amount: number;
  notes: string;
  checked_in_at: string | null;
  checked_out_at: string | null;
  folio?: HotelFolio | null;
}

export interface HotelOpenFolio {
  folio_id: string;
  reservation_id: string;
  reservation_number: string;
  room_code: string;
  guest_name: string;
  balance: number;
  branch_id: string;
}

export const hotelApi = {
  summary: (branchId?: string) =>
    apiRequest<ApiResponse<HotelSummary>>(
      `/hotel/summary/${qs({ branch_id: branchId })}`
    ),

  openFolios: (branchId?: string) =>
    apiRequest<ApiResponse<{ results: HotelOpenFolio[]; count: number }>>(
      `/hotel/folios/open/${qs({ branch_id: branchId })}`
    ),
  roomTypes: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<HotelRoomType>>(
      `/hotel/room-types/${qs({ page, branch_id: branchId })}`
    ),

  createRoomType: (data: {
    name: string;
    branch_id: string;
    code?: string;
    base_rate?: number;
    capacity?: number;
  }) =>
    apiRequest<ApiResponse<HotelRoomType>>("/hotel/room-types/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  rooms: (page = 1, branchId?: string, status?: string) =>
    apiRequest<ApiListResponse<HotelRoom>>(
      `/hotel/rooms/${qs({ page, branch_id: branchId, status })}`
    ),

  createRoom: (data: {
    code: string;
    branch_id: string;
    room_type_id: string;
    floor?: string;
  }) =>
    apiRequest<ApiResponse<HotelRoom>>("/hotel/rooms/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  setRoomStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<HotelRoom>>(`/hotel/rooms/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  guests: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<HotelGuest>>(
      `/hotel/guests/${qs({ page, branch_id: branchId })}`
    ),

  createGuest: (data: {
    full_name: string;
    branch_id?: string;
    phone?: string;
    email?: string;
  }) =>
    apiRequest<ApiResponse<HotelGuest>>("/hotel/guests/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  reservations: (page = 1, branchId?: string, status?: string) =>
    apiRequest<ApiListResponse<HotelReservation>>(
      `/hotel/reservations/${qs({ page, branch_id: branchId, status })}`
    ),

  createReservation: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<HotelReservation>>("/hotel/reservations/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  checkIn: (id: string, roomId?: string) =>
    apiRequest<ApiResponse<HotelReservation>>(`/hotel/reservations/${id}/check-in/`, {
      method: "POST",
      body: JSON.stringify(roomId ? { room_id: roomId } : {}),
    }),

  checkOut: (
    id: string,
    data?: { payment_method?: string; payment_reference?: string }
  ) =>
    apiRequest<ApiResponse<HotelReservation & { settlement?: Record<string, unknown> }>>(
      `/hotel/reservations/${id}/check-out/`,
      {
        method: "POST",
        body: JSON.stringify(data || {}),
      }
    ),

  cancel: (id: string) =>
    apiRequest<ApiResponse<HotelReservation>>(`/hotel/reservations/${id}/cancel/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  folio: (id: string) =>
    apiRequest<ApiResponse<HotelFolio>>(`/hotel/reservations/${id}/folio/`),
};
