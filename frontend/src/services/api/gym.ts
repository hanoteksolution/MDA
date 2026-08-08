import type { ApiResponse } from "@/types/models";
import type { ApiListResponse } from "@/types/models/catalog";
import { apiRequest, qs } from "./http";

export interface GymMember {
  id: string;
  membership_number: string;
  full_name: string;
  email: string;
  phone: string;
  date_of_birth: string | null;
  gender: string;
  address: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  status: "active" | "inactive" | "suspended";
  joined_at: string | null;
  notes: string;
  photo_url: string;
  customer_id: string | null;
  customer_name: string | null;
  branch_id: string | null;
  branch_name: string | null;
  created_at?: string | null;
}

export interface GymMemberSummary {
  total: number;
  active: number;
  inactive: number;
  suspended: number;
}

export interface GymSubscriptionSummary {
  total: number;
  pending: number;
  active: number;
  frozen: number;
  expired: number;
  cancelled: number;
}

export interface GymAttendanceSummary {
  today_checkins: number;
  currently_inside: number;
  total: number;
}

export interface GymClassSummary {
  upcoming_sessions: number;
  active_bookings: number;
  waitlisted: number;
  class_templates: number;
}

export interface GymWorkoutSummary {
  exercises: number;
  plans: number;
  active_assignments: number;
  progress_logs: number;
  measurements: number;
}

export interface GymSummary {
  members: GymMemberSummary;
  subscriptions: GymSubscriptionSummary;
  attendance?: GymAttendanceSummary;
  classes?: GymClassSummary;
  workouts?: GymWorkoutSummary;
}

export interface GymAttendance {
  id: string;
  member_id: string;
  member_name: string;
  membership_number: string;
  subscription_id: string | null;
  plan_name: string | null;
  branch_id: string | null;
  branch_name: string | null;
  check_in_at: string | null;
  check_out_at: string | null;
  source: string;
  notes: string;
  is_open: boolean;
}

export interface MembershipPlan {
  id: string;
  code: string;
  name: string;
  description: string;
  duration_days: number;
  price: number;
  visit_limit: number | null;
  freeze_allowed: boolean;
  max_freeze_days: number;
  is_active: boolean;
  sort_order: number;
}

export interface MembershipSubscription {
  id: string;
  member_id: string;
  member_name: string;
  membership_number: string;
  plan_id: string;
  plan_name: string;
  plan_code: string;
  status: "pending" | "active" | "frozen" | "cancelled" | "expired";
  start_date: string | null;
  end_date: string | null;
  visits_allowed: number | null;
  visits_used: number;
  price_paid: number;
  freeze_days_used: number;
  frozen_at: string | null;
  cancelled_at: string | null;
  activated_at: string | null;
  invoice_id: string | null;
  invoice_number?: string | null;
  payment_reference: string;
  notes: string;
  is_access_allowed: boolean;
  created_at?: string | null;
}

export interface GymCheckoutResult {
  subscription: MembershipSubscription;
  invoice: {
    id: string;
    invoice_number: string;
    status: string;
    total_amount: number;
    amount_paid: number;
  };
  payments: {
    id: string;
    method: string;
    amount: number;
    reference: string;
    paid_at: string | null;
  }[];
  payment_reference: string;
  idempotent_replay?: boolean;
}

export type GymMemberFormData = {
  membership_number?: string;
  full_name: string;
  email?: string;
  phone?: string;
  date_of_birth?: string | null;
  gender?: string;
  address?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  status?: string;
  joined_at?: string | null;
  notes?: string;
  customer_id?: string | null;
  branch_id?: string | null;
};

