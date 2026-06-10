import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { FormPageLayout, FormActions } from "@/components/forms/FormPageLayout";
import { PermissionMatrix, type PermissionItem } from "@/components/auth/PermissionMatrix";
import { PermissionGuard } from "@/components/auth/PermissionGuard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { adminApi, settingsApi } from "@/services/api/admin";

export function UserFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [roles, setRoles] = useState<{ id: string; name: string }[]>([]);
  const [branches, setBranches] = useState<{ id: string; name: string }[]>([]);
  const [form, setForm] = useState({
    username: "", email: "", password: "", first_name: "", last_name: "",
    phone: "", role_id: "", branch_id: "", is_active: true,
  });

  useEffect(() => {
    Promise.all([adminApi.roles(), settingsApi.branches()]).then(([r, b]) => {
      setRoles(r.data);
      setBranches(b.data);
    });
  }, []);

  useEffect(() => {
    if (!editId) return;
    adminApi.getUser(editId).then((res) => {
      const u = res.data;
      setForm({
        username: u.username, email: u.email, password: "",
        first_name: u.first_name, last_name: u.last_name, phone: u.phone || "",
        role_id: u.role?.id || "", branch_id: u.branch?.id || "", is_active: u.is_active,
      });
      setLoading(false);
    });
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        username: form.username,
        email: form.email,
        first_name: form.first_name,
        last_name: form.last_name,
        phone: form.phone,
        role_id: form.role_id || null,
        branch_id: form.branch_id || null,
        is_active: form.is_active,
      };
      if (form.password) payload.password = form.password;
      if (editId) await adminApi.updateUser(editId, payload);
      else {
        if (!form.password) throw new Error("Password is required for new users.");
        await adminApi.createUser({ ...payload, password: form.password });
      }
      navigate("/admin");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Administration"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PermissionGuard permission={editId ? "users.update" : "users.create"}>
      <PageLayout
        title={editId ? "Edit User" : "Add User"}
        description="Create or update a system user account and assign role & branch."
        breadcrumbs={["Home", "Administration", editId ? "Edit User" : "New User"]}
      >
        <form onSubmit={handleSubmit}>
          <FormPageLayout
            main={
              <FormSection title="Account Details">
                <FormGrid>
                  <FormField label="Username" required>
                    <Input required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
                  </FormField>
                  <FormField label="Email" required>
                    <Input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                  </FormField>
                  <FormField label={editId ? "New Password" : "Password"} required={!editId} hint={editId ? "Leave blank to keep current password" : undefined}>
                    <Input type="password" minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                  </FormField>
                  <FormField label="First Name">
                    <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
                  </FormField>
                  <FormField label="Last Name">
                    <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
                  </FormField>
                  <FormField label="Phone">
                    <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                  </FormField>
                  <FormField label="Role" hint="Determines what the user can access">
                    <Select value={form.role_id || "none"} onValueChange={(v) => setForm({ ...form, role_id: v === "none" ? "" : v })}>
                      <SelectTrigger><SelectValue placeholder="Select role" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        {roles.map((r) => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Branch">
                    <Select value={form.branch_id || "none"} onValueChange={(v) => setForm({ ...form, branch_id: v === "none" ? "" : v })}>
                      <SelectTrigger><SelectValue placeholder="Select branch" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        {branches.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </FormField>
                </FormGrid>
                <label className="mt-6 flex items-center gap-3 cursor-pointer">
                  <Checkbox checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: !!v })} />
                  <span className="text-sm font-medium">Active account</span>
                </label>
              </FormSection>
            }
            aside={
              <div className="ds-card p-4 space-y-3">
                <p className="text-sm font-semibold">Access control</p>
                <p className="text-xs text-muted-foreground">
                  Users inherit all permissions from their assigned role. Edit the role to change module access.
                </p>
                {form.role_id && (
                  <Badge variant="secondary">
                    {roles.find((r) => r.id === form.role_id)?.name ?? "Role selected"}
                  </Badge>
                )}
              </div>
            }
            actions={
              <FormActions>
                <Button type="submit" loading={saving}>{editId ? "Save Changes" : "Create User"}</Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/admin")}>Cancel</Button>
              </FormActions>
            }
          />
        </form>
      </PageLayout>
    </PermissionGuard>
  );
}

export function RoleFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [isSystem, setIsSystem] = useState(false);
  const [allPermissions, setAllPermissions] = useState<Record<string, PermissionItem[]>>({});
  const [selectedPermIds, setSelectedPermIds] = useState<string[]>([]);
  const [form, setForm] = useState({ name: "", slug: "", description: "" });

  useEffect(() => {
    adminApi.permissions().then((res) => setAllPermissions(res.data));
  }, []);

  useEffect(() => {
    if (!editId) return;
    adminApi.getRole(editId).then((res) => {
      const r = res.data;
      setForm({ name: r.name, slug: r.slug, description: r.description || "" });
      setSelectedPermIds(r.permissions.map((p) => p.id));
      setIsSystem(r.is_system);
      setLoading(false);
    });
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        slug: form.slug,
        description: form.description,
        permission_ids: selectedPermIds,
      };
      if (editId) await adminApi.updateRole(editId, payload);
      else await adminApi.createRole(payload);
      navigate("/admin");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Administration"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PermissionGuard permission={editId ? "roles.update" : "roles.create"}>
      <PageLayout
        title={editId ? "Edit Role" : "Create Role"}
        description="Define a role and select which modules and actions users can access."
        breadcrumbs={["Home", "Administration", editId ? "Edit Role" : "New Role"]}
      >
        <form onSubmit={handleSubmit}>
          <FormPageLayout
            main={
              <>
                <FormSection title="Role Details">
                  <FormGrid>
                    <FormField label="Role Name" required>
                      <Input
                        required
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        disabled={isSystem}
                      />
                    </FormField>
                    <FormField label="Slug" required hint="Lowercase identifier, e.g. store_manager">
                      <Input
                        required
                        value={form.slug}
                        onChange={(e) => setForm({ ...form, slug: e.target.value })}
                        className="font-mono"
                        disabled={isSystem}
                      />
                    </FormField>
                    <FormField label="Description" className="md:col-span-2">
                      <Input
                        value={form.description}
                        onChange={(e) => setForm({ ...form, description: e.target.value })}
                      />
                    </FormField>
                  </FormGrid>
                  {isSystem && (
                    <p className="mt-4 text-xs text-muted-foreground">
                      System role name and slug cannot be changed. You can still update permissions.
                    </p>
                  )}
                </FormSection>

                <FormSection
                  title="Permissions"
                  description={`${selectedPermIds.length} permission(s) selected`}
                >
                  <PermissionMatrix
                    permissions={allPermissions}
                    selected={selectedPermIds}
                    onChange={setSelectedPermIds}
                  />
                </FormSection>
              </>
            }
            aside={
              <div className="ds-card p-4 space-y-3">
                <p className="text-sm font-semibold">Summary</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Permissions</span>
                    <span className="font-semibold">{selectedPermIds.length}</span>
                  </div>
                  {isSystem && (
                    <Badge variant="outline">System Role</Badge>
                  )}
                </div>
              </div>
            }
            actions={
              <FormActions>
                <Button type="submit" loading={saving}>
                  {editId ? "Save Role" : "Create Role"}
                </Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/admin")}>
                  Cancel
                </Button>
              </FormActions>
            }
          />
        </form>
      </PageLayout>
    </PermissionGuard>
  );
}
