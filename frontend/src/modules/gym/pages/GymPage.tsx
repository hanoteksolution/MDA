import { useCallback, useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import {
  CreditCard,
  Dumbbell,
  LogIn,
  LogOut,
  Mail,
  Pencil,
  Phone,
  Plus,
  Trash2,
  Users,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { FormPageLayout, FormActions } from "@/components/forms/FormPageLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { usePermissions } from "@/hooks/usePermissions";
import {
  gymApi,
  type GymAttendance,
  type GymBodyMeasurement,
  type GymClassBooking,
  type GymClassSchedule,
  type GymClassTemplate,
  type GymExercise,
  type GymMember,
  type GymSummary,
  type GymTrainer,
  type GymWorkoutAssignment,
  type GymWorkoutPlan,
  type MembershipPlan,
  type MembershipSubscription,
  type PTSession,
  type TrainerAssignment,
} from "@/services/api/gym";
import { ChartCard } from "@/components/data/ChartCard";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { chartColors } from "@/design-system";
import { customersApi } from "@/services/api/partners";
import { settingsApi } from "@/services/api/admin";
import { appDialog } from "@/components/feedback/AppDialog";
import { formatCurrency } from "@/utils/cn";

type Tab =
  | "members"
  | "plans"
  | "subscriptions"
  | "attendance"
  | "trainers"
  | "classes"
  | "workouts";
type MemberMode = "list" | "create" | "edit";

const emptyMemberForm = {
  membership_number: "",
  full_name: "",
  email: "",
  phone: "",
  date_of_birth: "",
  gender: "",
  address: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  status: "active",
  joined_at: "",
  notes: "",
  customer_id: "",
  branch_id: "",
};

const emptyPlanForm = {
  code: "",
  name: "",
  description: "",
  duration_days: "30",
  price: "0",
  visit_limit: "",
  freeze_allowed: true,
  max_freeze_days: "30",
  is_active: true,
};

export function GymPage() {
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("gym.manage");
  const canCheckIn = hasPermission("gym.attendance.checkin") || canManage;

  const [tab, setTab] = useState<Tab>("members");
  const [summary, setSummary] = useState<GymSummary | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [mode, setMode] = useState<MemberMode>("list");
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyMemberForm);
  const [planForm, setPlanForm] = useState(emptyPlanForm);
  const [showPlanForm, setShowPlanForm] = useState(false);
  const [sellForm, setSellForm] = useState({
    member_id: "",
    plan_id: "",
    payment_method: "cash",
    payment_reference: "",
  });
  const [checkInCode, setCheckInCode] = useState("");
  const [checkInMsg, setCheckInMsg] = useState<string | null>(null);
  const [attendance, setAttendance] = useState<GymAttendance[]>([]);
  const [attLoading, setAttLoading] = useState(false);
  const [trainers, setTrainers] = useState<GymTrainer[]>([]);
  const [assignments, setAssignments] = useState<TrainerAssignment[]>([]);
  const [ptSessions, setPtSessions] = useState<PTSession[]>([]);
  const [trainerForm, setTrainerForm] = useState({
    full_name: "",
    phone: "",
    specialty_codes: "strength",
    hourly_rate: "40",
  });
  const [assignForm, setAssignForm] = useState({ member_id: "", trainer_id: "" });
  const [ptForm, setPtForm] = useState({
    member_id: "",
    trainer_id: "",
    scheduled_at: "",
    duration_minutes: "60",
  });
  const [showTrainerForm, setShowTrainerForm] = useState(false);
  const [classTemplates, setClassTemplates] = useState<GymClassTemplate[]>([]);
  const [classSchedules, setClassSchedules] = useState<GymClassSchedule[]>([]);
  const [classBookings, setClassBookings] = useState<GymClassBooking[]>([]);
  const [classForm, setClassForm] = useState({
    code: "",
    name: "",
    default_capacity: "15",
    drop_in_price: "15",
  });
  const [schedForm, setSchedForm] = useState({
    gym_class_id: "",
    starts_at: "",
    capacity: "",
  });
  const [bookForm, setBookForm] = useState({ schedule_id: "", member_id: "" });
  const [showClassForm, setShowClassForm] = useState(false);
  const [exercises, setExercises] = useState<GymExercise[]>([]);
  const [workoutPlans, setWorkoutPlans] = useState<GymWorkoutPlan[]>([]);
  const [workoutAssignments, setWorkoutAssignments] = useState<GymWorkoutAssignment[]>([]);
  const [measurements, setMeasurements] = useState<GymBodyMeasurement[]>([]);
  const [chartPoints, setChartPoints] = useState<{ date: string; value: number }[]>([]);
  const [progressMemberId, setProgressMemberId] = useState("");
  const [exerciseForm, setExerciseForm] = useState({
    code: "",
    name: "",
    muscle_group: "chest",
  });
  const [planFormWo, setPlanFormWo] = useState({
    code: "",
    name: "",
    exercise_id: "",
  });
  const [assignWoForm, setAssignWoForm] = useState({ member_id: "", workout_plan_id: "" });
  const [measureForm, setMeasureForm] = useState({
    member_id: "",
    weight_kg: "",
    waist_cm: "",
  });
  const [showExerciseForm, setShowExerciseForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [customers, setCustomers] = useState<{ id: string; name: string }[]>([]);
  const [branches, setBranches] = useState<{ id: string; name: string }[]>([]);
  const [plans, setPlans] = useState<MembershipPlan[]>([]);
  const [subs, setSubs] = useState<MembershipSubscription[]>([]);
  const [subsLoading, setSubsLoading] = useState(false);

  const {
    data: members,
    loading,
    page,
    setPage,
    pageSize,
    setPageSize,
    total,
    reload,
  } = usePaginatedList(gymApi.members, { search, status: statusFilter });

  const reloadSummary = useCallback(() => {
    gymApi.summary().then((res) => setSummary(res.data)).catch(() => setSummary(null));
  }, []);

  const reloadPlans = useCallback(() => {
    gymApi
      .plans({ page_size: 100, is_active: "true" })
      .then((res) => setPlans(res.data.results))
      .catch(() => setPlans([]));
  }, []);

  const reloadSubs = useCallback(() => {
    setSubsLoading(true);
    gymApi
      .subscriptions({ page_size: 100, search: search || undefined, status: statusFilter || undefined })
      .then((res) => setSubs(res.data.results))
      .catch(() => setSubs([]))
      .finally(() => setSubsLoading(false));
  }, [search, statusFilter]);

  const reloadAttendance = useCallback(() => {
    setAttLoading(true);
    gymApi
      .attendance({ page_size: 50 })
      .then((res) => setAttendance(res.data.results))
      .catch(() => setAttendance([]))
      .finally(() => setAttLoading(false));
  }, []);

  const reloadTrainers = useCallback(() => {
    Promise.all([
      gymApi.trainers({ page_size: 100 }),
      gymApi.assignments({ page_size: 100, status: "active" }),
      gymApi.ptSessions({ page_size: 50 }),
    ])
      .then(([t, a, p]) => {
        setTrainers(t.data.results);
        setAssignments(a.data.results);
        setPtSessions(p.data.results);
      })
      .catch(() => {
        setTrainers([]);
        setAssignments([]);
        setPtSessions([]);
      });
  }, []);

  const reloadClasses = useCallback(() => {
    Promise.all([
      gymApi.classes({ page_size: 100, is_active: "true" }),
      gymApi.classSchedules({ page_size: 50, upcoming: "true" }),
      gymApi.classBookings({ page_size: 50, status: "confirmed" }),
    ])
      .then(([c, s, b]) => {
        setClassTemplates(c.data.results);
        setClassSchedules(s.data.results);
        setClassBookings(b.data.results);
      })
      .catch(() => {
        setClassTemplates([]);
        setClassSchedules([]);
        setClassBookings([]);
      });
  }, []);

  const reloadWorkouts = useCallback((memberId?: string) => {
    Promise.all([
      gymApi.exercises({ page_size: 100, is_active: "true" }),
      gymApi.workoutPlans({ page_size: 100, is_active: "true" }),
      gymApi.workoutAssignments({ page_size: 50, status: "active" }),
      gymApi.bodyMeasurements({
        page_size: 20,
        member_id: memberId || undefined,
      }),
    ])
      .then(([ex, pl, asg, meas]) => {
        setExercises(ex.data.results);
        setWorkoutPlans(pl.data.results);
        setWorkoutAssignments(asg.data.results);
        setMeasurements(meas.data.results);
      })
      .catch(() => {
        setExercises([]);
        setWorkoutPlans([]);
        setWorkoutAssignments([]);
        setMeasurements([]);
      });
    if (memberId) {
      gymApi
        .bodyMeasurementChart({ member_id: memberId, metric: "weight_kg" })
        .then((res) => setChartPoints(res.data.points))
        .catch(() => setChartPoints([]));
    } else {
      setChartPoints([]);
    }
  }, []);

  useEffect(() => {
    reloadSummary();
  }, [members, reloadSummary]);

  useEffect(() => {
    customersApi
      .list({ page_size: 100 })
      .then((res) => setCustomers(res.data.results.map((c) => ({ id: c.id, name: c.full_name }))))
      .catch(() => setCustomers([]));
    settingsApi
      .branches()
      .then((res) => setBranches(res.data.map((b) => ({ id: b.id, name: b.name }))))
      .catch(() => setBranches([]));
    reloadPlans();
  }, [reloadPlans]);

  useEffect(() => {
    if (tab === "subscriptions") reloadSubs();
    if (tab === "plans") reloadPlans();
    if (tab === "attendance") reloadAttendance();
    if (tab === "trainers") reloadTrainers();
    if (tab === "classes") reloadClasses();
    if (tab === "workouts") reloadWorkouts(progressMemberId || undefined);
  }, [tab, reloadSubs, reloadPlans, reloadAttendance, reloadTrainers, reloadClasses, reloadWorkouts, progressMemberId]);

  const handleCheckIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setCheckInMsg(null);
    try {
      const code = checkInCode.trim();
      const res = await gymApi.checkIn({
        membership_number: code,
        source: "membership_number",
      });
      setCheckInMsg(`Checked in: ${res.data.member_name} (${res.data.membership_number})`);
      setCheckInCode("");
      reloadAttendance();
      reloadSummary();
    } catch (err) {
      setCheckInMsg(err instanceof Error ? err.message : "Check-in failed");
    } finally {
      setSaving(false);
    }
  };

  const handleCheckOut = async (row: GymAttendance) => {
    try {
      await gymApi.checkOut({ attendance_id: row.id });
      reloadAttendance();
      reloadSummary();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Check-out failed");
    }
  };
  const openCreate = () => {
    setForm(emptyMemberForm);
    setEditId(null);
    setMode("create");
  };

  const openEdit = async (id: string) => {
    const res = await gymApi.getMember(id);
    const m = res.data;
    setForm({
      membership_number: m.membership_number,
      full_name: m.full_name,
      email: m.email || "",
      phone: m.phone || "",
      date_of_birth: m.date_of_birth || "",
      gender: m.gender || "",
      address: m.address || "",
      emergency_contact_name: m.emergency_contact_name || "",
      emergency_contact_phone: m.emergency_contact_phone || "",
      status: m.status,
      joined_at: m.joined_at || "",
      notes: m.notes || "",
      customer_id: m.customer_id || "",
      branch_id: m.branch_id || "",
    });
    setEditId(id);
    setMode("edit");
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this member?")) return;
    await gymApi.deleteMember(id);
    reload();
  };

  const handleSubmitMember = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        membership_number: form.membership_number.trim() || undefined,
        full_name: form.full_name.trim(),
        email: form.email || undefined,
        phone: form.phone || undefined,
        date_of_birth: form.date_of_birth || null,
        gender: form.gender || undefined,
        address: form.address || undefined,
        emergency_contact_name: form.emergency_contact_name || undefined,
        emergency_contact_phone: form.emergency_contact_phone || undefined,
        status: form.status,
        joined_at: form.joined_at || null,
        notes: form.notes || undefined,
        customer_id: form.customer_id || null,
        branch_id: form.branch_id || null,
      };
      if (mode === "edit" && editId) await gymApi.updateMember(editId, payload);
      else await gymApi.createMember(payload);
      setMode("list");
      reload();
      reloadSummary();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleSavePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await gymApi.createPlan({
        code: planForm.code.trim(),
        name: planForm.name.trim(),
        description: planForm.description,
        duration_days: parseInt(planForm.duration_days, 10) || 30,
        price: parseFloat(planForm.price) || 0,
        visit_limit: planForm.visit_limit ? parseInt(planForm.visit_limit, 10) : null,
        freeze_allowed: planForm.freeze_allowed,
        max_freeze_days: parseInt(planForm.max_freeze_days, 10) || 30,
        is_active: planForm.is_active,
      });
      setShowPlanForm(false);
      setPlanForm(emptyPlanForm);
      reloadPlans();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Plan save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleSell = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await gymApi.checkoutMembership({
        member_id: sellForm.member_id,
        plan_id: sellForm.plan_id,
        payment_method: sellForm.payment_method,
        payment_reference: sellForm.payment_reference || undefined,
        activate_on_pay: sellForm.payment_method !== "on_account",
      });
      const msg = res.data.idempotent_replay
        ? "Checkout replayed."
        : res.data.subscription.status === "active"
          ? `Sold — invoice ${res.data.invoice.invoice_number}`
          : `Invoice ${res.data.invoice.invoice_number} — pending payment`;
      await appDialog.alert(msg);
      setSellForm({
        member_id: "",
        plan_id: "",
        payment_method: "cash",
        payment_reference: "",
      });
      setTab("subscriptions");
      reloadSubs();
      reloadSummary();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setSaving(false);
    }
  };

  const memberColumns: Column<GymMember>[] = [
    {
      key: "member",
      header: "Member",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.full_name}</p>
          <p className="text-xs text-muted-foreground font-mono">{r.membership_number}</p>
        </div>
      ),
    },
    {
      key: "contact",
      header: "Contact",
      cell: (r) => (
        <div className="text-sm">
          {r.phone && (
            <p className="flex items-center gap-1 text-muted-foreground">
              <Phone className="h-3 w-3" /> {r.phone}
            </p>
          )}
          {r.email && (
            <p className="flex items-center gap-1">
              <Mail className="h-3 w-3" /> {r.email}
            </p>
          )}
        </div>
      ),
    },
    { key: "branch", header: "Branch", cell: (r) => r.branch_name || "—" },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge
          variant={
            r.status === "active" ? "success" : r.status === "suspended" ? "warning" : "secondary"
          }
        >
          {r.status}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        canManage ? (
          <div className="flex justify-end gap-1">
            <Button variant="ghost" size="sm" onClick={() => void openEdit(r.id)}>
              <Pencil className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => void handleDelete(r.id)}>
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        ) : null,
    },
  ];

  const planColumns: Column<MembershipPlan>[] = [
    {
      key: "name",
      header: "Plan",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.name}</p>
          <p className="text-xs font-mono text-muted-foreground">{r.code}</p>
        </div>
      ),
    },
    { key: "duration", header: "Days", cell: (r) => r.duration_days },
    { key: "price", header: "Price", cell: (r) => formatCurrency(r.price) },
    {
      key: "visits",
      header: "Visits",
      cell: (r) => (r.visit_limit == null ? "Unlimited" : r.visit_limit),
    },
    {
      key: "active",
      header: "Status",
      cell: (r) => (
        <Badge variant={r.is_active ? "success" : "secondary"}>
          {r.is_active ? "Active" : "Off"}
        </Badge>
      ),
    },
  ];

  const subColumns: Column<MembershipSubscription>[] = [
    {
      key: "member",
      header: "Member",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.member_name}</p>
          <p className="text-xs font-mono text-muted-foreground">{r.membership_number}</p>
        </div>
      ),
    },
    { key: "plan", header: "Plan", cell: (r) => r.plan_name },
    {
      key: "invoice",
      header: "Invoice",
      cell: (r) => r.invoice_number || "—",
    },
    {
      key: "dates",
      header: "Period",
      cell: (r) => (
        <span className="text-sm">
          {r.start_date || "—"} → {r.end_date || "—"}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge
          variant={
            r.status === "active"
              ? "success"
              : r.status === "frozen" || r.status === "pending"
                ? "warning"
                : "secondary"
          }
        >
          {r.status}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        canManage ? (
          <div className="flex flex-wrap justify-end gap-1">
            {r.status === "pending" && (
              <Button
                variant="secondary"
                size="sm"
                onClick={async () => {
                  try {
                    const res = await gymApi.paySubscription(r.id, {
                      payment_method: "cash",
                      payment_reference: "counter-pay",
                    });
                    await appDialog.alert(
                      `Paid — ${res.data.invoice.invoice_number || "invoice"}`
                    );
                    reloadSubs();
                    reloadSummary();
                  } catch (err) {
                    await appDialog.alert(err instanceof Error ? err.message : "Pay failed");
                  }
                }}
              >
                Collect payment
              </Button>
            )}
            {r.status === "active" && (
              <Button
                variant="secondary"
                size="sm"
                onClick={async () => {
                  await gymApi.freezeSubscription(r.id);
                  reloadSubs();
                }}
              >
                Freeze
              </Button>
            )}
            {r.status === "frozen" && (
              <Button
                variant="secondary"
                size="sm"
                onClick={async () => {
                  await gymApi.unfreezeSubscription(r.id);
                  reloadSubs();
                }}
              >
                Unfreeze
              </Button>
            )}
            {r.status !== "cancelled" && r.status !== "expired" && (
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  if (!confirm("Cancel this subscription?")) return;
                  await gymApi.cancelSubscription(r.id);
                  reloadSubs();
                  reloadSummary();
                }}
              >
                Cancel
              </Button>
            )}
          </div>
        ) : null,
    },
  ];

  if (mode !== "list") {
    return (
      <PageLayout
        title={mode === "edit" ? "Edit member" : "Add member"}
        description="Gym member profile. Membership number is optional — auto-assigned when blank."
        breadcrumbs={["Home", "Gym", mode === "edit" ? "Edit" : "New"]}
        backTo="/gym"
        backLabel="Back to gym"
      >
        <form onSubmit={handleSubmitMember}>
          <FormPageLayout
            main={
              <FormGrid>
                <FormField label="Full name" required>
                  <Input
                    required
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                    className="h-11 rounded-xl"
                  />
                </FormField>
                <FormField label="Membership #" hint="Auto-generated if empty">
                  <Input
                    value={form.membership_number}
                    onChange={(e) => setForm({ ...form, membership_number: e.target.value })}
                    className="h-11 rounded-xl font-mono"
                  />
                </FormField>
                <FormField label="Phone">
                  <Input
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    className="h-11 rounded-xl"
                  />
                </FormField>
                <FormField label="Email">
                  <Input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="h-11 rounded-xl"
                  />
                </FormField>
                <FormField label="Status">
                  <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                    <SelectTrigger className="h-11 rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                      <SelectItem value="suspended">Suspended</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Branch">
                  <Select
                    value={form.branch_id || "none"}
                    onValueChange={(v) => setForm({ ...form, branch_id: v === "none" ? "" : v })}
                  >
                    <SelectTrigger className="h-11 rounded-xl">
                      <SelectValue placeholder="—" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">—</SelectItem>
                      {branches.map((b) => (
                        <SelectItem key={b.id} value={b.id}>
                          {b.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Linked customer">
                  <Select
                    value={form.customer_id || "none"}
                    onValueChange={(v) => setForm({ ...form, customer_id: v === "none" ? "" : v })}
                  >
                    <SelectTrigger className="h-11 rounded-xl">
                      <SelectValue placeholder="—" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">—</SelectItem>
                      {customers.map((c) => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
              </FormGrid>
            }
            actions={
              <FormActions>
                <div className="flex gap-3">
                  <Button type="submit" loading={saving}>
                    {mode === "edit" ? "Save changes" : "Create member"}
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => setMode("list")}>
                    Cancel
                  </Button>
                </div>
              </FormActions>
            }
          />
        </form>
      </PageLayout>
    );
  }

  const memberSummary = summary?.members;
  const subSummary = summary?.subscriptions;
  const attSummary = summary?.attendance;

  return (
    <PageLayout
      title="Gym"
      description="Members, plans, subscriptions, and check-in."
      breadcrumbs={["Home", "Gym"]}
      actions={
        canManage && tab === "members" ? (
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" />
            Add member
          </Button>
        ) : undefined
      }
    >
      <KpiGrid>
        <KpiCard
          title="Members"
          value={String(memberSummary?.total ?? total)}
          icon={<Users className="h-5 w-5" />}
        />
        <KpiCard
          title="Active subs"
          value={String(subSummary?.active ?? 0)}
          icon={<CreditCard className="h-5 w-5" />}
          accent="success"
        />
        <KpiCard
          title="Check-ins today"
          value={String(attSummary?.today_checkins ?? 0)}
          icon={<LogIn className="h-5 w-5" />}
        />
        <KpiCard
          title="Inside now"
          value={String(attSummary?.currently_inside ?? 0)}
          icon={<Dumbbell className="h-5 w-5" />}
          accent="warning"
        />
      </KpiGrid>

      <div className="mt-4 flex flex-wrap gap-2">
        {(
          [
            "members",
            "plans",
            "subscriptions",
            "attendance",
            "trainers",
            "classes",
            "workouts",
          ] as Tab[]
        ).map((t) => (
          <Button
            key={t}
            variant={tab === t ? "default" : "secondary"}
            size="sm"
            onClick={() => {
              setTab(t);
              setSearch("");
              setStatusFilter("");
            }}
          >
            {t === "members"
              ? "Members"
              : t === "plans"
                ? "Plans"
                : t === "subscriptions"
                  ? "Subscriptions"
                  : t === "attendance"
                    ? "Check-in"
                    : t === "trainers"
                      ? "Trainers"
                      : t === "classes"
                        ? "Classes"
                        : "Workouts"}
          </Button>
        ))}
      </div>

      {tab === "members" && (
        <ContentSection
          title="Members"
          description="Tenant-scoped gym members."
          action={
            <div className="flex flex-wrap gap-2">
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search…"
                className="h-9 w-48"
              />
              <Select
                value={statusFilter || "all"}
                onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}
              >
                <SelectTrigger className="h-9 w-36">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                </SelectContent>
              </Select>
            </div>
          }
        >
          <DataTable
            columns={memberColumns}
            data={members}
            loading={loading}
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            emptyMessage="No members yet."
          />
        </ContentSection>
      )}

      {tab === "plans" && (
        <ContentSection
          title="Membership plans"
          description="Duration, price, and visit limits."
          action={
            canManage ? (
              <Button size="sm" onClick={() => setShowPlanForm((v) => !v)}>
                <Plus className="h-4 w-4" />
                {showPlanForm ? "Close" : "New plan"}
              </Button>
            ) : undefined
          }
        >
          {showPlanForm && (
            <form onSubmit={handleSavePlan} className="mb-6 rounded-xl border border-border/60 p-4">
              <FormGrid>
                <FormField label="Code" required>
                  <Input
                    required
                    value={planForm.code}
                    onChange={(e) => setPlanForm({ ...planForm, code: e.target.value })}
                    className="h-10 rounded-xl font-mono"
                    placeholder="monthly"
                  />
                </FormField>
                <FormField label="Name" required>
                  <Input
                    required
                    value={planForm.name}
                    onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })}
                    className="h-10 rounded-xl"
                  />
                </FormField>
                <FormField label="Duration (days)" required>
                  <Input
                    required
                    type="number"
                    min={1}
                    value={planForm.duration_days}
                    onChange={(e) => setPlanForm({ ...planForm, duration_days: e.target.value })}
                    className="h-10 rounded-xl"
                  />
                </FormField>
                <FormField label="Price" required>
                  <Input
                    required
                    type="number"
                    min={0}
                    step="0.01"
                    value={planForm.price}
                    onChange={(e) => setPlanForm({ ...planForm, price: e.target.value })}
                    className="h-10 rounded-xl"
                  />
                </FormField>
                <FormField label="Visit limit" hint="Blank = unlimited">
                  <Input
                    type="number"
                    min={0}
                    value={planForm.visit_limit}
                    onChange={(e) => setPlanForm({ ...planForm, visit_limit: e.target.value })}
                    className="h-10 rounded-xl"
                  />
                </FormField>
                <FormField label="Max freeze days">
                  <Input
                    type="number"
                    min={0}
                    value={planForm.max_freeze_days}
                    onChange={(e) => setPlanForm({ ...planForm, max_freeze_days: e.target.value })}
                    className="h-10 rounded-xl"
                  />
                </FormField>
              </FormGrid>
              <div className="mt-3">
                <Button type="submit" loading={saving} size="sm">
                  Create plan
                </Button>
              </div>
            </form>
          )}
          <DataTable columns={planColumns} data={plans} emptyMessage="No plans yet." />
        </ContentSection>
      )}

      {tab === "subscriptions" && (
        <>
          {canManage && (
            <ContentSection title="Sell membership" description="Creates a central invoice + payment; activates when paid.">
              <form onSubmit={handleSell}>
                <FormGrid>
                  <FormField label="Member" required>
                    <Select
                      value={sellForm.member_id || "none"}
                      onValueChange={(v) =>
                        setSellForm({ ...sellForm, member_id: v === "none" ? "" : v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Select member" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {members.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.full_name} ({m.membership_number})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Plan" required>
                    <Select
                      value={sellForm.plan_id || "none"}
                      onValueChange={(v) =>
                        setSellForm({ ...sellForm, plan_id: v === "none" ? "" : v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Select plan" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {plans.map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.name} — {formatCurrency(p.price)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Payment method" required>
                    <Select
                      value={sellForm.payment_method}
                      onValueChange={(v) =>
                        setSellForm({ ...sellForm, payment_method: v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="cash">Cash</SelectItem>
                        <SelectItem value="mobile">Mobile money</SelectItem>
                        <SelectItem value="card">Card</SelectItem>
                        <SelectItem value="on_account">Pay later (invoice)</SelectItem>
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Payment reference">
                    <Input
                      value={sellForm.payment_reference}
                      onChange={(e) =>
                        setSellForm({ ...sellForm, payment_reference: e.target.value })
                      }
                      className="h-10 rounded-xl"
                      placeholder="Receipt / MoMo ref"
                    />
                  </FormField>
                </FormGrid>
                <div className="mt-3">
                  <Button
                    type="submit"
                    loading={saving}
                    disabled={!sellForm.member_id || !sellForm.plan_id}
                  >
                    {sellForm.payment_method === "on_account"
                      ? "Create invoice"
                      : "Sell & activate"}
                  </Button>
                </div>
              </form>
            </ContentSection>
          )}
          <ContentSection title="Subscriptions" description="Lifecycle: pending → active → freeze/cancel/expire.">
            <DataTable
              columns={subColumns}
              data={subs}
              loading={subsLoading}
              emptyMessage="No subscriptions yet."
            />
          </ContentSection>
        </>
      )}

      {tab === "attendance" && (
        <>
          {canCheckIn && (
            <ContentSection
              title="Check-in console"
              description="Scan or type membership number / phone. Requires an active subscription."
            >
              <form onSubmit={handleCheckIn} className="flex flex-wrap items-end gap-3">
                <FormField label="Membership # / phone" className="min-w-[240px] flex-1">
                  <Input
                    autoFocus
                    value={checkInCode}
                    onChange={(e) => setCheckInCode(e.target.value)}
                    placeholder="MEM-00001 or phone"
                    className="h-11 rounded-xl font-mono"
                  />
                </FormField>
                <Button type="submit" loading={saving} disabled={!checkInCode.trim()}>
                  <LogIn className="h-4 w-4" />
                  Check in
                </Button>
              </form>
              {checkInMsg && (
                <p className="mt-3 text-sm text-muted-foreground">{checkInMsg}</p>
              )}
            </ContentSection>
          )}
          <ContentSection title="Recent attendance" description="Open visits can be checked out.">
            <DataTable
              columns={[
                {
                  key: "member",
                  header: "Member",
                  cell: (r: GymAttendance) => (
                    <div>
                      <p className="font-medium">{r.member_name}</p>
                      <p className="text-xs font-mono text-muted-foreground">
                        {r.membership_number}
                      </p>
                    </div>
                  ),
                },
                {
                  key: "in",
                  header: "Check-in",
                  cell: (r: GymAttendance) =>
                    r.check_in_at ? new Date(r.check_in_at).toLocaleString() : "—",
                },
                {
                  key: "out",
                  header: "Check-out",
                  cell: (r: GymAttendance) =>
                    r.check_out_at ? new Date(r.check_out_at).toLocaleString() : "—",
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (r: GymAttendance) => (
                    <Badge variant={r.is_open ? "warning" : "secondary"}>
                      {r.is_open ? "Inside" : "Out"}
                    </Badge>
                  ),
                },
                {
                  key: "actions",
                  header: "",
                  cell: (r: GymAttendance) =>
                    canCheckIn && r.is_open ? (
                      <Button variant="secondary" size="sm" onClick={() => void handleCheckOut(r)}>
                        <LogOut className="h-4 w-4" />
                        Check out
                      </Button>
                    ) : null,
                },
              ]}
              data={attendance}
              loading={attLoading}
              emptyMessage="No attendance yet."
            />
          </ContentSection>
        </>
      )}

      {tab === "trainers" && (
        <>
          {canManage && (
            <ContentSection
              title="Trainers"
              description="Profiles, specialties, and member assignments."
              action={
                <Button size="sm" onClick={() => setShowTrainerForm((v) => !v)}>
                  <Plus className="h-4 w-4" />
                  {showTrainerForm ? "Close" : "Add trainer"}
                </Button>
              }
            >
              {showTrainerForm && (
                <form
                  className="mb-4 rounded-xl border border-border/60 p-4"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setSaving(true);
                    try {
                      await gymApi.createTrainer({
                        full_name: trainerForm.full_name.trim(),
                        phone: trainerForm.phone || undefined,
                        specialty_codes: trainerForm.specialty_codes
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                        hourly_rate: Number(trainerForm.hourly_rate) || 0,
                      });
                      setTrainerForm({
                        full_name: "",
                        phone: "",
                        specialty_codes: "strength",
                        hourly_rate: "40",
                      });
                      setShowTrainerForm(false);
                      reloadTrainers();
                      reloadSummary();
                    } catch (err) {
                      await appDialog.alert(err instanceof Error ? err.message : "Failed");
                    } finally {
                      setSaving(false);
                    }
                  }}
                >
                  <FormGrid>
                    <FormField label="Full name" required>
                      <Input
                        required
                        value={trainerForm.full_name}
                        onChange={(e) =>
                          setTrainerForm({ ...trainerForm, full_name: e.target.value })
                        }
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                    <FormField label="Phone">
                      <Input
                        value={trainerForm.phone}
                        onChange={(e) =>
                          setTrainerForm({ ...trainerForm, phone: e.target.value })
                        }
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                    <FormField label="Hourly rate">
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        value={trainerForm.hourly_rate}
                        onChange={(e) =>
                          setTrainerForm({ ...trainerForm, hourly_rate: e.target.value })
                        }
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                    <FormField label="Specialties" hint="Comma-separated codes">
                      <Input
                        value={trainerForm.specialty_codes}
                        onChange={(e) =>
                          setTrainerForm({ ...trainerForm, specialty_codes: e.target.value })
                        }
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                  </FormGrid>
                  <Button type="submit" loading={saving} size="sm" className="mt-3">
                    Create trainer
                  </Button>
                </form>
              )}
              <DataTable
                columns={[
                  {
                    key: "name",
                    header: "Trainer",
                    cell: (r: GymTrainer) => (
                      <div>
                        <p className="font-medium">{r.full_name}</p>
                        <p className="text-xs font-mono text-muted-foreground">{r.code}</p>
                      </div>
                    ),
                  },
                  {
                    key: "specs",
                    header: "Specialties",
                    cell: (r: GymTrainer) =>
                      r.specialties.map((s) => s.name).join(", ") || "—",
                  },
                  {
                    key: "rate",
                    header: "Rate",
                    cell: (r: GymTrainer) =>
                      r.hourly_rate ? `${Number(r.hourly_rate).toFixed(2)}/hr` : "—",
                  },
                  { key: "phone", header: "Phone", cell: (r: GymTrainer) => r.phone || "—" },
                  {
                    key: "status",
                    header: "Status",
                    cell: (r: GymTrainer) => (
                      <Badge variant={r.status === "active" ? "success" : "secondary"}>
                        {r.status}
                      </Badge>
                    ),
                  },
                ]}
                data={trainers}
                emptyMessage="No trainers yet."
              />
            </ContentSection>
          )}
          {!canManage && (
            <ContentSection title="Trainers">
              <DataTable
                columns={[
                  {
                    key: "name",
                    header: "Trainer",
                    cell: (r: GymTrainer) => r.full_name,
                  },
                  {
                    key: "specs",
                    header: "Specialties",
                    cell: (r: GymTrainer) =>
                      r.specialties.map((s) => s.name).join(", ") || "—",
                  },
                ]}
                data={trainers}
                emptyMessage="No trainers yet."
              />
            </ContentSection>
          )}
          {canManage && (
            <ContentSection title="Assign member → trainer" description="Active coaching assignments.">
              <form
                className="mb-4"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSaving(true);
                  try {
                    await gymApi.assignTrainer(assignForm);
                    setAssignForm({ member_id: "", trainer_id: "" });
                    reloadTrainers();
                  } catch (err) {
                    await appDialog.alert(err instanceof Error ? err.message : "Assign failed");
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                <FormGrid>
                  <FormField label="Member" required>
                    <Select
                      value={assignForm.member_id || "none"}
                      onValueChange={(v) =>
                        setAssignForm({ ...assignForm, member_id: v === "none" ? "" : v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Member" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {members.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.full_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Trainer" required>
                    <Select
                      value={assignForm.trainer_id || "none"}
                      onValueChange={(v) =>
                        setAssignForm({ ...assignForm, trainer_id: v === "none" ? "" : v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Trainer" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {trainers.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.full_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                </FormGrid>
                <Button
                  type="submit"
                  loading={saving}
                  size="sm"
                  className="mt-3"
                  disabled={!assignForm.member_id || !assignForm.trainer_id}
                >
                  Assign
                </Button>
              </form>
              <DataTable
                columns={[
                  {
                    key: "pair",
                    header: "Assignment",
                    cell: (r: TrainerAssignment) => (
                      <span>
                        {r.member_name} → {r.trainer_name}
                      </span>
                    ),
                  },
                  {
                    key: "start",
                    header: "Start",
                    cell: (r: TrainerAssignment) => r.start_date || "—",
                  },
                  {
                    key: "actions",
                    header: "",
                    cell: (r: TrainerAssignment) => (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={async () => {
                          await gymApi.endAssignment(r.id);
                          reloadTrainers();
                        }}
                      >
                        End
                      </Button>
                    ),
                  },
                ]}
                data={assignments}
                emptyMessage="No active assignments."
              />
            </ContentSection>
          )}
          {canManage && (
            <ContentSection
              title="Personal training"
              description="Schedule PT sessions and bill via Invoice + CAE."
            >
              <form
                className="mb-4 rounded-xl border border-border/60 p-4"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSaving(true);
                  try {
                    await gymApi.schedulePtSession({
                      member_id: ptForm.member_id,
                      trainer_id: ptForm.trainer_id,
                      scheduled_at: new Date(ptForm.scheduled_at).toISOString(),
                      duration_minutes: Number(ptForm.duration_minutes) || 60,
                    });
                    setPtForm({
                      member_id: "",
                      trainer_id: "",
                      scheduled_at: "",
                      duration_minutes: "60",
                    });
                    reloadTrainers();
                  } catch (err) {
                    await appDialog.alert(err instanceof Error ? err.message : "Schedule failed");
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                <FormGrid>
                  <FormField label="Member" required>
                    <Select
                      value={ptForm.member_id || "none"}
                      onValueChange={(v) =>
                        setPtForm({ ...ptForm, member_id: v === "none" ? "" : v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Member" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {members.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.full_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Trainer" required>
                    <Select
                      value={ptForm.trainer_id || "none"}
                      onValueChange={(v) =>
                        setPtForm({ ...ptForm, trainer_id: v === "none" ? "" : v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Trainer" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {trainers.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.full_name}
                            {t.hourly_rate ? ` (${Number(t.hourly_rate).toFixed(0)}/hr)` : ""}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="When" required>
                    <Input
                      required
                      type="datetime-local"
                      value={ptForm.scheduled_at}
                      onChange={(e) => setPtForm({ ...ptForm, scheduled_at: e.target.value })}
                      className="h-10 rounded-xl"
                    />
                  </FormField>
                  <FormField label="Minutes">
                    <Input
                      type="number"
                      min={15}
                      step={15}
                      value={ptForm.duration_minutes}
                      onChange={(e) =>
                        setPtForm({ ...ptForm, duration_minutes: e.target.value })
                      }
                      className="h-10 rounded-xl"
                    />
                  </FormField>
                </FormGrid>
                <Button
                  type="submit"
                  loading={saving}
                  size="sm"
                  className="mt-3"
                  disabled={!ptForm.member_id || !ptForm.trainer_id || !ptForm.scheduled_at}
                >
                  Schedule session
                </Button>
              </form>
              <DataTable
                columns={[
                  {
                    key: "who",
                    header: "Session",
                    cell: (r: PTSession) => (
                      <div>
                        <p className="font-medium">
                          {r.member_name} · {r.trainer_name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {r.scheduled_at
                            ? new Date(r.scheduled_at).toLocaleString()
                            : "—"}{" "}
                          · {r.duration_minutes} min
                        </p>
                      </div>
                    ),
                  },
                  {
                    key: "amount",
                    header: "Amount",
                    cell: (r: PTSession) =>
                      formatCurrency(
                        r.invoice_id
                          ? Number(r.amount_charged ?? 0)
                          : Number(r.suggested_amount ?? 0)
                      ),
                  },
                  {
                    key: "status",
                    header: "Status",
                    cell: (r: PTSession) => (
                      <Badge variant={r.invoice_id ? "success" : "secondary"}>{r.status}</Badge>
                    ),
                  },
                  {
                    key: "actions",
                    header: "",
                    cell: (r: PTSession) =>
                      !r.invoice_id && r.status !== "cancelled" && r.status !== "no_show" ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={async () => {
                            const ok = await appDialog.confirm(
                              `Bill PT session for ${formatCurrency(
                                Number(r.suggested_amount ?? 0)
                              )} (cash)?`
                            );
                            if (!ok) return;
                            setSaving(true);
                            try {
                              const res = await gymApi.checkoutPtSession(r.id, {
                                payment_method: "cash",
                              });
                              await appDialog.alert(
                                `Invoiced ${res.data.invoice.invoice_number} · ${formatCurrency(
                                  Number(res.data.invoice.total_amount)
                                )}`
                              );
                              reloadTrainers();
                            } catch (err) {
                              await appDialog.alert(
                                err instanceof Error ? err.message : "Billing failed"
                              );
                            } finally {
                              setSaving(false);
                            }
                          }}
                        >
                          <CreditCard className="h-4 w-4" />
                          Complete &amp; bill
                        </Button>
                      ) : r.invoice_id ? (
                        <span className="text-xs text-muted-foreground">Billed</span>
                      ) : null,
                  },
                ]}
                data={ptSessions}
                emptyMessage="No PT sessions yet."
              />
            </ContentSection>
          )}
        </>
      )}

      {tab === "classes" && (
        <>
          {canManage && (
            <ContentSection
              title="Class templates"
              description="Reusable class types with default capacity."
              action={
                <Button size="sm" onClick={() => setShowClassForm((v) => !v)}>
                  <Plus className="h-4 w-4" />
                  {showClassForm ? "Close" : "Add class"}
                </Button>
              }
            >
              {showClassForm && (
                <form
                  className="mb-4 rounded-xl border border-border/60 p-4"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setSaving(true);
                    try {
                      await gymApi.createClass({
                        code: classForm.code.trim(),
                        name: classForm.name.trim(),
                        default_capacity: Number(classForm.default_capacity) || 15,
                        drop_in_price: Number(classForm.drop_in_price) || 0,
                      });
                      setClassForm({
                        code: "",
                        name: "",
                        default_capacity: "15",
                        drop_in_price: "15",
                      });
                      setShowClassForm(false);
                      reloadClasses();
                      reloadSummary();
                    } catch (err) {
                      await appDialog.alert(err instanceof Error ? err.message : "Failed");
                    } finally {
                      setSaving(false);
                    }
                  }}
                >
                  <FormGrid>
                    <FormField label="Code" required>
                      <Input
                        required
                        value={classForm.code}
                        onChange={(e) => setClassForm({ ...classForm, code: e.target.value })}
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                    <FormField label="Name" required>
                      <Input
                        required
                        value={classForm.name}
                        onChange={(e) => setClassForm({ ...classForm, name: e.target.value })}
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                    <FormField label="Default capacity">
                      <Input
                        type="number"
                        min={1}
                        value={classForm.default_capacity}
                        onChange={(e) =>
                          setClassForm({ ...classForm, default_capacity: e.target.value })
                        }
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                    <FormField label="Drop-in price">
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        value={classForm.drop_in_price}
                        onChange={(e) =>
                          setClassForm({ ...classForm, drop_in_price: e.target.value })
                        }
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                  </FormGrid>
                  <Button type="submit" loading={saving} size="sm" className="mt-3">
                    Create class
                  </Button>
                </form>
              )}
              <DataTable
                columns={[
                  {
                    key: "name",
                    header: "Class",
                    cell: (r: GymClassTemplate) => (
                      <div>
                        <p className="font-medium">{r.name}</p>
                        <p className="text-xs font-mono text-muted-foreground">{r.code}</p>
                      </div>
                    ),
                  },
                  {
                    key: "cap",
                    header: "Capacity",
                    cell: (r: GymClassTemplate) => r.default_capacity,
                  },
                  {
                    key: "price",
                    header: "Drop-in",
                    cell: (r: GymClassTemplate) =>
                      formatCurrency(Number(r.drop_in_price ?? 0)),
                  },
                  {
                    key: "dur",
                    header: "Duration",
                    cell: (r: GymClassTemplate) => `${r.duration_minutes} min`,
                  },
                ]}
                data={classTemplates}
                emptyMessage="No class templates yet."
              />
            </ContentSection>
          )}

          <ContentSection
            title="Upcoming sessions"
            description="Schedules with live capacity and waitlist."
          >
            {canManage && (
              <form
                className="mb-4 rounded-xl border border-border/60 p-4"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSaving(true);
                  try {
                    await gymApi.createClassSchedule({
                      gym_class_id: schedForm.gym_class_id,
                      starts_at: new Date(schedForm.starts_at).toISOString(),
                      capacity: schedForm.capacity
                        ? Number(schedForm.capacity)
                        : undefined,
                    });
                    setSchedForm({ gym_class_id: "", starts_at: "", capacity: "" });
                    reloadClasses();
                    reloadSummary();
                  } catch (err) {
                    await appDialog.alert(err instanceof Error ? err.message : "Schedule failed");
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                <FormGrid>
                  <FormField label="Class" required>
                    <Select
                      value={schedForm.gym_class_id || "none"}
                      onValueChange={(v) =>
                        setSchedForm({ ...schedForm, gym_class_id: v === "none" ? "" : v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Class" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {classTemplates.map((c) => (
                          <SelectItem key={c.id} value={c.id}>
                            {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Starts at" required>
                    <Input
                      type="datetime-local"
                      required
                      value={schedForm.starts_at}
                      onChange={(e) =>
                        setSchedForm({ ...schedForm, starts_at: e.target.value })
                      }
                      className="h-10 rounded-xl"
                    />
                  </FormField>
                  <FormField label="Capacity override">
                    <Input
                      type="number"
                      min={1}
                      value={schedForm.capacity}
                      onChange={(e) =>
                        setSchedForm({ ...schedForm, capacity: e.target.value })
                      }
                      className="h-10 rounded-xl"
                    />
                  </FormField>
                </FormGrid>
                <Button
                  type="submit"
                  loading={saving}
                  size="sm"
                  className="mt-3"
                  disabled={!schedForm.gym_class_id || !schedForm.starts_at}
                >
                  Schedule session
                </Button>
              </form>
            )}
            <DataTable
              columns={[
                {
                  key: "class",
                  header: "Session",
                  cell: (r: GymClassSchedule) => (
                    <div>
                      <p className="font-medium">{r.class_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {r.starts_at
                          ? new Date(r.starts_at).toLocaleString()
                          : "—"}
                      </p>
                    </div>
                  ),
                },
                {
                  key: "fill",
                  header: "Fill",
                  cell: (r: GymClassSchedule) =>
                    `${r.confirmed_count}/${r.capacity}` +
                    (r.waitlisted_count ? ` (+${r.waitlisted_count} wait)` : ""),
                },
                {
                  key: "spots",
                  header: "Spots left",
                  cell: (r: GymClassSchedule) => r.spots_remaining,
                },
              ]}
              data={classSchedules}
              emptyMessage="No upcoming sessions."
            />
          </ContentSection>

          {(canManage || canCheckIn) && (
            <ContentSection title="Book a spot" description="Confirms if under capacity; else waitlists.">
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSaving(true);
                  try {
                    const res = await gymApi.bookClass({
                      schedule_id: bookForm.schedule_id,
                      member_id: bookForm.member_id,
                      allow_waitlist: true,
                    });
                    await appDialog.alert(
                      `Booking ${res.data.status} for ${res.data.member_name}`
                    );
                    setBookForm({ schedule_id: "", member_id: "" });
                    reloadClasses();
                    reloadSummary();
                  } catch (err) {
                    await appDialog.alert(err instanceof Error ? err.message : "Book failed");
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                <FormGrid>
                  <FormField label="Session" required>
                    <Select
                      value={bookForm.schedule_id || "none"}
                      onValueChange={(v) =>
                        setBookForm({ ...bookForm, schedule_id: v === "none" ? "" : v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Session" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {classSchedules.map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            {s.class_name} —{" "}
                            {s.starts_at
                              ? new Date(s.starts_at).toLocaleString()
                              : "?"}{" "}
                            ({s.spots_remaining} left)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Member" required>
                    <Select
                      value={bookForm.member_id || "none"}
                      onValueChange={(v) =>
                        setBookForm({ ...bookForm, member_id: v === "none" ? "" : v })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Member" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {members.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.full_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                </FormGrid>
                <Button
                  type="submit"
                  loading={saving}
                  size="sm"
                  className="mt-3"
                  disabled={!bookForm.schedule_id || !bookForm.member_id}
                >
                  Book
                </Button>
              </form>
            </ContentSection>
          )}
          {canManage && (
            <ContentSection
              title="Confirmed bookings"
              description="Bill drop-in fees via Invoice + CAE (GYM_CLASS_REVENUE)."
            >
              <DataTable
                columns={[
                  {
                    key: "who",
                    header: "Booking",
                    cell: (r: GymClassBooking) => (
                      <div>
                        <p className="font-medium">
                          {r.member_name} · {r.class_name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {r.starts_at ? new Date(r.starts_at).toLocaleString() : "—"}
                        </p>
                      </div>
                    ),
                  },
                  {
                    key: "amount",
                    header: "Amount",
                    cell: (r: GymClassBooking) =>
                      formatCurrency(
                        r.invoice_id
                          ? Number(r.amount_charged ?? 0)
                          : Number(r.drop_in_price ?? 0)
                      ),
                  },
                  {
                    key: "status",
                    header: "Status",
                    cell: (r: GymClassBooking) => (
                      <Badge variant={r.invoice_id ? "success" : "secondary"}>
                        {r.invoice_id ? "billed" : r.status}
                      </Badge>
                    ),
                  },
                  {
                    key: "actions",
                    header: "",
                    cell: (r: GymClassBooking) =>
                      !r.invoice_id ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={async () => {
                            const ok = await appDialog.confirm(
                              `Bill drop-in for ${formatCurrency(
                                Number(r.drop_in_price ?? 0)
                              )} (cash)?`
                            );
                            if (!ok) return;
                            setSaving(true);
                            try {
                              const res = await gymApi.checkoutClassBooking(r.id, {
                                payment_method: "cash",
                              });
                              await appDialog.alert(
                                `Invoiced ${res.data.invoice.invoice_number} · ${formatCurrency(
                                  Number(res.data.invoice.total_amount)
                                )}`
                              );
                              reloadClasses();
                            } catch (err) {
                              await appDialog.alert(
                                err instanceof Error ? err.message : "Billing failed"
                              );
                            } finally {
                              setSaving(false);
                            }
                          }}
                        >
                          <CreditCard className="h-4 w-4" />
                          Bill drop-in
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">Billed</span>
                      ),
                  },
                ]}
                data={classBookings}
                emptyMessage="No confirmed bookings."
              />
            </ContentSection>
          )}
        </>
      )}

      {tab === "workouts" && (
        <>
          {canManage && (
            <ContentSection
              title="Exercise library"
              description="Reusable exercises for workout plans."
              action={
                <Button size="sm" onClick={() => setShowExerciseForm((v) => !v)}>
                  <Plus className="h-4 w-4" />
                  {showExerciseForm ? "Close" : "Add exercise"}
                </Button>
              }
            >
              {showExerciseForm && (
                <form
                  className="mb-4 rounded-xl border border-border/60 p-4"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setSaving(true);
                    try {
                      await gymApi.createExercise({
                        code: exerciseForm.code.trim(),
                        name: exerciseForm.name.trim(),
                        muscle_group: exerciseForm.muscle_group,
                      });
                      setExerciseForm({ code: "", name: "", muscle_group: "chest" });
                      setShowExerciseForm(false);
                      reloadWorkouts(progressMemberId || undefined);
                      reloadSummary();
                    } catch (err) {
                      await appDialog.alert(err instanceof Error ? err.message : "Failed");
                    } finally {
                      setSaving(false);
                    }
                  }}
                >
                  <FormGrid>
                    <FormField label="Code" required>
                      <Input
                        required
                        value={exerciseForm.code}
                        onChange={(e) =>
                          setExerciseForm({ ...exerciseForm, code: e.target.value })
                        }
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                    <FormField label="Name" required>
                      <Input
                        required
                        value={exerciseForm.name}
                        onChange={(e) =>
                          setExerciseForm({ ...exerciseForm, name: e.target.value })
                        }
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                    <FormField label="Muscle group">
                      <Input
                        value={exerciseForm.muscle_group}
                        onChange={(e) =>
                          setExerciseForm({ ...exerciseForm, muscle_group: e.target.value })
                        }
                        className="h-10 rounded-xl"
                      />
                    </FormField>
                  </FormGrid>
                  <Button type="submit" loading={saving} size="sm" className="mt-3">
                    Create exercise
                  </Button>
                </form>
              )}
              <DataTable
                columns={[
                  {
                    key: "name",
                    header: "Exercise",
                    cell: (r: GymExercise) => (
                      <div>
                        <p className="font-medium">{r.name}</p>
                        <p className="text-xs font-mono text-muted-foreground">{r.code}</p>
                      </div>
                    ),
                  },
                  {
                    key: "group",
                    header: "Muscle",
                    cell: (r: GymExercise) => r.muscle_group || "—",
                  },
                ]}
                data={exercises}
                emptyMessage="No exercises yet."
              />
            </ContentSection>
          )}

          {canManage && (
            <ContentSection
              title="Workout plans"
              description="Multi-day templates assigned to members."
            >
              <form
                className="mb-4 rounded-xl border border-border/60 p-4"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSaving(true);
                  try {
                    await gymApi.createWorkoutPlan({
                      code: planFormWo.code.trim(),
                      name: planFormWo.name.trim(),
                      days: planFormWo.exercise_id
                        ? [
                            {
                              day_number: 1,
                              name: "Day 1",
                              exercises: [
                                {
                                  exercise_id: planFormWo.exercise_id,
                                  sets: 3,
                                  reps: "10",
                                },
                              ],
                            },
                          ]
                        : [],
                    });
                    setPlanFormWo({ code: "", name: "", exercise_id: "" });
                    reloadWorkouts(progressMemberId || undefined);
                    reloadSummary();
                  } catch (err) {
                    await appDialog.alert(err instanceof Error ? err.message : "Failed");
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                <FormGrid>
                  <FormField label="Code" required>
                    <Input
                      required
                      value={planFormWo.code}
                      onChange={(e) => setPlanFormWo({ ...planFormWo, code: e.target.value })}
                      className="h-10 rounded-xl"
                    />
                  </FormField>
                  <FormField label="Name" required>
                    <Input
                      required
                      value={planFormWo.name}
                      onChange={(e) => setPlanFormWo({ ...planFormWo, name: e.target.value })}
                      className="h-10 rounded-xl"
                    />
                  </FormField>
                  <FormField label="Day 1 exercise">
                    <Select
                      value={planFormWo.exercise_id || "none"}
                      onValueChange={(v) =>
                        setPlanFormWo({
                          ...planFormWo,
                          exercise_id: v === "none" ? "" : v,
                        })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Optional" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        {exercises.map((ex) => (
                          <SelectItem key={ex.id} value={ex.id}>
                            {ex.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                </FormGrid>
                <Button type="submit" loading={saving} size="sm" className="mt-3">
                  Create plan
                </Button>
              </form>
              <DataTable
                columns={[
                  {
                    key: "name",
                    header: "Plan",
                    cell: (r: GymWorkoutPlan) => (
                      <div>
                        <p className="font-medium">{r.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {r.day_count} day(s) · {r.goal}
                        </p>
                      </div>
                    ),
                  },
                  { key: "weeks", header: "Weeks", cell: (r: GymWorkoutPlan) => r.duration_weeks },
                ]}
                data={workoutPlans}
                emptyMessage="No workout plans yet."
              />
            </ContentSection>
          )}

          {canManage && (
            <ContentSection title="Assign plan to member">
              <form
                className="mb-4"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSaving(true);
                  try {
                    await gymApi.assignWorkoutPlan(assignWoForm);
                    setAssignWoForm({ member_id: "", workout_plan_id: "" });
                    reloadWorkouts(progressMemberId || undefined);
                    reloadSummary();
                  } catch (err) {
                    await appDialog.alert(err instanceof Error ? err.message : "Assign failed");
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                <FormGrid>
                  <FormField label="Member" required>
                    <Select
                      value={assignWoForm.member_id || "none"}
                      onValueChange={(v) =>
                        setAssignWoForm({
                          ...assignWoForm,
                          member_id: v === "none" ? "" : v,
                        })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Member" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {members.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.full_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Plan" required>
                    <Select
                      value={assignWoForm.workout_plan_id || "none"}
                      onValueChange={(v) =>
                        setAssignWoForm({
                          ...assignWoForm,
                          workout_plan_id: v === "none" ? "" : v,
                        })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Plan" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {workoutPlans.map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                </FormGrid>
                <Button
                  type="submit"
                  loading={saving}
                  size="sm"
                  className="mt-3"
                  disabled={!assignWoForm.member_id || !assignWoForm.workout_plan_id}
                >
                  Assign
                </Button>
              </form>
              <DataTable
                columns={[
                  {
                    key: "pair",
                    header: "Assignment",
                    cell: (r: GymWorkoutAssignment) => `${r.member_name} → ${r.plan_name}`,
                  },
                  {
                    key: "start",
                    header: "Start",
                    cell: (r: GymWorkoutAssignment) => r.start_date || "—",
                  },
                ]}
                data={workoutAssignments}
                emptyMessage="No active assignments."
              />
            </ContentSection>
          )}

          <ContentSection
            title="Body progress"
            description="Measurements and weight trend."
          >
            <FormGrid>
              <FormField label="Member for chart">
                <Select
                  value={progressMemberId || "none"}
                  onValueChange={(v) => {
                    const id = v === "none" ? "" : v;
                    setProgressMemberId(id);
                    reloadWorkouts(id || undefined);
                  }}
                >
                  <SelectTrigger className="h-10 rounded-xl">
                    <SelectValue placeholder="Select member" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">All / none</SelectItem>
                    {members.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
            </FormGrid>

            {progressMemberId && chartPoints.length > 0 && (
              <div className="mt-4">
                <ChartCard title="Weight (kg)" height={220}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartPoints}>
                      <CartesianGrid strokeDasharray="4 4" stroke="hsl(var(--border))" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke={chartColors.primary}
                        strokeWidth={2}
                        dot={{ r: 3 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>
            )}

            {canManage && (
              <form
                className="mt-4 rounded-xl border border-border/60 p-4"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSaving(true);
                  try {
                    await gymApi.recordBodyMeasurement({
                      member_id: measureForm.member_id,
                      weight_kg: measureForm.weight_kg
                        ? Number(measureForm.weight_kg)
                        : undefined,
                      waist_cm: measureForm.waist_cm
                        ? Number(measureForm.waist_cm)
                        : undefined,
                    });
                    const mid = measureForm.member_id;
                    setMeasureForm({ member_id: mid, weight_kg: "", waist_cm: "" });
                    setProgressMemberId(mid);
                    reloadWorkouts(mid);
                    reloadSummary();
                  } catch (err) {
                    await appDialog.alert(err instanceof Error ? err.message : "Failed");
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                <FormGrid>
                  <FormField label="Member" required>
                    <Select
                      value={measureForm.member_id || "none"}
                      onValueChange={(v) =>
                        setMeasureForm({
                          ...measureForm,
                          member_id: v === "none" ? "" : v,
                        })
                      }
                    >
                      <SelectTrigger className="h-10 rounded-xl">
                        <SelectValue placeholder="Member" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select…</SelectItem>
                        {members.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.full_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Weight (kg)">
                    <Input
                      type="number"
                      step="0.1"
                      value={measureForm.weight_kg}
                      onChange={(e) =>
                        setMeasureForm({ ...measureForm, weight_kg: e.target.value })
                      }
                      className="h-10 rounded-xl"
                    />
                  </FormField>
                  <FormField label="Waist (cm)">
                    <Input
                      type="number"
                      step="0.1"
                      value={measureForm.waist_cm}
                      onChange={(e) =>
                        setMeasureForm({ ...measureForm, waist_cm: e.target.value })
                      }
                      className="h-10 rounded-xl"
                    />
                  </FormField>
                </FormGrid>
                <Button
                  type="submit"
                  loading={saving}
                  size="sm"
                  className="mt-3"
                  disabled={!measureForm.member_id}
                >
                  Record measurement
                </Button>
              </form>
            )}

            <DataTable
              columns={[
                {
                  key: "member",
                  header: "Member",
                  cell: (r: GymBodyMeasurement) => r.member_name,
                },
                {
                  key: "when",
                  header: "Date",
                  cell: (r: GymBodyMeasurement) =>
                    r.measured_at ? new Date(r.measured_at).toLocaleDateString() : "—",
                },
                {
                  key: "weight",
                  header: "Weight",
                  cell: (r: GymBodyMeasurement) =>
                    r.weight_kg != null ? `${r.weight_kg} kg` : "—",
                },
                {
                  key: "waist",
                  header: "Waist",
                  cell: (r: GymBodyMeasurement) =>
                    r.waist_cm != null ? `${r.waist_cm} cm` : "—",
                },
              ]}
              data={measurements}
              emptyMessage="No measurements yet."
            />
          </ContentSection>
        </>
      )}
    </PageLayout>
  );
}
