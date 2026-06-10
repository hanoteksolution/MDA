import { useEffect, useState, useCallback, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Shield, Users, UserPlus, Pencil, Trash2, KeyRound } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { ContentSection } from "@/components/layout/ContentSection";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { DataTable, type Column } from "@/components/data/DataTable";
import { PermissionMatrix, type PermissionItem } from "@/components/auth/PermissionMatrix";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { adminApi } from "@/services/api/admin";
import { usePermissions } from "@/hooks/usePermissions";
import type { AdminUser, RoleDetail } from "@/types/models/admin";

export function AdminPage() {
  const navigate = useNavigate();
  const { hasPermission, hasAnyPermission } = usePermissions();
  const canManageUsers = hasPermission("users.view");
  const canManageRoles = hasPermission("roles.view");
  const canCreateUser = hasPermission("users.create");
  const canCreateRole = hasPermission("roles.create");
  const canDeleteUser = hasPermission("users.delete");

  const defaultTab = canManageUsers ? "users" : canManageRoles ? "roles" : "permissions";
  const [tab, setTab] = useState(defaultTab);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roles, setRoles] = useState<RoleDetail[]>([]);
  const [permissions, setPermissions] = useState<Record<string, PermissionItem[]>>({});
  const [permSearch, setPermSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const loadUsers = useCallback(async () => {
    if (!canManageUsers) return;
    setLoading(true);
    try {
      const res = await adminApi.users(search || undefined);
      setUsers(res.data);
    } finally {
      setLoading(false);
    }
  }, [search, canManageUsers]);

  const loadRoles = useCallback(async () => {
    if (!canManageRoles) return;
    setLoading(true);
    try {
      const res = await adminApi.roles();
      setRoles(res.data);
    } finally {
      setLoading(false);
    }
  }, [canManageRoles]);

  const loadPermissions = useCallback(async () => {
    if (!canManageRoles) return;
    setLoading(true);
    try {
      const res = await adminApi.permissions();
      setPermissions(res.data);
    } finally {
      setLoading(false);
    }
  }, [canManageRoles]);

  useEffect(() => {
    if (tab === "users") loadUsers();
    else if (tab === "roles") loadRoles();
    else loadPermissions();
  }, [tab, loadUsers, loadRoles, loadPermissions]);

  const handleDeactivateUser = async (id: string, username: string) => {
    if (!confirm(`Deactivate user "${username}"? They will no longer be able to sign in.`)) return;
    try {
      await adminApi.deactivateUser(id);
      loadUsers();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to deactivate user");
    }
  };

  const activeUsers = users.filter((u) => u.is_active).length;

  const filteredPermissions = useMemo(() => {
    const q = permSearch.trim().toLowerCase();
    if (!q) return permissions;
    const filtered: Record<string, PermissionItem[]> = {};
    for (const [module, perms] of Object.entries(permissions)) {
      const match = perms.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.codename.toLowerCase().includes(q) ||
          module.toLowerCase().includes(q)
      );
      if (match.length) filtered[module] = match;
    }
    return filtered;
  }, [permissions, permSearch]);
  const totalPermissionCount = Object.values(permissions).flat().length;

  const userColumns: Column<AdminUser>[] = [
    {
      key: "user",
      header: "User",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.first_name} {r.last_name}</p>
          <p className="text-xs text-muted-foreground">@{r.username}</p>
        </div>
      ),
      exportValue: (r) => `${r.first_name} ${r.last_name} (@${r.username})`,
    },
    { key: "email", header: "Email", cell: (r) => r.email, exportValue: (r) => r.email },
    { key: "role", header: "Role", cell: (r) => r.role?.name ?? "—", exportValue: (r) => r.role?.name ?? "—" },
    { key: "branch", header: "Branch", cell: (r) => r.branch?.name ?? "—", exportValue: (r) => r.branch?.name ?? "—" },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={r.is_active ? "success" : "secondary"}>
          {r.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
      exportValue: (r) => (r.is_active ? "Active" : "Inactive"),
    },
    {
      key: "actions",
      header: "",
      cell: (r) => (
        <div className="flex gap-1 justify-end">
          {hasPermission("users.update") && (
            <Button variant="ghost" size="sm" onClick={() => navigate(`/admin/users/${r.id}/edit`)}>
              <Pencil className="h-4 w-4" />
            </Button>
          )}
          {canDeleteUser && r.is_active && (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive"
              onClick={() => handleDeactivateUser(r.id, r.username)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  const roleColumns: Column<RoleDetail>[] = [
    { key: "name", header: "Role", cell: (r) => <span className="font-medium">{r.name}</span>, exportValue: (r) => r.name },
    { key: "slug", header: "Slug", cell: (r) => <span className="font-mono text-xs">{r.slug}</span>, exportValue: (r) => r.slug },
    { key: "desc", header: "Description", cell: (r) => r.description || "—", exportValue: (r) => r.description || "—" },
    {
      key: "perms",
      header: "Permissions",
      cell: (r) => <Badge variant="secondary">{r.permission_count}</Badge>,
      exportValue: (r) => String(r.permission_count),
    },
    {
      key: "type",
      header: "Type",
      cell: (r) => (
        <Badge variant={r.is_system ? "outline" : "secondary"}>
          {r.is_system ? "System" : "Custom"}
        </Badge>
      ),
      exportValue: (r) => (r.is_system ? "System" : "Custom"),
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        hasPermission("roles.update") ? (
          <Button variant="ghost" size="sm" onClick={() => navigate(`/admin/roles/${r.id}/edit`)}>
            <Pencil className="h-4 w-4" />
          </Button>
        ) : null,
    },
  ];

  if (!hasAnyPermission("users.view", "roles.view")) {
    return (
      <PageLayout title="Access Denied" breadcrumbs={["Home", "Administration"]}>
        <p className="text-muted-foreground">You do not have permission to manage users or roles.</p>
      </PageLayout>
    );
  }

  const tabs = [
    ...(canManageUsers ? [{ id: "users", label: "Users", count: users.length }] : []),
    ...(canManageRoles ? [{ id: "roles", label: "Roles", count: roles.length }] : []),
    ...(canManageRoles ? [{ id: "permissions", label: "Permissions", count: totalPermissionCount }] : []),
  ];

  return (
    <PageLayout
      title="User & Access Management"
      description="Manage users, roles, and granular permissions across the system."
      breadcrumbs={["Home", "Administration"]}
      actions={
        tab === "users" && canCreateUser ? (
          <Button asChild>
            <Link to="/admin/users/new"><UserPlus className="h-4 w-4" /> Add User</Link>
          </Button>
        ) : tab === "roles" && canCreateRole ? (
          <Button asChild>
            <Link to="/admin/roles/new"><Shield className="h-4 w-4" /> Add Role</Link>
          </Button>
        ) : undefined
      }
    >
      <KpiGrid>
        <KpiCard title="Total Users" value={String(users.length)} icon={<Users className="h-5 w-5" />} loading={loading && tab === "users"} />
        <KpiCard title="Active Users" value={String(activeUsers)} icon={<Users className="h-5 w-5" />} loading={loading && tab === "users"} />
        <KpiCard title="Roles" value={String(roles.length)} icon={<Shield className="h-5 w-5" />} loading={loading && tab === "roles"} />
        <KpiCard title="Permissions" value={String(totalPermissionCount)} icon={<KeyRound className="h-5 w-5" />} loading={loading && tab === "permissions"} />
      </KpiGrid>

      <TabNav tabs={tabs} active={tab} onChange={setTab} />

      {tab === "users" && canManageUsers && (
        <ContentSection title="User Accounts" description="Create and manage system users" noPadding>
          <DataTable
            embedded
            exportTitle="Users"
            columns={userColumns}
            data={users}
            loading={loading}
            searchPlaceholder="Search users..."
            searchValue={search}
            onSearchChange={setSearch}
            emptyMessage="No users found."
            defaultPageSize={10}
          />
        </ContentSection>
      )}

      {tab === "roles" && canManageRoles && (
        <ContentSection title="Roles" description="Assign permission sets to user groups" noPadding>
          <DataTable
            embedded
            exportTitle="Roles"
            columns={roleColumns}
            data={roles}
            loading={loading}
            emptyMessage="No roles configured."
            defaultPageSize={10}
          />
        </ContentSection>
      )}

      {tab === "permissions" && canManageRoles && (
        <ContentSection
          title="Permission Catalog"
          description="All permissions available in the system, grouped by module"
        >
          <div className="mb-4 max-w-md">
            <Input
              value={permSearch}
              onChange={(e) => setPermSearch(e.target.value)}
              placeholder="Search permissions..."
            />
          </div>
          {loading ? (
            <div className="h-64 animate-pulse rounded-xl bg-muted" />
          ) : (
            <PermissionMatrix
              permissions={filteredPermissions}
              selected={[]}
              onChange={() => {}}
              readOnly
            />
          )}
        </ContentSection>
      )}
    </PageLayout>
  );
}
