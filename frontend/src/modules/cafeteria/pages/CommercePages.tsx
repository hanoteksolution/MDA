import { useCallback, useEffect, useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/store/authStore";
import { apiRequest, qs } from "@/services/api/http";
import type { ApiResponse } from "@/types/models";
import type { ApiListResponse } from "@/types/models/catalog";
import { formatCurrency } from "@/utils/cn";

type Promo = {
  id: string;
  name: string;
  code: string;
  promotion_type: string;
  percent_off: number;
  amount_off: number;
  coupon_code: string;
  is_active: boolean;
};

type Combo = {
  id: string;
  name: string;
  code: string;
  combo_price: number;
  regular_total: number;
  savings: number;
  is_active: boolean;
};

type Reservation = {
  id: string;
  customer_name: string;
  phone: string;
  reserved_for: string;
  guests: number;
  table_code: string | null;
  status: string;
};

type Shift = {
  id: string;
  user_name: string;
  role: string;
  planned_start: string;
  planned_end: string;
  status: string;
};

const commerceApi = {
  promotions: (branchId?: string) =>
    apiRequest<ApiListResponse<Promo>>(`/restaurant/promotions/${qs({ branch_id: branchId, page: 1 })}`),
  createPromotion: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Promo>>("/restaurant/promotions/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updatePromotion: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Promo>>(`/restaurant/promotions/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  archivePromotion: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/promotions/${id}/`, {
      method: "DELETE",
    }),
  combos: (branchId?: string) =>
    apiRequest<ApiListResponse<Combo>>(`/restaurant/combos/${qs({ branch_id: branchId, page: 1 })}`),
  createCombo: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Combo>>("/restaurant/combos/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCombo: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Combo>>(`/restaurant/combos/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  archiveCombo: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/combos/${id}/`, {
      method: "DELETE",
    }),
  reservations: (branchId?: string) =>
    apiRequest<ApiListResponse<Reservation>>(
      `/restaurant/reservations/${qs({ branch_id: branchId, page: 1 })}`
    ),
  createReservation: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Reservation>>("/restaurant/reservations/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  reservationStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<Reservation>>(`/restaurant/reservations/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
  shifts: (branchId?: string) =>
    apiRequest<ApiListResponse<Shift>>(`/restaurant/shifts/${qs({ branch_id: branchId, page: 1 })}`),
  createShift: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Shift>>("/restaurant/shifts/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  shiftAction: (id: string, action: "open" | "close") =>
    apiRequest<ApiResponse<Shift>>(`/restaurant/shifts/${id}/${action}/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  loyalty: (branchId: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(
      `/restaurant/loyalty/program/${qs({ branch_id: branchId })}`
    ),
  updateLoyalty: (branchId: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(
      `/restaurant/loyalty/program/${qs({ branch_id: branchId })}`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),
};

export function PromotionsPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [rows, setRows] = useState<Promo[]>([]);
  const [form, setForm] = useState({
    name: "",
    promotion_type: "percent",
    percent_off: "10",
    amount_off: "0",
    coupon_code: "",
  });
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const res = await commerceApi.promotions(branchId);
      setRows(res.data.results || []);
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const create = async () => {
    if (!branchId || !form.name) return;
    await commerceApi.createPromotion({ ...form, branch_id: branchId });
    setForm({ name: "", promotion_type: "percent", percent_off: "10", amount_off: "0", coupon_code: "" });
    await reload();
  };

  const columns: Column<Promo>[] = [
    { key: "name", header: "Name", cell: (r) => r.name },
    { key: "type", header: "Type", cell: (r) => r.promotion_type },
    {
      key: "value",
      header: "Value",
      cell: (r) =>
        r.promotion_type === "fixed" || (r.promotion_type === "coupon" && r.amount_off)
          ? formatCurrency(r.amount_off)
          : `${r.percent_off}%`,
    },
    { key: "coupon", header: "Coupon", cell: (r) => r.coupon_code || "—" },
    {
      key: "active",
      header: "Status",
      cell: (r) => <Badge variant={r.is_active ? "success" : "outline"}>{r.is_active ? "Active" : "Off"}</Badge>,
    },
    {
      key: "actions",
      header: "",
      cell: (r) => (
        <div className="flex justify-end gap-1">
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              void commerceApi
                .updatePromotion(r.id, { is_active: !r.is_active })
                .then(reload)
            }
          >
            {r.is_active ? "Disable" : "Enable"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => void commerceApi.archivePromotion(r.id).then(reload)}
          >
            Archive
          </Button>
        </div>
      ),
    },
  ];

  return (
    <PageLayout title="Promotions & Coupons" description="Happy hour, percent, fixed, and coupon deals.">
      <ContentSection title="New promotion">
        <FormGrid>
          <FormField label="Name" required>
            <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
          </FormField>
          <FormField label="Type">
            <Select value={form.promotion_type} onValueChange={(v) => setForm((f) => ({ ...f, promotion_type: v }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="percent">Percent</SelectItem>
                <SelectItem value="fixed">Fixed</SelectItem>
                <SelectItem value="coupon">Coupon</SelectItem>
                <SelectItem value="happy_hour">Happy hour</SelectItem>
                <SelectItem value="bogo">BOGO</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Percent off">
            <Input value={form.percent_off} onChange={(e) => setForm((f) => ({ ...f, percent_off: e.target.value }))} />
          </FormField>
          <FormField label="Amount off">
            <Input value={form.amount_off} onChange={(e) => setForm((f) => ({ ...f, amount_off: e.target.value }))} />
          </FormField>
          <FormField label="Coupon code">
            <Input value={form.coupon_code} onChange={(e) => setForm((f) => ({ ...f, coupon_code: e.target.value }))} />
          </FormField>
        </FormGrid>
        <Button className="mt-4" onClick={() => void create()}>Create promotion</Button>
      </ContentSection>
      <ContentSection title="Active promotions">
        <DataTable columns={columns} data={rows} loading={loading} emptyMessage="No promotions yet." />
      </ContentSection>
    </PageLayout>
  );
}

export function CombosPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [rows, setRows] = useState<Combo[]>([]);
  const [menuItems, setMenuItems] = useState<{ id: string; name: string; unit_price: number }[]>([]);
  const [form, setForm] = useState({
    name: "",
    code: "",
    combo_price: "",
    item_a: "",
    item_b: "",
  });
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const [comboRes, itemsRes] = await Promise.all([
        commerceApi.combos(branchId),
        apiRequest<ApiListResponse<{ id: string; name: string; unit_price: number }>>(
          `/restaurant/items/${qs({ page: 1, branch_id: branchId, page_size: 100 })}`
        ),
      ]);
      setRows(comboRes.data.results || []);
      setMenuItems(itemsRes.data.results || []);
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const create = async () => {
    if (!branchId || !form.name) return;
    const items = [form.item_a, form.item_b]
      .filter(Boolean)
      .map((menu_item_id, idx) => ({ menu_item_id, quantity: 1, sort_order: (idx + 1) * 100 }));
    await commerceApi.createCombo({
      name: form.name,
      code: form.code,
      combo_price: form.combo_price,
      branch_id: branchId,
      items,
    });
    setForm({ name: "", code: "", combo_price: "", item_a: "", item_b: "" });
    await reload();
  };

  const columns: Column<Combo>[] = [
    { key: "name", header: "Combo", cell: (r) => r.name },
    { key: "code", header: "Code", cell: (r) => r.code },
    { key: "price", header: "Combo price", cell: (r) => formatCurrency(r.combo_price) },
    { key: "regular", header: "Regular", cell: (r) => formatCurrency(r.regular_total) },
    { key: "save", header: "Savings", cell: (r) => formatCurrency(r.savings) },
    {
      key: "actions",
      header: "",
      cell: (r) => (
        <div className="flex justify-end gap-1">
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              void commerceApi.updateCombo(r.id, { is_active: !r.is_active }).then(reload)
            }
          >
            {r.is_active ? "Disable" : "Enable"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => void commerceApi.archiveCombo(r.id).then(reload)}
          >
            Archive
          </Button>
        </div>
      ),
    },
  ];

  return (
    <PageLayout title="Combos" description="Bundled menu deals with component inventory tracking.">
      <ContentSection title="New combo">
        <FormGrid>
          <FormField label="Name" required>
            <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
          </FormField>
          <FormField label="Code">
            <Input value={form.code} onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))} />
          </FormField>
          <FormField label="Combo price">
            <Input value={form.combo_price} onChange={(e) => setForm((f) => ({ ...f, combo_price: e.target.value }))} />
          </FormField>
          <FormField label="Item 1">
            <Select value={form.item_a || undefined} onValueChange={(v) => setForm((f) => ({ ...f, item_a: v }))}>
              <SelectTrigger><SelectValue placeholder="Select item" /></SelectTrigger>
              <SelectContent>
                {menuItems.map((m) => (
                  <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Item 2">
            <Select value={form.item_b || undefined} onValueChange={(v) => setForm((f) => ({ ...f, item_b: v }))}>
              <SelectTrigger><SelectValue placeholder="Select item" /></SelectTrigger>
              <SelectContent>
                {menuItems.map((m) => (
                  <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        </FormGrid>
        <Button className="mt-4" onClick={() => void create()}>Create combo</Button>
      </ContentSection>
      <ContentSection title="Combos">
        <DataTable columns={columns} data={rows} loading={loading} emptyMessage="No combos yet." />
      </ContentSection>
    </PageLayout>
  );
}

export function ReservationsPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [rows, setRows] = useState<Reservation[]>([]);
  const [form, setForm] = useState({
    customer_name: "",
    phone: "",
    reserved_for: "",
    guests: "2",
  });
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const res = await commerceApi.reservations(branchId);
      setRows(res.data.results || []);
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const create = async () => {
    if (!branchId || !form.customer_name || !form.reserved_for) return;
    await commerceApi.createReservation({ ...form, branch_id: branchId });
    setForm({ customer_name: "", phone: "", reserved_for: "", guests: "2" });
    await reload();
  };

  const columns: Column<Reservation>[] = [
    { key: "customer_name", header: "Guest", cell: (r) => r.customer_name },
    { key: "phone", header: "Phone", cell: (r) => r.phone || "—" },
    { key: "when", header: "When", cell: (r) => r.reserved_for },
    { key: "guests", header: "Guests", cell: (r) => r.guests },
    { key: "table", header: "Table", cell: (r) => r.table_code || "—" },
    { key: "status", header: "Status", cell: (r) => <Badge variant="secondary">{r.status}</Badge> },
    {
      key: "actions",
      header: "",
      cell: (r) => (
        <div className="flex gap-1 justify-end">
          {r.status === "pending" ? (
            <Button size="sm" variant="outline" onClick={() => void commerceApi.reservationStatus(r.id, "confirmed").then(reload)}>
              Confirm
            </Button>
          ) : null}
          {r.status === "confirmed" ? (
            <Button size="sm" onClick={() => void commerceApi.reservationStatus(r.id, "seated").then(reload)}>
              Seat
            </Button>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <PageLayout title="Reservations" description="Table bookings with conflict prevention.">
      <ContentSection title="New reservation">
        <FormGrid>
          <FormField label="Guest name" required>
            <Input value={form.customer_name} onChange={(e) => setForm((f) => ({ ...f, customer_name: e.target.value }))} />
          </FormField>
          <FormField label="Phone">
            <Input value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
          </FormField>
          <FormField label="Date & time" required>
            <Input type="datetime-local" value={form.reserved_for} onChange={(e) => setForm((f) => ({ ...f, reserved_for: e.target.value }))} />
          </FormField>
          <FormField label="Guests">
            <Input value={form.guests} onChange={(e) => setForm((f) => ({ ...f, guests: e.target.value }))} />
          </FormField>
        </FormGrid>
        <Button className="mt-4" onClick={() => void create()}>Book table</Button>
      </ContentSection>
      <ContentSection title="Upcoming">
        <DataTable columns={columns} data={rows} loading={loading} emptyMessage="No reservations." />
      </ContentSection>
    </PageLayout>
  );
}

export function ShiftsPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const userId = useAuthStore((s) => s.user?.id);
  const [rows, setRows] = useState<Shift[]>([]);
  const [loading, setLoading] = useState(true);
  const [plannedStart, setPlannedStart] = useState("");
  const [plannedEnd, setPlannedEnd] = useState("");

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const res = await commerceApi.shifts(branchId);
      setRows(res.data.results || []);
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const create = async () => {
    if (!branchId || !userId || !plannedStart || !plannedEnd) return;
    await commerceApi.createShift({
      branch_id: branchId,
      user_id: userId,
      role: "barista",
      planned_start: plannedStart,
      planned_end: plannedEnd,
    });
    await reload();
  };

  const columns: Column<Shift>[] = [
    { key: "user", header: "Staff", cell: (r) => r.user_name },
    { key: "role", header: "Role", cell: (r) => r.role },
    { key: "start", header: "Start", cell: (r) => r.planned_start },
    { key: "end", header: "End", cell: (r) => r.planned_end },
    { key: "status", header: "Status", cell: (r) => <Badge variant="secondary">{r.status}</Badge> },
    {
      key: "actions",
      header: "",
      cell: (r) => (
        <div className="flex gap-1 justify-end">
          {r.status === "scheduled" ? (
            <Button size="sm" onClick={() => void commerceApi.shiftAction(r.id, "open").then(reload)}>
              Open
            </Button>
          ) : null}
          {r.status === "open" ? (
            <Button size="sm" variant="outline" onClick={() => void commerceApi.shiftAction(r.id, "close").then(reload)}>
              Close
            </Button>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <PageLayout title="Shifts" description="Barista, cashier, and kitchen shift schedule.">
      <ContentSection title="Schedule shift">
        <FormGrid>
          <FormField label="Start" required>
            <Input type="datetime-local" value={plannedStart} onChange={(e) => setPlannedStart(e.target.value)} />
          </FormField>
          <FormField label="End" required>
            <Input type="datetime-local" value={plannedEnd} onChange={(e) => setPlannedEnd(e.target.value)} />
          </FormField>
        </FormGrid>
        <Button className="mt-4" onClick={() => void create()}>Add shift</Button>
      </ContentSection>
      <ContentSection title="Shifts">
        <DataTable columns={columns} data={rows} loading={loading} emptyMessage="No shifts scheduled." />
      </ContentSection>
    </PageLayout>
  );
}

export function LoyaltyPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [program, setProgram] = useState<Record<string, unknown> | null>(null);
  const [pointsPer, setPointsPer] = useState("1");
  const [redeemPts, setRedeemPts] = useState("100");
  const [redeemVal, setRedeemVal] = useState("5");
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    if (!branchId) return;
    const res = await commerceApi.loyalty(branchId);
    setProgram(res.data);
    setPointsPer(String(res.data.points_per_currency ?? 1));
    setRedeemPts(String(res.data.redemption_points ?? 100));
    setRedeemVal(String(res.data.redemption_value ?? 5));
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const save = async () => {
    if (!branchId) return;
    setSaving(true);
    try {
      const res = await commerceApi.updateLoyalty(branchId, {
        points_per_currency: Number(pointsPer || 1),
        redemption_points: Number(redeemPts || 0),
        redemption_value: Number(redeemVal || 0),
      });
      setProgram(res.data);
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageLayout title="Loyalty" description="Points, tiers, and redemption policy (configurable).">
      <ContentSection title="Program">
        {program ? (
          <div className="space-y-4 text-sm">
            <p className="text-lg font-semibold">{String(program.name || "Café Rewards")}</p>
            <FormGrid>
              <FormField label="Points per currency">
                <Input value={pointsPer} onChange={(e) => setPointsPer(e.target.value)} />
              </FormField>
              <FormField label="Redemption points">
                <Input value={redeemPts} onChange={(e) => setRedeemPts(e.target.value)} />
              </FormField>
              <FormField label="Redemption value">
                <Input value={redeemVal} onChange={(e) => setRedeemVal(e.target.value)} />
              </FormField>
            </FormGrid>
            <Button loading={saving} onClick={() => void save()}>
              Save program
            </Button>
            <div className="flex flex-wrap gap-2 pt-2">
              {((program.tiers as { name: string; min_points: number }[]) || []).map((t) => (
                <Badge key={t.name} variant="outline">
                  {t.name} · {t.min_points}+ pts
                </Badge>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Loading program…</p>
        )}
      </ContentSection>
    </PageLayout>
  );
}
