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
import { usePermissions } from "@/hooks/usePermissions";
import { gymApi, type GymMember } from "@/services/api/gym";
import { customersApi } from "@/services/api/partners";
import { settingsApi } from "@/services/api/admin";
import { appDialog } from "@/components/feedback/AppDialog";

const emptyForm = {
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

export function GymMemberFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [branches, setBranches] = useState<{ id: string; name: string }[]>([]);
  const [customers, setCustomers] = useState<{ id: string; name: string }[]>([]);
  const [form, setForm] = useState(emptyForm);

  useEffect(() => {
    settingsApi.branches().then((res) => setBranches(res.data)).catch(() => undefined);
    customersApi
      .list({ page_size: 100 })
      .then((res) =>
        setCustomers(
          (res.data.results || []).map((c) => ({ id: c.id, name: c.full_name }))
        )
      )
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!editId) return;
    gymApi
      .getMember(editId)
      .then((res) => {
        const m = res.data;
        setForm({
          membership_number: m.membership_number || "",
          full_name: m.full_name || "",
          email: m.email || "",
          phone: m.phone || "",
          date_of_birth: m.date_of_birth || "",
          gender: m.gender || "",
          address: m.address || "",
          emergency_contact_name: m.emergency_contact_name || "",
          emergency_contact_phone: m.emergency_contact_phone || "",
          status: m.status || "active",
          joined_at: m.joined_at || "",
          notes: m.notes || "",
          customer_id: m.customer_id || "",
          branch_id: m.branch_id || "",
        });
      })
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Member not found."))
      .finally(() => setLoading(false));
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
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
      if (editId) await gymApi.updateMember(editId, payload);
      else await gymApi.createMember(payload);
      navigate("/gym/members");
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Gym", "Members"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit member" : "New member"}
      description="Gym membership profile."
      breadcrumbs={["Home", "Gym", "Members", editId ? "Edit" : "New"]}
    >
      <form onSubmit={handleSubmit}>
        <FormPageLayout
          main={
            <FormSection title="Member">
              <FormGrid>
                <FormField label="Full name" required>
                  <Input
                    required
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  />
                </FormField>
                <FormField label="Membership #">
                  <Input
                    value={form.membership_number}
                    onChange={(e) => setForm({ ...form, membership_number: e.target.value })}
                    placeholder="Auto"
                  />
                </FormField>
                <FormField label="Phone">
                  <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </FormField>
                <FormField label="Email">
                  <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </FormField>
                <FormField label="Date of birth">
                  <Input
                    type="date"
                    value={form.date_of_birth}
                    onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
                  />
                </FormField>
                <FormField label="Joined">
                  <Input
                    type="date"
                    value={form.joined_at}
                    onChange={(e) => setForm({ ...form, joined_at: e.target.value })}
                  />
                </FormField>
                <FormField label="Gender">
                  <Select value={form.gender || "none"} onValueChange={(v) => setForm({ ...form, gender: v === "none" ? "" : v })}>
                    <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">—</SelectItem>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Status">
                  <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                      <SelectItem value="suspended">Suspended</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Address" className="md:col-span-2 xl:col-span-3">
                  <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
                </FormField>
                <FormField label="Emergency contact">
                  <Input
                    value={form.emergency_contact_name}
                    onChange={(e) => setForm({ ...form, emergency_contact_name: e.target.value })}
                  />
                </FormField>
                <FormField label="Emergency phone">
                  <Input
                    value={form.emergency_contact_phone}
                    onChange={(e) => setForm({ ...form, emergency_contact_phone: e.target.value })}
                  />
                </FormField>
                <FormField label="Branch">
                  <Select
                    value={form.branch_id || "none"}
                    onValueChange={(v) => setForm({ ...form, branch_id: v === "none" ? "" : v })}
                  >
                    <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">—</SelectItem>
                      {branches.map((b) => (
                        <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Linked customer">
                  <Select
                    value={form.customer_id || "none"}
                    onValueChange={(v) => setForm({ ...form, customer_id: v === "none" ? "" : v })}
                  >
                    <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">—</SelectItem>
                      {customers.map((c) => (
                        <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
                <Button type="submit" loading={saving}>
                  {editId ? "Save changes" : "Create member"}
                </Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/gym/members")}>
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

export function GymMemberEditPage() {
  const { id } = useParams();
  return <GymMemberFormPage editId={id} />;
}

export function GymMemberDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasAnyPermission } = usePermissions();
  const canUpdate = hasAnyPermission("gym.manage", "gym.members.update");
  const [member, setMember] = useState<GymMember | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    gymApi
      .getMember(id)
      .then((res) => setMember(res.data))
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Member not found."))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !member) {
    return (
      <PageLayout title={loading ? "Loading..." : "Member"} breadcrumbs={["Home", "Gym", "Members"]}>
        {loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={member.full_name}
      description={`${member.membership_number} · ${member.branch_name || "No branch"}`}
      breadcrumbs={["Home", "Gym", "Members", member.membership_number]}
      actions={
        <div className="flex gap-2">
          {canUpdate ? (
            <Button variant="secondary" onClick={() => navigate(`/gym/members/${member.id}/edit`)}>
              Edit
            </Button>
          ) : null}
          <Button variant="secondary" onClick={() => navigate("/gym/members")}>
            Back
          </Button>
        </div>
      }
    >
      <ContentSection title="Profile">
        <div className="grid gap-3 sm:grid-cols-2 text-sm">
          <p>
            <span className="text-muted-foreground">Status</span> ·{" "}
            <Badge variant={member.status === "active" ? "success" : "secondary"}>{member.status}</Badge>
          </p>
          <p>
            <span className="text-muted-foreground">Phone</span> · {member.phone || "—"}
          </p>
          <p>
            <span className="text-muted-foreground">Email</span> · {member.email || "—"}
          </p>
          <p>
            <span className="text-muted-foreground">Joined</span> · {member.joined_at || "—"}
          </p>
          <p>
            <span className="text-muted-foreground">Customer</span> · {member.customer_name || "—"}
          </p>
          <p>
            <span className="text-muted-foreground">Emergency</span> ·{" "}
            {member.emergency_contact_name || "—"}
            {member.emergency_contact_phone ? ` (${member.emergency_contact_phone})` : ""}
          </p>
        </div>
      </ContentSection>
    </PageLayout>
  );
}
