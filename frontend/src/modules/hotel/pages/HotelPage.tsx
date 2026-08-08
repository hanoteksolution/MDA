import { useCallback, useEffect, useMemo, useState } from "react";
import { BedDouble, CalendarCheck, DoorOpen, Plus, Sparkles } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { DataTable, type Column } from "@/components/data/DataTable";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { usePermissions } from "@/hooks/usePermissions";
import { useAuthStore } from "@/store/authStore";
import {
  hotelApi,
  type HotelReservation,
  type HotelRoom,
  type HotelRoomType,
  type HotelSummary,
} from "@/services/api/hotel";
import { formatCurrency } from "@/utils/cn";

type Tab = "reservations" | "rooms" | "types";

function tomorrowISO() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

function dayAfterTomorrowISO() {
  const d = new Date();
  d.setDate(d.getDate() + 3);
  return d.toISOString().slice(0, 10);
}

export function HotelPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("hotel.manage");
  const canFrontDesk = hasPermission("hotel.front_desk") || canManage;
  const canHousekeeping = hasPermission("hotel.housekeeping") || canManage;

  const [tab, setTab] = useState<Tab>("reservations");
  const [summary, setSummary] = useState<HotelSummary | null>(null);
  const [roomTypes, setRoomTypes] = useState<HotelRoomType[]>([]);
  const [rooms, setRooms] = useState<HotelRoom[]>([]);
  const [reservations, setReservations] = useState<HotelReservation[]>([]);
  const [loading, setLoading] = useState(true);

  const [typeForm, setTypeForm] = useState({ name: "", code: "", base_rate: "", capacity: "2" });
  const [roomForm, setRoomForm] = useState({ code: "", room_type_id: "", floor: "" });
  const [resForm, setResForm] = useState({
    guest_name: "",
    phone: "",
    room_type_id: "",
    room_id: "",
    check_in_date: tomorrowISO(),
    check_out_date: dayAfterTomorrowISO(),
    adults: "1",
  });

  const [checkoutTarget, setCheckoutTarget] = useState<HotelReservation | null>(null);
  const [checkoutMethod, setCheckoutMethod] = useState("cash");
  const [checkoutRef, setCheckoutRef] = useState("");
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const [sumRes, typeRes, roomRes, resRes] = await Promise.all([
        hotelApi.summary(branchId),
        hotelApi.roomTypes(1, branchId),
        hotelApi.rooms(1, branchId),
        hotelApi.reservations(1, branchId),
      ]);
      setSummary(sumRes.data);
      setRoomTypes(typeRes.data.results);
      setRooms(roomRes.data.results);
      setReservations(resRes.data.results);
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const vacantRooms = useMemo(
    () => rooms.filter((r) => r.status === "vacant" || r.status === "reserved"),
    [rooms]
  );

  const addType = async () => {
    if (!branchId || !typeForm.name) return;
    await hotelApi.createRoomType({
      name: typeForm.name,
      code: typeForm.code,
      base_rate: Number(typeForm.base_rate) || 0,
      capacity: Number(typeForm.capacity) || 2,
      branch_id: branchId,
    });
    setTypeForm({ name: "", code: "", base_rate: "", capacity: "2" });
    void reload();
  };

  const addRoom = async () => {
    if (!branchId || !roomForm.code || !roomForm.room_type_id) return;
    await hotelApi.createRoom({
      code: roomForm.code,
      room_type_id: roomForm.room_type_id,
      floor: roomForm.floor,
      branch_id: branchId,
    });
    setRoomForm({ code: "", room_type_id: "", floor: "" });
    void reload();
  };

  const addReservation = async () => {
    if (!branchId || !resForm.guest_name || !resForm.room_type_id) return;
    await hotelApi.createReservation({
      branch_id: branchId,
      guest_name: resForm.guest_name,
      phone: resForm.phone,
      room_type_id: resForm.room_type_id,
      room_id: resForm.room_id || undefined,
      check_in_date: resForm.check_in_date,
      check_out_date: resForm.check_out_date,
      adults: Number(resForm.adults) || 1,
    });
    setResForm({
      guest_name: "",
      phone: "",
      room_type_id: "",
      room_id: "",
      check_in_date: tomorrowISO(),
      check_out_date: dayAfterTomorrowISO(),
      adults: "1",
    });
    void reload();
  };

  const openCheckout = (r: HotelReservation) => {
    setCheckoutTarget(r);
    setCheckoutMethod("cash");
    setCheckoutRef("");
    setCheckoutError(null);
  };

  const confirmCheckout = async () => {
    if (!checkoutTarget) return;
    const outstanding =
      checkoutTarget.folio?.outstanding ??
      Math.max(
        0,
        (checkoutTarget.folio?.balance || 0) - (checkoutTarget.folio?.amount_paid || 0)
      );
    setCheckoutBusy(true);
    setCheckoutError(null);
    try {
      await hotelApi.checkOut(
        checkoutTarget.id,
        outstanding > 0
          ? { payment_method: checkoutMethod, payment_reference: checkoutRef || undefined }
          : {}
      );
      setCheckoutTarget(null);
      void reload();
    } catch (err) {
      setCheckoutError(err instanceof Error ? err.message : "Check-out failed");
    } finally {
      setCheckoutBusy(false);
    }
  };

  const reservationColumns: Column<HotelReservation>[] = [
    {
      key: "number",
      header: "Reservation",
      cell: (r) => <span className="font-medium">{r.reservation_number}</span>,
    },
    { key: "guest", header: "Guest", cell: (r) => r.guest_name },
    {
      key: "room",
      header: "Room",
      cell: (r) => r.room_code || r.room_type_name || "—",
    },
    {
      key: "dates",
      header: "Stay",
      cell: (r) => `${r.check_in_date || "?"} → ${r.check_out_date || "?"}`,
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant="secondary">{r.status}</Badge>,
    },
    {
      key: "folio",
      header: "Folio",
      cell: (r) =>
        r.folio
          ? formatCurrency(r.folio.outstanding ?? r.folio.balance)
          : "—",
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        canFrontDesk ? (
          <div className="flex justify-end gap-1">
            {r.status === "booked" ? (
              <Button size="sm" onClick={() => hotelApi.checkIn(r.id).then(reload)}>
                Check in
              </Button>
            ) : null}
            {r.status === "checked_in" ? (
              <Button size="sm" variant="outline" onClick={() => openCheckout(r)}>
                Check out
              </Button>
            ) : null}
            {r.status === "booked" ? (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => hotelApi.cancel(r.id).then(reload)}
              >
                Cancel
              </Button>
            ) : null}
          </div>
        ) : null,
    },
  ];

  const roomColumns: Column<HotelRoom>[] = [
    { key: "code", header: "Room", cell: (r) => r.code },
    { key: "type", header: "Type", cell: (r) => r.room_type_name },
    { key: "floor", header: "Floor", cell: (r) => r.floor || "—" },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant="secondary">{r.status}</Badge>,
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        canHousekeeping && r.status === "dirty" ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => hotelApi.setRoomStatus(r.id, "vacant").then(reload)}
          >
            Mark clean
          </Button>
        ) : null,
    },
  ];

  const typeColumns: Column<HotelRoomType>[] = [
    { key: "name", header: "Type", cell: (r) => r.name },
    { key: "code", header: "Code", cell: (r) => r.code || "—" },
    { key: "rate", header: "Base rate", cell: (r) => formatCurrency(r.base_rate) },
    { key: "capacity", header: "Capacity", cell: (r) => r.capacity },
  ];

  return (
    <PageLayout
      title="Hotel"
      description="Rooms, reservations, check-in/out, and guest folios."
      breadcrumbs={["Home", "Hotel"]}
    >
      <KpiGrid columns={4}>
        <KpiCard
          index={0}
          accent="primary"
          title="In house"
          value={String(summary?.in_house ?? 0)}
          icon={<BedDouble className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={1}
          accent="success"
          title="Vacant rooms"
          value={`${summary?.rooms_vacant ?? 0}/${summary?.rooms ?? 0}`}
          icon={<DoorOpen className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={2}
          accent="info"
          title="Arrivals today"
          value={String(summary?.arrivals_today ?? 0)}
          icon={<CalendarCheck className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={3}
          accent="warning"
          title="Dirty rooms"
          value={String(summary?.rooms_dirty ?? 0)}
          icon={<Sparkles className="h-5 w-5" />}
          loading={loading}
        />
      </KpiGrid>

      <div className="mb-4 flex gap-2">
        {(["reservations", "rooms", "types"] as Tab[]).map((t) => (
          <Button
            key={t}
            size="sm"
            variant={tab === t ? "default" : "outline"}
            onClick={() => setTab(t)}
          >
            {t[0].toUpperCase() + t.slice(1)}
          </Button>
        ))}
      </div>

      {tab === "reservations" ? (
        <ContentSection title="Reservations" description="Book, check in, and settle folios">
          {canFrontDesk ? (
            <FormGrid className="mb-4">
              <FormField label="Guest name">
                <Input
                  value={resForm.guest_name}
                  onChange={(e) => setResForm((f) => ({ ...f, guest_name: e.target.value }))}
                />
              </FormField>
              <FormField label="Phone">
                <Input
                  value={resForm.phone}
                  onChange={(e) => setResForm((f) => ({ ...f, phone: e.target.value }))}
                />
              </FormField>
              <FormField label="Room type">
                <Select
                  value={resForm.room_type_id}
                  onValueChange={(v) => setResForm((f) => ({ ...f, room_type_id: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {roomTypes.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name} ({formatCurrency(t.base_rate)})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Room (optional)">
                <Select
                  value={resForm.room_id || "__none"}
                  onValueChange={(v) =>
                    setResForm((f) => ({ ...f, room_id: v === "__none" ? "" : v }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Auto-assign at check-in" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none">Auto-assign later</SelectItem>
                    {vacantRooms.map((r) => (
                      <SelectItem key={r.id} value={r.id}>
                        {r.code} · {r.room_type_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Check-in">
                <Input
                  type="date"
                  value={resForm.check_in_date}
                  onChange={(e) => setResForm((f) => ({ ...f, check_in_date: e.target.value }))}
                />
              </FormField>
              <FormField label="Check-out">
                <Input
                  type="date"
                  value={resForm.check_out_date}
                  onChange={(e) => setResForm((f) => ({ ...f, check_out_date: e.target.value }))}
                />
              </FormField>
              <div className="flex items-end">
                <Button onClick={addReservation}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Book
                </Button>
              </div>
            </FormGrid>
          ) : null}
          <DataTable
            columns={reservationColumns}
            data={reservations}
            loading={loading}
            emptyMessage="No reservations yet."
          />
        </ContentSection>
      ) : null}

      {tab === "rooms" ? (
        <ContentSection title="Rooms" description="Inventory and housekeeping status">
          {canManage ? (
            <FormGrid className="mb-4">
              <FormField label="Code">
                <Input
                  value={roomForm.code}
                  onChange={(e) => setRoomForm((f) => ({ ...f, code: e.target.value }))}
                />
              </FormField>
              <FormField label="Type">
                <Select
                  value={roomForm.room_type_id}
                  onValueChange={(v) => setRoomForm((f) => ({ ...f, room_type_id: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {roomTypes.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Floor">
                <Input
                  value={roomForm.floor}
                  onChange={(e) => setRoomForm((f) => ({ ...f, floor: e.target.value }))}
                />
              </FormField>
              <div className="flex items-end">
                <Button onClick={addRoom}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Add room
                </Button>
              </div>
            </FormGrid>
          ) : null}
          <DataTable columns={roomColumns} data={rooms} loading={loading} emptyMessage="No rooms." />
        </ContentSection>
      ) : null}

      {tab === "types" ? (
        <ContentSection title="Room types" description="Categories and nightly rates">
          {canManage ? (
            <FormGrid className="mb-4">
              <FormField label="Name">
                <Input
                  value={typeForm.name}
                  onChange={(e) => setTypeForm((f) => ({ ...f, name: e.target.value }))}
                />
              </FormField>
              <FormField label="Code">
                <Input
                  value={typeForm.code}
                  onChange={(e) => setTypeForm((f) => ({ ...f, code: e.target.value }))}
                />
              </FormField>
              <FormField label="Base rate">
                <Input
                  value={typeForm.base_rate}
                  onChange={(e) => setTypeForm((f) => ({ ...f, base_rate: e.target.value }))}
                />
              </FormField>
              <FormField label="Capacity">
                <Input
                  value={typeForm.capacity}
                  onChange={(e) => setTypeForm((f) => ({ ...f, capacity: e.target.value }))}
                />
              </FormField>
              <div className="flex items-end">
                <Button onClick={addType}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Add type
                </Button>
              </div>
            </FormGrid>
          ) : null}
          <DataTable
            columns={typeColumns}
            data={roomTypes}
            loading={loading}
            emptyMessage="No room types."
          />
        </ContentSection>
      ) : null}

      {checkoutTarget ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">Check out & settle</h3>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setCheckoutTarget(null)}
                disabled={checkoutBusy}
              >
                Close
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              {checkoutTarget.guest_name}
              {checkoutTarget.room_code ? ` · Room ${checkoutTarget.room_code}` : ""}
            </p>
            <p className="mt-2 text-lg font-semibold tabular-nums">
              {formatCurrency(
                checkoutTarget.folio?.outstanding ??
                  Math.max(
                    0,
                    (checkoutTarget.folio?.balance || 0) -
                      (checkoutTarget.folio?.amount_paid || 0)
                  )
              )}
              <span className="ml-2 text-xs font-normal text-muted-foreground">due</span>
            </p>
            {(checkoutTarget.folio?.outstanding ??
              Math.max(
                0,
                (checkoutTarget.folio?.balance || 0) - (checkoutTarget.folio?.amount_paid || 0)
              )) > 0 ? (
              <div className="mt-4 space-y-3">
                <FormField label="Payment method">
                  <Select value={checkoutMethod} onValueChange={setCheckoutMethod}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cash">Cash</SelectItem>
                      <SelectItem value="mobile">Mobile</SelectItem>
                      <SelectItem value="card">Card</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Reference (optional)">
                  <Input
                    value={checkoutRef}
                    onChange={(e) => setCheckoutRef(e.target.value)}
                    placeholder="Txn / receipt ref"
                  />
                </FormField>
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">No balance due — ready to check out.</p>
            )}
            {checkoutError ? (
              <p className="mt-3 text-sm text-destructive">{checkoutError}</p>
            ) : null}
            <div className="mt-4 flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setCheckoutTarget(null)}
                disabled={checkoutBusy}
              >
                Cancel
              </Button>
              <Button onClick={() => void confirmCheckout()} disabled={checkoutBusy}>
                {checkoutBusy ? "Settling…" : "Confirm check-out"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </PageLayout>
  );
}
