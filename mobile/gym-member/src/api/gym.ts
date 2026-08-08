import { apiRequest } from "./client";

export interface GymMemberProfile {
  id: string;
  membership_number: string;
  full_name: string;
  email: string;
  phone: string;
  status: string;
  branch_name: string | null;
}

export interface GymSubscription {
  id: string;
  plan_name: string;
  status: string;
  end_date: string | null;
  is_access_allowed: boolean;
}

export interface GymHome {
  member: GymMemberProfile;
  active_subscription: GymSubscription | null;
  today_checkins: number;
  is_checked_in: boolean;
  open_attendance_id: string | null;
  upcoming_classes: Array<{ id: string; class_name: string; starts_at: string | null }>;
  active_workouts: Array<{ id: string; plan_name: string; status: string }>;
}

export interface GymQr {
  payload: string;
  membership_number: string;
  member_name: string;
}

export interface Paginated<T> {
  results: T[];
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface GymAttendance {
  id: string;
  check_in_at: string | null;
  check_out_at: string | null;
  branch_name: string | null;
  is_open: boolean;
}

export function fetchHome() {
  return apiRequest<GymHome>("/mobile/gym/home/");
}

export function fetchQr() {
  return apiRequest<GymQr>("/mobile/gym/qr/");
}

export function fetchAttendance(page = 1) {
  return apiRequest<Paginated<GymAttendance>>(`/mobile/gym/attendance/?page=${page}`);
}

export function fetchWorkouts(page = 1) {
  return apiRequest<Paginated<{ id: string; plan_name: string; status: string }>>(
    `/mobile/gym/workouts/?page=${page}`
  );
}

export function fetchClasses(page = 1) {
  return apiRequest<
    Paginated<{ id: string; class_name: string; starts_at: string | null; status: string }>
  >(`/mobile/gym/classes/?page=${page}`);
}
