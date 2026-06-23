import { useCallback, useEffect, useState } from "react";
import { Calendar, Clock, DollarSign, Plus, Trophy, Users } from "lucide-react";
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
  futsalApi,
  type FutsalBooking,
  type FutsalCourt,
  type FutsalLedgerEntry,
  type FutsalPlayer,
  type FutsalSummary,
  type FutsalTeam,
} from "@/services/api/futsal";
import { formatCurrency } from "@/utils/cn";

type Tab = "bookings" | "teams" | "finance";

export function FutsalPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("futsal.manage");
  const canFinance = hasPermission("futsal.finance");

  const [tab, setTab] = useState<Tab>("bookings");
  const [summary, setSummary] = useState<FutsalSummary | null>(null);
  const [courts, setCourts] = useState<FutsalCourt[]>([]);
  const [teams, setTeams] = useState<FutsalTeam[]>([]);
  const [players, setPlayers] = useState<FutsalPlayer[]>([]);
  const [bookings, setBookings] = useState<FutsalBooking[]>([]);
  const [ledger, setLedger] = useState<FutsalLedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const [courtForm, setCourtForm] = useState({ name: "", code: "", hourly_rate: "" });
  const [teamForm, setTeamForm] = useState({ name: "", captain_name: "", contact_phone: "" });
  const [playerForm, setPlayerForm] = useState({ full_name: "", phone: "", team_id: "" });
  const [bookingForm, setBookingForm] = useState({
    court_id: "",
    title: "",
    start_at: "",
    end_at: "",
    amount_paid: "",
  });
  const [ledgerForm, setLedgerForm] = useState({
    entry_type: "expense",
    category: "other",
    amount: "",
    description: "",
  });

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const [sumRes, courtsRes, teamsRes, playersRes, bookingsRes] = await Promise.all([
        futsalApi.summary(branchId),
        futsalApi.courts(1, branchId),
        futsalApi.teams(1, branchId),
        futsalApi.players(1, branchId),
        futsalApi.bookings(1, branchId),
      ]);
      setSummary(sumRes.data);
      setCourts(courtsRes.data.results);
      setTeams(teamsRes.data.results);
      setPlayers(playersRes.data.results);
      setBookings(bookingsRes.data.results);
      if (canFinance) {
        const ledgerRes = await futsalApi.ledger(1, branchId);
        setLedger(ledgerRes.data.results);
      }
    } finally {
      setLoading(false);
    }
  }, [branchId, canFinance]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const addCourt = async () => {
    if (!branchId || !courtForm.name || !courtForm.code) return;
    await futsalApi.createCourt({
      name: courtForm.name,
      code: courtForm.code,
      branch_id: branchId,
      hourly_rate: Number(courtForm.hourly_rate) || 0,
    });
    setCourtForm({ name: "", code: "", hourly_rate: "" });
    void reload();
  };

  const addTeam = async () => {
    if (!branchId || !teamForm.name) return;
    await futsalApi.createTeam({ ...teamForm, branch_id: branchId });
    setTeamForm({ name: "", captain_name: "", contact_phone: "" });
    void reload();
  };

  const addPlayer = async () => {
    if (!branchId || !playerForm.full_name) return;
    await futsalApi.createPlayer({
      full_name: playerForm.full_name,
      phone: playerForm.phone,
      branch_id: branchId,
      team_id: playerForm.team_id || undefined,
    });
    setPlayerForm({ full_name: "", phone: "", team_id: "" });
    void reload();
  };

  const addBooking = async () => {
    if (!branchId || !bookingForm.court_id || !bookingForm.start_at || !bookingForm.end_at) return;
    await futsalApi.createBooking({
      branch_id: branchId,
      court_id: bookingForm.court_id,
      title: bookingForm.title,
      start_at: new Date(bookingForm.start_at).toISOString(),
      end_at: new Date(bookingForm.end_at).toISOString(),
      amount_paid: Number(bookingForm.amount_paid) || 0,
    });
    setBookingForm({ court_id: "", title: "", start_at: "", end_at: "", amount_paid: "" });
    void reload();
  };

  const addLedger = async () => {
    if (!branchId || !ledgerForm.amount) return;
    await futsalApi.createLedger({
      branch_id: branchId,
      entry_type: ledgerForm.entry_type,
      category: ledgerForm.category,
      amount: Number(ledgerForm.amount),
      description: ledgerForm.description,
    });
    setLedgerForm({ entry_type: "expense", category: "other", amount: "", description: "" });
    void reload();
  };

  const bookingColumns: Column<FutsalBooking>[] = [
    {
      key: "when",
      header: "Date / Time",
      cell: (r) => (
        <div>
          <p className="font-medium">{new Date(r.start_at).toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">{r.hours}h · {r.court_name}</p>
        </div>
      ),
    },
    { key: "title", header: "Title", cell: (r) => r.title || r.team_name || "—" },
    { key: "amount", header: "Amount", cell: (r) => formatCurrency(r.amount) },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant="secondary" className="capitalize">{r.status}</Badge>,
    },
  ];

  const ledgerColumns: Column<FutsalLedgerEntry>[] = [
    { key: "date", header: "Date", cell: (r) => r.entry_date },
    {
      key: "type",
      header: "Type",
      cell: (r) => (
        <Badge variant={r.entry_type === "income" ? "success" : "secondary"} className="capitalize">
          {r.entry_type}
        </Badge>
      ),
    },
    { key: "category", header: "Category", cell: (r) => r.category },
    {
      key: "amount",
      header: "Amount",
      cell: (r) => (
        <span className={r.entry_type === "income" ? "text-emerald-600" : "text-destructive"}>
          {formatCurrency(r.amount)}
        </span>
      ),
    },
    { key: "desc", header: "Description", cell: (r) => r.description || "—" },
  ];

  return (
    <PageLayout
      title="Futsal"
      description="Courts, bookings, teams, players, and futsal income & expenses — same system as your cafeteria."
    >
      <KpiGrid>
        <KpiCard title="Bookings today" value={String(summary?.bookings_today ?? 0)} icon={<Calendar className="h-5 w-5" />} loading={loading} />
        <KpiCard title="Hours today" value={String(summary?.hours_today ?? 0)} icon={<Clock className="h-5 w-5" />} loading={loading} />
        <KpiCard title="Income (month)" value={formatCurrency(summary?.income_month ?? 0)} icon={<DollarSign className="h-5 w-5" />} loading={loading} />
        <KpiCard title="Profit (month)" value={formatCurrency(summary?.profit_month ?? 0)} icon={<Trophy className="h-5 w-5" />} loading={loading} />
      </KpiGrid>

      <div className="mt-6 flex flex-wrap gap-2">
        {(["bookings", "teams", "finance"] as Tab[]).map((t) => {
          if (t === "finance" && !canFinance) return null;
          return (
            <Button key={t} variant={tab === t ? "default" : "secondary"} size="sm" onClick={() => setTab(t)}>
              {t === "bookings" ? "Bookings & Courts" : t === "teams" ? "Teams & Players" : "Income & Expenses"}
            </Button>
          );
        })}
      </div>

      {tab === "bookings" && (
        <div className="mt-6 space-y-6">
          {canManage && (
            <ContentSection title="Courts" description="Register futsal courts and hourly rates.">
              <FormGrid className="mb-4">
                <FormField label="Court name">
                  <Input value={courtForm.name} onChange={(e) => setCourtForm({ ...courtForm, name: e.target.value })} />
                </FormField>
                <FormField label="Code">
                  <Input value={courtForm.code} onChange={(e) => setCourtForm({ ...courtForm, code: e.target.value })} />
                </FormField>
                <FormField label="Hourly rate">
                  <Input type="number" value={courtForm.hourly_rate} onChange={(e) => setCourtForm({ ...courtForm, hourly_rate: e.target.value })} />
                </FormField>
                <div className="flex items-end">
                  <Button onClick={addCourt}><Plus className="h-4 w-4" /> Add court</Button>
                </div>
              </FormGrid>
              <div className="flex flex-wrap gap-2">
                {courts.map((c) => (
                  <Badge key={c.id} variant="outline">{c.name} — {formatCurrency(c.hourly_rate)}/hr</Badge>
                ))}
              </div>
            </ContentSection>
          )}

          {canManage && (
            <ContentSection title="New booking" description="Schedule court hours. Payment creates income automatically.">
              <FormGrid>
                <FormField label="Court">
                  <Select value={bookingForm.court_id} onValueChange={(v) => setBookingForm({ ...bookingForm, court_id: v })}>
                    <SelectTrigger><SelectValue placeholder="Select court" /></SelectTrigger>
                    <SelectContent>
                      {courts.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Title / team name">
                  <Input value={bookingForm.title} onChange={(e) => setBookingForm({ ...bookingForm, title: e.target.value })} />
                </FormField>
                <FormField label="Start">
                  <Input type="datetime-local" value={bookingForm.start_at} onChange={(e) => setBookingForm({ ...bookingForm, start_at: e.target.value })} />
                </FormField>
                <FormField label="End">
                  <Input type="datetime-local" value={bookingForm.end_at} onChange={(e) => setBookingForm({ ...bookingForm, end_at: e.target.value })} />
                </FormField>
                <FormField label="Paid now">
                  <Input type="number" value={bookingForm.amount_paid} onChange={(e) => setBookingForm({ ...bookingForm, amount_paid: e.target.value })} />
                </FormField>
                <div className="flex items-end">
                  <Button onClick={addBooking}><Plus className="h-4 w-4" /> Book</Button>
                </div>
              </FormGrid>
            </ContentSection>
          )}

          <ContentSection title="Bookings">
            <DataTable columns={bookingColumns} data={bookings} loading={loading} emptyMessage="No bookings yet." />
          </ContentSection>
        </div>
      )}

      {tab === "teams" && (
        <div className="mt-6 space-y-6">
          {canManage && (
            <>
              <ContentSection title="Teams">
                <FormGrid className="mb-4">
                  <FormField label="Team name">
                    <Input value={teamForm.name} onChange={(e) => setTeamForm({ ...teamForm, name: e.target.value })} />
                  </FormField>
                  <FormField label="Captain">
                    <Input value={teamForm.captain_name} onChange={(e) => setTeamForm({ ...teamForm, captain_name: e.target.value })} />
                  </FormField>
                  <FormField label="Phone">
                    <Input value={teamForm.contact_phone} onChange={(e) => setTeamForm({ ...teamForm, contact_phone: e.target.value })} />
                  </FormField>
                  <div className="flex items-end">
                    <Button onClick={addTeam}><Plus className="h-4 w-4" /> Add team</Button>
                  </div>
                </FormGrid>
                <div className="space-y-2">
                  {teams.map((t) => (
                    <div key={t.id} className="flex items-center gap-2 text-sm">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{t.name}</span>
                      <span className="text-muted-foreground">({t.player_count} players)</span>
                    </div>
                  ))}
                </div>
              </ContentSection>

              <ContentSection title="Players">
                <FormGrid className="mb-4">
                  <FormField label="Full name">
                    <Input value={playerForm.full_name} onChange={(e) => setPlayerForm({ ...playerForm, full_name: e.target.value })} />
                  </FormField>
                  <FormField label="Phone">
                    <Input value={playerForm.phone} onChange={(e) => setPlayerForm({ ...playerForm, phone: e.target.value })} />
                  </FormField>
                  <FormField label="Team">
                    <Select value={playerForm.team_id || "none"} onValueChange={(v) => setPlayerForm({ ...playerForm, team_id: v === "none" ? "" : v })}>
                      <SelectTrigger><SelectValue placeholder="Optional" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No team</SelectItem>
                        {teams.map((t) => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <div className="flex items-end">
                    <Button onClick={addPlayer}><Plus className="h-4 w-4" /> Add player</Button>
                  </div>
                </FormGrid>
                <div className="space-y-1">
                  {players.map((p) => (
                    <p key={p.id} className="text-sm">
                      {p.full_name}
                      {p.team_name ? <span className="text-muted-foreground"> · {p.team_name}</span> : null}
                    </p>
                  ))}
                </div>
              </ContentSection>
            </>
          )}
        </div>
      )}

      {tab === "finance" && canFinance && (
        <div className="mt-6 space-y-6">
          <ContentSection title="Record income or expense">
            <FormGrid>
              <FormField label="Type">
                <Select value={ledgerForm.entry_type} onValueChange={(v) => setLedgerForm({ ...ledgerForm, entry_type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="income">Income</SelectItem>
                    <SelectItem value="expense">Expense</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Category">
                <Input value={ledgerForm.category} onChange={(e) => setLedgerForm({ ...ledgerForm, category: e.target.value })} />
              </FormField>
              <FormField label="Amount">
                <Input type="number" value={ledgerForm.amount} onChange={(e) => setLedgerForm({ ...ledgerForm, amount: e.target.value })} />
              </FormField>
              <FormField label="Description">
                <Input value={ledgerForm.description} onChange={(e) => setLedgerForm({ ...ledgerForm, description: e.target.value })} />
              </FormField>
              <div className="flex items-end">
                <Button onClick={addLedger}><Plus className="h-4 w-4" /> Save</Button>
              </div>
            </FormGrid>
          </ContentSection>
          <ContentSection title="Futsal ledger">
            <DataTable columns={ledgerColumns} data={ledger} loading={loading} emptyMessage="No entries yet." />
          </ContentSection>
        </div>
      )}
    </PageLayout>
  );
}