export const gymApi = {
  summary: () => apiRequest<ApiResponse<GymSummary>>("/gym/summary/"),

  members: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymMember>>(`/gym/members/${qs(params)}`),

  getMember: (id: string) =>
    apiRequest<ApiResponse<GymMember>>(`/gym/members/${id}/`),

  createMember: (data: GymMemberFormData) =>
    apiRequest<ApiResponse<GymMember>>("/gym/members/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateMember: (id: string, data: Partial<GymMemberFormData>) =>
    apiRequest<ApiResponse<GymMember>>(`/gym/members/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteMember: (id: string) =>
    apiRequest<ApiResponse<null>>(`/gym/members/${id}/`, { method: "DELETE" }),

  plans: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<MembershipPlan>>(`/gym/plans/${qs(params)}`),

  createPlan: (data: Partial<MembershipPlan> & { code: string; name: string }) =>
    apiRequest<ApiResponse<MembershipPlan>>("/gym/plans/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updatePlan: (id: string, data: Partial<MembershipPlan>) =>
    apiRequest<ApiResponse<MembershipPlan>>(`/gym/plans/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deletePlan: (id: string) =>
    apiRequest<ApiResponse<null>>(`/gym/plans/${id}/`, { method: "DELETE" }),

  subscriptions: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<MembershipSubscription>>(
      `/gym/subscriptions/${qs(params)}`
    ),

  subscribe: (data: {
    member_id: string;
    plan_id: string;
    start_date?: string;
    activate?: boolean;
    mark_paid?: boolean;
    payment_reference?: string;
    price_paid?: number;
    notes?: string;
  }) =>
    apiRequest<ApiResponse<MembershipSubscription>>("/gym/subscriptions/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  checkoutMembership: (data: {
    member_id: string;
    plan_id: string;
    payment_method?: string;
    payment_reference?: string;
    idempotency_key?: string;
    activate_on_pay?: boolean;
    notes?: string;
    payments?: { method: string; amount: number; reference?: string }[];
  }) =>
    apiRequest<ApiResponse<GymCheckoutResult>>("/gym/checkout/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  paySubscription: (
    id: string,
    data: {
      payment_method?: string;
      payment_reference?: string;
      payments?: { method: string; amount: number; reference?: string }[];
    } = {}
  ) =>
    apiRequest<ApiResponse<GymCheckoutResult>>(`/gym/subscriptions/${id}/pay/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  activateSubscription: (
    id: string,
    data: { payment_reference?: string; start_date?: string; price_paid?: number } = {}
  ) =>
    apiRequest<ApiResponse<MembershipSubscription>>(`/gym/subscriptions/${id}/activate/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  freezeSubscription: (id: string) =>
    apiRequest<ApiResponse<MembershipSubscription>>(`/gym/subscriptions/${id}/freeze/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  unfreezeSubscription: (id: string) =>
    apiRequest<ApiResponse<MembershipSubscription>>(`/gym/subscriptions/${id}/unfreeze/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  cancelSubscription: (id: string, notes = "") =>
    apiRequest<ApiResponse<MembershipSubscription>>(`/gym/subscriptions/${id}/cancel/`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  attendance: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymAttendance>>(`/gym/attendance/${qs(params)}`),

  checkIn: (data: {
    member_id?: string;
    membership_number?: string;
    barcode?: string;
    qr_payload?: string;
    branch_id?: string;
    source?: string;
    notes?: string;
  }) =>
    apiRequest<ApiResponse<GymAttendance>>("/gym/attendance/check-in/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  checkOut: (data: {
    attendance_id?: string;
    member_id?: string;
    membership_number?: string;
    notes?: string;
  }) =>
    apiRequest<ApiResponse<GymAttendance>>("/gym/attendance/check-out/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  trainers: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymTrainer>>(`/gym/trainers/${qs(params)}`),

  createTrainer: (data: {
    full_name: string;
    code?: string;
    phone?: string;
    email?: string;
    specialty_codes?: string[];
    schedules?: { day_of_week: number; start_time: string; end_time: string }[];
    hourly_rate?: number;
    bio?: string;
  }) =>
    apiRequest<ApiResponse<GymTrainer>>("/gym/trainers/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  deleteTrainer: (id: string) =>
    apiRequest<ApiResponse<null>>(`/gym/trainers/${id}/`, { method: "DELETE" }),

  assignments: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<TrainerAssignment>>(`/gym/assignments/${qs(params)}`),

  assignTrainer: (data: {
    member_id: string;
    trainer_id: string;
    start_date?: string;
    notes?: string;
  }) =>
    apiRequest<ApiResponse<TrainerAssignment>>("/gym/assignments/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  endAssignment: (id: string) =>
    apiRequest<ApiResponse<TrainerAssignment>>(`/gym/assignments/${id}/end/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  ptSessions: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<PTSession>>(`/gym/pt-sessions/${qs(params)}`),

  schedulePtSession: (data: {
    member_id: string;
    trainer_id: string;
    scheduled_at: string;
    duration_minutes?: number;
    notes?: string;
  }) =>
    apiRequest<ApiResponse<PTSession>>("/gym/pt-sessions/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updatePtSessionStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<PTSession>>(`/gym/pt-sessions/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  checkoutPtSession: (
    id: string,
    data: {
      payment_method?: string;
      payment_reference?: string;
      amount?: number;
      idempotency_key?: string;
      notes?: string;
      payments?: { method: string; amount: number; reference?: string }[];
    } = {}
  ) =>
    apiRequest<
      ApiResponse<{
        session: PTSession;
        invoice: {
          id: string;
          invoice_number: string;
          status: string;
          total_amount: number;
          amount_paid: number;
        };
        payments: { id: string; method: string; amount: number; reference: string }[];
        idempotent_replay?: boolean;
      }>
    >(`/gym/pt-sessions/${id}/checkout/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  classes: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymClassTemplate>>(`/gym/classes/${qs(params)}`),

  createClass: (data: {
    code: string;
    name: string;
    default_capacity?: number;
    duration_minutes?: number;
    drop_in_price?: number;
    description?: string;
  }) =>
    apiRequest<ApiResponse<GymClassTemplate>>("/gym/classes/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  classSchedules: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymClassSchedule>>(
      `/gym/class-schedules/${qs(params)}`
    ),

  createClassSchedule: (data: {
    gym_class_id: string;
    starts_at: string;
    capacity?: number;
    trainer_id?: string;
  }) =>
    apiRequest<ApiResponse<GymClassSchedule>>("/gym/class-schedules/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  bookClass: (data: {
    schedule_id: string;
    member_id: string;
    allow_waitlist?: boolean;
  }) =>
    apiRequest<ApiResponse<GymClassBooking>>("/gym/class-bookings/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  classBookings: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymClassBooking>>(`/gym/class-bookings/${qs(params)}`),

  cancelBooking: (id: string) =>
    apiRequest<ApiResponse<GymClassBooking>>(`/gym/class-bookings/${id}/cancel/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  checkoutClassBooking: (
    id: string,
    data: {
      payment_method?: string;
      payment_reference?: string;
      amount?: number;
      idempotency_key?: string;
      notes?: string;
    } = {}
  ) =>
    apiRequest<
      ApiResponse<{
        booking: GymClassBooking;
        invoice: {
          id: string;
          invoice_number: string;
          status: string;
          total_amount: number;
          amount_paid: number;
        };
        idempotent_replay?: boolean;
      }>
    >(`/gym/class-bookings/${id}/checkout/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  exercises: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymExercise>>(`/gym/exercises/${qs(params)}`),

  createExercise: (data: {
    code: string;
    name: string;
    muscle_group?: string;
    equipment?: string;
    description?: string;
  }) =>
    apiRequest<ApiResponse<GymExercise>>("/gym/exercises/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  workoutPlans: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymWorkoutPlan>>(`/gym/workout-plans/${qs(params)}`),

  getWorkoutPlan: (id: string) =>
    apiRequest<ApiResponse<GymWorkoutPlanDetail>>("/gym/workout-plans/" + id + "/"),

  createWorkoutPlan: (data: {
    code: string;
    name: string;
    goal?: string;
    duration_weeks?: number;
    days?: {
      day_number: number;
      name: string;
      exercises: { exercise_id: string; sets?: number; reps?: string }[];
    }[];
  }) =>
    apiRequest<ApiResponse<GymWorkoutPlanDetail>>("/gym/workout-plans/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  workoutAssignments: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymWorkoutAssignment>>(
      `/gym/workout-assignments/${qs(params)}`
    ),

  assignWorkoutPlan: (data: {
    member_id: string;
    workout_plan_id: string;
    trainer_id?: string;
    start_date?: string;
  }) =>
    apiRequest<ApiResponse<GymWorkoutAssignment>>("/gym/workout-assignments/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  bodyMeasurements: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<GymBodyMeasurement>>(
      `/gym/body-measurements/${qs(params)}`
    ),

  recordBodyMeasurement: (data: {
    member_id: string;
    weight_kg?: number;
    body_fat_pct?: number;
    waist_cm?: number;
    measured_at?: string;
  }) =>
    apiRequest<ApiResponse<GymBodyMeasurement>>("/gym/body-measurements/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  bodyMeasurementChart: (params: { member_id: string; metric?: string }) =>
    apiRequest<ApiResponse<{ points: { date: string; value: number }[] }>>(
      `/gym/body-measurements/chart/${qs(params)}`
    ),
};

export interface GymClassTemplate {
  id: string;
  code: string;
  name: string;
  description: string;
  default_capacity: number;
  duration_minutes: number;
  drop_in_price?: number;
  default_trainer_id: string | null;
  default_trainer_name: string | null;
  is_active: boolean;
}

export interface GymClassSchedule {
  id: string;
  gym_class_id: string;
  class_name: string;
  class_code: string;
  drop_in_price?: number;
  trainer_id: string | null;
  trainer_name: string | null;
  starts_at: string | null;
  ends_at: string | null;
  capacity: number;
  confirmed_count: number;
  waitlisted_count: number;
  spots_remaining: number;
  status: string;
}

export interface GymClassBooking {
  id: string;
  schedule_id: string;
  class_name: string;
  starts_at: string | null;
  member_id: string;
  member_name: string;
  membership_number: string;
  status: string;
  booked_at: string | null;
  drop_in_price?: number;
  amount_charged?: number;
  invoice_id?: string | null;
  payment_reference?: string;
}

export interface GymExercise {
  id: string;
  code: string;
  name: string;
  description: string;
  muscle_group: string;
  equipment: string;
  is_active: boolean;
}

export interface GymWorkoutPlan {
  id: string;
  code: string;
  name: string;
  description: string;
  goal: string;
  duration_weeks: number;
  is_active: boolean;
  trainer_id: string | null;
  trainer_name: string | null;
  day_count: number;
}

export interface GymWorkoutPlanDetail extends GymWorkoutPlan {
  days?: {
    id: string;
    day_number: number;
    name: string;
    notes: string;
    exercises: {
      id: string;
      exercise_id: string;
      exercise_name: string;
      sets: number;
      reps: string;
    }[];
  }[];
}

export interface GymWorkoutAssignment {
  id: string;
  member_id: string;
  member_name: string;
  workout_plan_id: string;
  plan_name: string;
  plan_code: string;
  trainer_id: string | null;
  trainer_name: string | null;
  start_date: string | null;
  end_date: string | null;
  status: string;
}

export interface GymBodyMeasurement {
  id: string;
  member_id: string;
  member_name: string;
  measured_at: string | null;
  weight_kg: number | null;
  body_fat_pct: number | null;
  chest_cm: number | null;
  waist_cm: number | null;
  hips_cm: number | null;
  arms_cm: number | null;
  thighs_cm: number | null;
  notes: string;
}

export interface GymTrainer {
  id: string;
  code: string;
  full_name: string;
  email: string;
  phone: string;
  bio: string;
  status: string;
  hourly_rate: number;
  notes: string;
  branch_id: string | null;
  branch_name: string | null;
  specialties: { id: string; code: string; name: string }[];
  schedules: {
    id: string;
    day_of_week: number;
    start_time: string | null;
    end_time: string | null;
    is_active: boolean;
  }[];
}

export interface TrainerAssignment {
  id: string;
  member_id: string;
  member_name: string;
  membership_number: string;
  trainer_id: string;
  trainer_name: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  notes: string;
}

export interface PTSession {
  id: string;
  member_id: string;
  member_name: string;
  trainer_id: string;
  trainer_name: string;
  trainer_hourly_rate?: number;
  assignment_id: string | null;
  scheduled_at: string | null;
  duration_minutes: number;
  status: string;
  amount_charged?: number;
  suggested_amount?: number;
  invoice_id?: string | null;
  payment_reference?: string;
  notes: string;
}
