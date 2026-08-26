import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
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
import { platformApi } from "@/services/api/platform";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";
import { appDialog } from "@/components/feedback/AppDialog";

const FULL_ACCESS_ROLE_SLUGS = new Set(["super_admin", "platform_admin"]);

function canPickShop(user: ReturnType<typeof useAuthStore.getState>["user"]) {
  if (!user) return false;
  return Boolean(
    user.is_super_admin ||
      user.is_platform_admin ||
      user.is_superuser ||
      user.role?.slug === "super_admin" ||
      user.role?.slug === "platform_admin" ||
      user.managed_shop_group ||
      user.permissions?.includes("platform.manage") ||
      user.permissions?.includes("platform.view")
  );
}

export function UserFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const queryTenant = searchParams.get("tenant") || "";
  const authUser = useAuthStore((s) => s.user);
  const { hasPermission } = usePermissions();
  const shopPicker = canPickShop(authUser);

  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [roles, setRoles] = useState<{ id: string; name: string; slug?: string; permissions?: { id: string }[] }[]>([]);
  const [branches, setBranches] = useState<{ id: string; name: string }[]>([]);
  const [shops, setShops] = useState<{ id: string; name: string; slug: string }[]>([]);
  const [allPermissions, setAllPermissions] = useState<Record<string, PermissionItem[]>>({});
  const [selectedPermIds, setSelectedPermIds] = useState<string[]>([]);
  const [rolePermIds, setRolePermIds] = useState<string[]>([]);
  const [tenantLocked, setTenantLocked] = useState(Boolean(queryTenant));
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
    role_id: "",
    branch_id: "",
    tenant_id: queryTenant,
    is_active: true,
  });

  useEffect(() => {
    Promise.all([adminApi.roles(), settingsApi.branches()]).then(([r, b]) => {
      setRoles(r.data);
      setBranches(b.data);
    });
  }, []);

  useEffect(() => {
    adminApi
      .permissions({ tenant: form.tenant_id || undefined })
      .then((p) => setAllPermissions(p.data))
      .catch(() => setAllPermissions({}));
  }, [form.tenant_id]);

  useEffect(() => {
    if (!shopPicker) return;
    platformApi
      .tenants()
      .then((res) => {
        const rows = (res.data || []).map((t) => ({
          id: t.id,
          name: t.name,
          slug: t.slug,
        }));
        setShops(rows);
      })
      .catch(() => setShops([]));
  }, [shopPicker]);

  useEffect(() => {
    if (!editId) return;
    adminApi.getUser(editId).then((res) => {
      const u = res.data;
      setForm({
        username: u.username,
        email: u.email,
        password: "",
        first_name: u.first_name,
        last_name: u.last_name,
        phone: u.phone || "",
        role_id: u.role?.id || "",
        branch_id: u.branch?.id || "",
        tenant_id: u.tenant_id || queryTenant || "",
        is_active: u.is_active,
      });
      setSelectedPermIds(
        (u.permission_ids || u.direct_permissions?.map((p) => p.id) || []).map(String)
      );
      setRolePermIds((u.role_permission_ids || []).map(String));
      if (u.tenant_id && !shopPicker) setTenantLocked(true);
      setLoading(false);
    });
  }, [editId, queryTenant, shopPicker]);

  const lockedShopName = useMemo(() => {
    if (!form.tenant_id) return "";
    return shops.find((s) => s.id === form.tenant_id)?.name || "";
  }, [form.tenant_id, shops]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (shopPicker && !form.tenant_id && !editId) {
      await appDialog.alert("Select the shop this user belongs to.");
      return;
    }
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
      if (form.tenant_id) payload.tenant_id = form.tenant_id;
      const selectedRole = roles.find((r) => r.id === form.role_id);
      const fullAccess = FULL_ACCESS_ROLE_SLUGS.has(selectedRole?.slug || "");
      if (!fullAccess) payload.permission_ids = selectedPermIds;
      if (form.password) payload.password = form.password;
      if (editId) await adminApi.updateUser(editId, payload);
      else {
        if (!form.password) throw new Error("Password is required for new users.");
        await adminApi.createUser({ ...payload, password: form.password });
      }
      navigate("/admin");
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
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
        description="Assign a role and optional direct permissions. Shop binding is automatic for shop admins; platform managers can pick a shop."
        breadcrumbs={["Home", "Administration", editId ? "Edit User" : "New User"]}
      >
        <form onSubmit={handleSubmit}>
          <FormPageLayout
            main={
              <>
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
                    {shopPicker && (
                      <FormField
                        label="Shop"
                        required={!editId}
                        hint={tenantLocked ? "Bound from shop page" : "User will belong to this shop"}
                      >
                        {tenantLocked && form.tenant_id ? (
                          <Input
                            readOnly
                            value={lockedShopName || form.tenant_id}
                            className="bg-muted/40"
                          />
                        ) : (
                          <Select
                            value={form.tenant_id || "none"}
                            onValueChange={(v) => setForm({ ...form, tenant_id: v === "none" ? "" : v })}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select shop" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">Select shop…</SelectItem>
                              {shops.map((s) => (
                                <SelectItem key={s.id} value={s.id}>
                                  {s.name} ({s.slug})
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                      </FormField>
                    )}
                    <FormField label="Role" hint="Super Admin / Platform Admin unlock all features automatically">
                      <Select
                        value={form.role_id || "none"}
                        onValueChange={(v) => {
                          const roleId = v === "none" ? "" : v;
                          setForm({ ...form, role_id: roleId });
                          const role = roles.find((r) => r.id === roleId);
                          const fromRole = (role?.permissions || []).map((p) => String(p.id));
                          setRolePermIds(fromRole);
                          // Reset effective selection to the new role baseline.
                          setSelectedPermIds(fromRole);
                        }}
                      >
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
                          <SelectItem value="none">None (shop default)</SelectItem>
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

                {FULL_ACCESS_ROLE_SLUGS.has(roles.find((r) => r.id === form.role_id)?.slug || "") ? (
                  <FormSection
                    title="Access"
                    description="This role has full access to every module and action. You do not need to grant extra permissions."
                  >
                    <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm">
                      Super Admin / Platform Admin already see all ERP features. Permission checkboxes
                      are only used for cashiers, managers, and other limited roles.
                    </div>
                  </FormSection>
                ) : (
                  <FormSection
                    title="Permissions"
                    description="Shows what this user can do now. Uncheck Users / Administration items to revoke them from a Shop Admin without changing their role."
                  >
                    <PermissionMatrix
                      permissions={allPermissions}
                      selected={selectedPermIds}
                      rolePermissionIds={rolePermIds}
                      onChange={setSelectedPermIds}
                    />
                  </FormSection>
                )}
              </>
            }
            aside={
              <div className="ds-card p-4 space-y-3">
                <p className="text-sm font-semibold">Access control</p>
                <p className="text-xs text-muted-foreground">
                  Role sets the baseline. Direct grants add or tailor access (e.g. gym-only, POS-only, or user management).
                </p>
                {form.tenant_id && (
                  <Badge variant="secondary">
                    Shop: {lockedShopName || form.tenant_id.slice(0, 8)}
                  </Badge>
                )}
                {form.role_id && (
                  <Badge variant="secondary">
                    Role: {roles.find((r) => r.id === form.role_id)?.name ?? "Selected"}
                  </Badge>
                )}
                {!FULL_ACCESS_ROLE_SLUGS.has(roles.find((r) => r.id === form.role_id)?.slug || "") && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Direct grants</span>
                    <span className="font-semibold">{selectedPermIds.length}</span>
                  </div>
                )}
                {hasPermission("users.create") && (
                  <p className="text-xs text-muted-foreground">
                    You can create users. To revoke that for someone else, remove users.create from their direct permissions or role.
                  </p>
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
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
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
                    <FormField label="Name" required>
                      <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} disabled={isSystem} />
                    </FormField>
                    <FormField label="Slug" required hint="Unique code, e.g. warehouse_clerk">
                      <Input required value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} disabled={isSystem} />
                    </FormField>
                    <FormField label="Description">
                      <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                    </FormField>
                  </FormGrid>
                  {isSystem && (
                    <p className="mt-3 text-xs text-muted-foreground">
                      System role name/slug are locked. You can still adjust permissions.
                    </p>
                  )}
                </FormSection>
                <FormSection title="Permissions" description="Modules and actions this role can access.">
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
                <p className="text-sm font-semibold">Role summary</p>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Permissions</span>
                  <span className="font-semibold">{selectedPermIds.length}</span>
                </div>
                {isSystem && <Badge variant="secondary">System role</Badge>}
              </div>
            }
            actions={
              <FormActions>
                <Button type="submit" loading={saving}>{editId ? "Save Changes" : "Create Role"}</Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/admin")}>Cancel</Button>
              </FormActions>
            }
          />
        </form>
      </PageLayout>
    </PermissionGuard>
  );
}
