import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { FormActions, FormPageLayout } from "@/components/forms/FormPageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";
import {
  hotelApi,
  type HotelFolio,
  type HotelReservation,
  type HotelRoom,
  type HotelRoomType,
} from "@/services/api/hotel";
import { appDialog } from "@/components/feedback/AppDialog";
import { formatCurrency } from "@/utils/cn";

function tomorrowISO(offset = 1) {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return d.toISOString().slice(0, 10);
}

export function HotelReservationFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [roomTypes, setRoomTypes] = useState<HotelRoomType[]>([]);
  const [rooms, setRooms] = useState<HotelRoom[]>([]);
  const [form, setForm] = useState({
    guest_name: "",
    phone: "",
    room_type_id: "",
    room_id: "",
    check_in_date: tomorrowISO(1),
    check_out_date: tomorrowISO(2),
    adults: "1",
    children: "0",
    rate_amount: "",
    notes: "",
  });

  useEffect(() => {
    if (!branchId) return;
    Promise.all([hotelApi.roomTypes(1, branchId), hotelApi.rooms(1, branchId)]).then(
      ([types, roomRes]) => {
        setRoomTypes(types.data.results);
        setRooms(roomRes.data.results);
      }
    );
  }, [branchId]);

  useEffect(() => {
    if (!editId) return;
    hotelApi
      .reservation(editId)
      .then((res) => {
        const r = res.data;
        setForm({
          guest_name: r.guest_name || "",
          phone: r.guest_phone || "",
          room_type_id: r.room_type_id || "",
          room_id: r.room_id || "",
          check_in_date: r.check_in_date || tomorrowISO(1),
          check_out_date: r.check_out_date || tomorrowISO(2),
          adults: String(r.adults || 1),
          children: String(r.children || 0),
          rate_amount: String(r.rate_amount || ""),
          notes: r.notes || "",
        });
      })
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Not found"))
      .finally(() => setLoading(false));
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!branchId) return;
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        branch_id: branchId,
        guest_name: form.guest_name.trim(),
        phone: form.phone || undefined,
        room_type_id: form.room_type_id,
        room_id: form.room_id || undefined,
        check_in_date: form.check_in_date,
        check_out_date: form.check_out_date,
        adults: Number(form.adults) || 1,
        children: Number(form.children) || 0,
        rate_amount: form.rate_amount ? Number(form.rate_amount) : undefined,
        notes: form.notes || undefined,
      };
      if (editId) await hotelApi.updateReservation(editId, payload);
      else await hotelApi.createReservation(payload);
      navigate(editId ? `/hotel/reservations/${editId}` : "/hotel/reservations");
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Hotel", "Reservations"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit reservation" : "New reservation"}
      breadcrumbs={["Home", "Hotel", "Reservations", editId ? "Edit" : "New"]}
    >
      <form onSubmit={handleSubmit}>
        <FormPageLayout
          main={
            <FormSection title="Stay">
              <FormGrid>
                <FormField label="Guest name" required>
                  <Input
                    required
                    value={form.guest_name}
                    onChange={(e) => setForm({ ...form, guest_name: e.target.value })}
                  />
                </FormField>
                <FormField label="Phone">
                  <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </FormField>
                <FormField label="Room type" required>
                  <Select value={form.room_type_id} onValueChange={(v) => setForm({ ...form, room_type_id: v })}>
                    <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                    <SelectContent>
                      {roomTypes.map((t) => (
                        <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Room">
                  <Select
                    value={form.room_id || "none"}
                    onValueChange={(v) => setForm({ ...form, room_id: v === "none" ? "" : v })}
                  >
                    <SelectTrigger><SelectValue placeholder="Unassigned" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Unassigned</SelectItem>
                      {rooms.map((r) => (
                        <SelectItem key={r.id} value={r.id}>{r.code}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Check-in" required>
                  <Input
                    type="date"
                    required
                    value={form.check_in_date}
                    onChange={(e) => setForm({ ...form, check_in_date: e.target.value })}
                  />
                </FormField>
                <FormField label="Check-out" required>
                  <Input
                    type="date"
                    required
                    value={form.check_out_date}
                    onChange={(e) => setForm({ ...form, check_out_date: e.target.value })}
                  />
                </FormField>
                <FormField label="Adults">
                  <Input type="number" min="1" value={form.adults} onChange={(e) => setForm({ ...form, adults: e.target.value })} />
                </FormField>
                <FormField label="Children">
                  <Input type="number" min="0" value={form.children} onChange={(e) => setForm({ ...form, children: e.target.value })} />
                </FormField>
                <FormField label="Nightly rate">
                  <Input type="number" min="0" step="0.01" value={form.rate_amount} onChange={(e) => setForm({ ...form, rate_amount: e.target.value })} />
                </FormField>
                <FormField label="Notes" className="md:col-span-2 xl:col-span-3">
                  <Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </FormField>
              </FormGrid>
            </FormSection>
          }
          actions={
            <FormActions>
              <div className="flex gap-3">
                <Button type="submit" loading={saving}>{editId ? "Save" : "Book stay"}</Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/hotel/reservations")}>
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

export function HotelReservationEditPage() {
  const { id } = useParams();
  return <HotelReservationFormPage editId={id} />;
}

export function HotelReservationDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasAnyPermission } = usePermissions();
  const canFrontDesk = hasAnyPermission("hotel.manage", "hotel.front_desk", "hotel.reservations.update");
  const [row, setRow] = useState<HotelReservation | null>(null);
  const [folio, setFolio] = useState<HotelFolio | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await hotelApi.reservation(id);
      setRow(res.data);
      try {
        const f = await hotelApi.folio(id);
        setFolio(f.data);
      } catch {
        setFolio(res.data.folio || null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload on id change only
  }, [id]);

  if (loading || !row) {
    return (
      <PageLayout title={loading ? "Loading..." : "Reservation"} breadcrumbs={["Home", "Hotel", "Reservations"]}>
        {loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={row.reservation_number}
      description={`${row.guest_name} · ${row.check_in_date} → ${row.check_out_date}`}
      breadcrumbs={["Home", "Hotel", "Reservations", row.reservation_number]}
      actions={
        <div className="flex gap-2">
          {row.status === "booked" && canFrontDesk ? (
            <Button variant="secondary" onClick={() => navigate(`/hotel/reservations/${row.id}/edit`)}>
              Edit
            </Button>
          ) : null}
          <Button variant="secondary" onClick={() => navigate("/hotel/reservations")}>
            Back
          </Button>
        </div>
      }
    >
      <ContentSection title="Stay">
        <div className="grid gap-3 sm:grid-cols-2 text-sm">
          <p><span className="text-muted-foreground">Guest</span> · {row.guest_name}</p>
          <p><span className="text-muted-foreground">Phone</span> · {row.guest_phone || "—"}</p>
          <p><span className="text-muted-foreground">Room</span> · {row.room_code || row.room_type_name}</p>
          <p>
            <span className="text-muted-foreground">Status</span> · <Badge variant="secondary">{row.status}</Badge>
          </p>
          <p><span className="text-muted-foreground">Rate</span> · {formatCurrency(row.rate_amount)}</p>
          <p><span className="text-muted-foreground">Guests</span> · {row.adults} adults / {row.children} children</p>
        </div>
      </ContentSection>
      <ContentSection title="Folio" description="Room charges and payments">
        {!folio ? (
          <p className="text-sm text-muted-foreground">No folio yet.</p>
        ) : (
          <div className="space-y-3 text-sm">
            <p>
              Balance {formatCurrency(folio.outstanding ?? folio.balance)} · {folio.status}
            </p>
            {(folio.lines || []).map((line) => (
              <div key={line.id} className="flex justify-between border-t border-border/40 pt-2">
                <span>{line.description}</span>
                <span>{formatCurrency(line.amount)}</span>
              </div>
            ))}
          </div>
        )}
      </ContentSection>
    </PageLayout>
  );
}
