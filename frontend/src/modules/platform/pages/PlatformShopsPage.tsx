import { useEffect, useState } from "react";
import { Building2, Pencil, Plus, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { PlanCreateInline, SubscriptionEditModal } from "@/components/platform/SubscriptionForm";
import { PlatformCloudNotice } from "@/components/platform/PlatformCloudNotice";
import {
  platformApi,
  type PlatformPlanRow,
  type PlatformShopGroupRow,
  type PlatformSubscriptionRow,
  type PlatformTenantRow,
} from "@/services/api/platform";
import { usePermissions } from "@/hooks/usePermissions";
import { useAuthStore } from "@/store/authStore";
import { formatCurrency } from "@/utils/cn";

type ShopSubscriptionMode = "plan" | "existing" | "none";
type ShopGroupMode = "none" | "existing" | "new";

const SHOP_OWNER_ROLES = [
  { slug: "admin", name: "Shop Admin (desktop POS)" },
  { slug: "shop_group_manager", name: "Multi-Shop Manager (cloud only)" },
  { slug: "branch_manager", name: "Branch Manager" },
  { slug: "accountant", name: "Accountant" },
  { slug: "inventory_manager", name: "Inventory Manager" },
  { slug: "futsal_manager", name: "Futsal Manager" },
];

interface ShopFormState {
  name: string;
  contact_email: string;
  contact_phone: string;
  address: string;
  subscription_mode: ShopSubscriptionMode;
  plan_code: string;
  subscription_status: string;
  trial_days: string;
  subscription_id: string;
  owner_username: string;
  owner_password: string;
  owner_email: string;
  owner_first_name: string;
  owner_last_name: string;
  owner_role_slug: string;
  shop_group_mode: ShopGroupMode;
  shop_group_id: string;
  shop_group_name: string;
}

const EMPTY_FORM: ShopFormState = {
  name: "",
  contact_email: "",
  contact_phone: "",
  address: "",
  subscription_mode: "plan",
  plan_code: "",
  subscription_status: "trial",
  trial_days: "30",
  subscription_id: "",
  owner_username: "",
  owner_password: "",
  owner_email: "",
  owner_first_name: "",
  owner_last_name: "",
  owner_role_slug: "admin",
  shop_group_mode: "none",
  shop_group_id: "",
  shop_group_name: "",
};

interface ShopEditState {
  id: string;
  name: string;
  contact_email: string;
  contact_phone: string;
  address: string;
  country: string;
  is_active: boolean;
  has_subscription: boolean;
  subscription_reference: string;
  subscription_expires_at: string;
  subscription_mode: ShopSubscriptionMode | "keep";
  plan_code: string;
  subscription_status: string;
  trial_days: string;
  subscription_id: string;
  shop_group_id: string;
}

export function PlatformShopsPage() {
  const user = useAuthStore((s) => s.user);
  const { hasPermission } = usePermissions();
  const canManage = Boolean(user?.is_platform_admin || hasPermission("platform.manage"));
  const isGroupManager = Boolean(user?.managed_shop_group);
  const pageTitle = isGroupManager ? "My Shops" : "All Shops";
  const pageDescription = isGroupManager
    ? "Sales and subscription status for every shop in your group."
    : "Manage shops, edit profiles, and link subscriptions.";

  const [shops, setShops] = useState<PlatformTenantRow[]>([]);
  const [shopGroups, setShopGroups] = useState<PlatformShopGroupRow[]>([]);
  const [unassignedSubs, setUnassignedSubs] = useState<PlatformSubscriptionRow[]>([]);
  const [allSubs, setAllSubs] = useState<PlatformSubscriptionRow[]>([]);
  const [plans, setPlans] = useState<PlatformPlanRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<ShopFormState>(EMPTY_FORM);
  const [editingShop, setEditingShop] = useState<ShopEditState | null>(null);
  const [editingSub, setEditingSub] = useState<PlatformSubscriptionRow | null>(null);
  const [shopSaving, setShopSaving] = useState(false);
  const [shopEditError, setShopEditError] = useState("");
  const [formError, setFormError] = useState("");
  const [shopSyncInfo, setShopSyncInfo] = useState({
    slug: "",
    sync_secret: "",
    last_synced_at: "",
  });

  const load = () => {
    setLoading(true);
    const requests: Promise<unknown>[] = [
      platformApi.tenants("month"),
      platformApi.subscriptions(true),
      platformApi.subscriptions(),
      platformApi.plans(),
    ];
    if (canManage) {
      requests.push(platformApi.shopGroups());
    }
    Promise.all(requests)
      .then((results) => {
        const [tenantsRes, unassignedRes, allRes, plansRes, groupsRes] = results as [
          Awaited<ReturnType<typeof platformApi.tenants>>,
          Awaited<ReturnType<typeof platformApi.subscriptions>>,
          Awaited<ReturnType<typeof platformApi.subscriptions>>,
          Awaited<ReturnType<typeof platformApi.plans>>,
          Awaited<ReturnType<typeof platformApi.shopGroups>> | undefined,
        ];
        setShops(tenantsRes.data);
        setUnassignedSubs(unassignedRes.data);
        setAllSubs(allRes.data);
        setPlans(plansRes.data);
        if (groupsRes) setShopGroups(groupsRes.data);
        setForm((prev) => {
          if (prev.plan_code || !plansRes.data.length) return prev;
          return { ...prev, plan_code: plansRes.data[0].code };
        });
      })
      .catch((err) => {
        setShops([]);
        setUnassignedSubs([]);
        setAllSubs([]);
        setFormError(err instanceof Error ? err.message : "Could not load shops from server.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const openEditShop = async (shop: PlatformTenantRow) => {
    setShopEditError("");
    const detail = await platformApi.tenant(shop.id);
    const tenant = detail.data.tenant as Record<string, unknown>;
    const company = detail.data.company as Record<string, unknown> | null;
    const subscription = detail.data.subscription as Record<string, unknown> | null;
    const hasSubscription = Boolean(subscription?.id);
    setEditingShop({
      id: shop.id,
      name: String(tenant.name ?? shop.name),
      contact_email: String(tenant.contact_email ?? shop.contact_email ?? ""),
      contact_phone: String(tenant.contact_phone ?? ""),
      address: String(company?.address ?? ""),
      country: String(tenant.country ?? ""),
      is_active: Boolean(tenant.is_active ?? true),
      has_subscription: hasSubscription,
      subscription_reference: String(subscription?.reference_code ?? ""),
      subscription_expires_at: String(subscription?.expires_at ?? ""),
      subscription_mode: hasSubscription ? "keep" : "plan",
      plan_code: String(subscription?.plan_code ?? plans[0]?.code ?? ""),
      subscription_status: String(subscription?.status ?? "trial"),
      trial_days: "30",
      subscription_id: "",
      shop_group_id: String(tenant.shop_group_id ?? ""),
    });
    setShopSyncInfo({
      slug: String(tenant.slug ?? ""),
      sync_secret: String(tenant.sync_secret ?? ""),
      last_synced_at: String(tenant.last_synced_at ?? ""),
    });
    if (shop.subscription?.id) {
      const sub = allSubs.find((s) => s.id === shop.subscription?.id);
      if (sub) setEditingSub(sub);
      else {
        platformApi.subscription(shop.subscription.id).then((res) => setEditingSub(res.data)).catch(() => {});
      }
    } else {
      setEditingSub(null);
    }
  };

  const saveShop = async () => {
    if (!editingShop) return;
    if (!editingShop.has_subscription) {
      if (editingShop.subscription_mode === "plan" && !editingShop.plan_code) {
        setShopEditError("Select a subscription plan.");
        return;
      }
      if (editingShop.subscription_mode === "existing" && !editingShop.subscription_id) {
        setShopEditError("Select an existing subscription license.");
        return;
      }
    }
    setShopSaving(true);
    setShopEditError("");
    try {
      const payload: Record<string, unknown> = {
        name: editingShop.name,
        contact_email: editingShop.contact_email,
        contact_phone: editingShop.contact_phone,
        address: editingShop.address,
        country: editingShop.country,
        is_active: editingShop.is_active,
      };
      if (editingShop.has_subscription) {
        if (editingShop.plan_code) payload.plan_code = editingShop.plan_code;
        payload.status = editingShop.subscription_status;
      } else if (editingShop.subscription_mode === "existing" && editingShop.subscription_id) {
        payload.subscription_id = editingShop.subscription_id;
      } else if (editingShop.subscription_mode === "plan" && editingShop.plan_code) {
        payload.plan_code = editingShop.plan_code;
        payload.status = editingShop.subscription_status;
        payload.trial_days = Number(editingShop.trial_days) || 30;
      }
      if (editingShop.shop_group_id) payload.shop_group_id = editingShop.shop_group_id;
      await platformApi.updateShop(editingShop.id, payload);
      setEditingShop(null);
      load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not save shop.";
      setShopEditError(message);
    } finally {
      setShopSaving(false);
    }
  };

  const createShop = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setFormError("Shop name is required.");
      return;
    }
    if (form.subscription_mode === "plan" && !form.plan_code) {
      setFormError("Select a subscription plan.");
      return;
    }
    if (form.subscription_mode === "existing" && !form.subscription_id) {
      setFormError("Select an existing subscription license.");
      return;
    }
    if (!form.owner_username.trim()) {
      setFormError("Shop owner username is required.");
      return;
    }
    if (form.owner_password.length < 8) {
      setFormError("Shop owner password must be at least 8 characters.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        contact_email: form.contact_email,
        contact_phone: form.contact_phone,
        address: form.address,
      };
      if (form.subscription_mode === "existing" && form.subscription_id) {
        payload.subscription_id = form.subscription_id;
      } else if (form.subscription_mode === "plan" && form.plan_code) {
        payload.plan_code = form.plan_code;
        payload.status = form.subscription_status;
        payload.trial_days = Number(form.trial_days) || 30;
      }
      if (form.shop_group_mode === "existing" && form.shop_group_id) {
        payload.shop_group_id = form.shop_group_id;
      } else if (form.shop_group_mode === "new" && form.shop_group_name.trim()) {
        payload.shop_group_name = form.shop_group_name.trim();
      }
      if (form.owner_role_slug === "shop_group_manager") {
        payload.assign_owner_as_group_manager = true;
      }
      payload.owner = {
        username: form.owner_username.trim(),
        password: form.owner_password,
        email: form.owner_email.trim() || form.contact_email.trim(),
        first_name: form.owner_first_name.trim(),
        last_name: form.owner_last_name.trim(),
        phone: form.contact_phone.trim(),
        role_slug: form.owner_role_slug || "admin",
      };
      const res = await platformApi.createShop(payload);
      const owner = (res.data as { owner?: { username: string } }).owner;
      setShowForm(false);
      setForm(EMPTY_FORM);
      load();
      if (owner?.username) {
        alert(`Shop created. Owner can log in with username: ${owner.username}`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not create shop.";
      setFormError(message);
      alert(message);
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<PlatformTenantRow>[] = [
    { key: "name", header: "Shop", cell: (r) => <span className="font-medium">{r.name}</span> },
    ...(isGroupManager || shopGroups.length
      ? [
          {
            key: "group",
            header: "Group",
            cell: (r: PlatformTenantRow) => r.shop_group_name ?? "—",
          } as Column<PlatformTenantRow>,
        ]
      : []),
    { key: "plan", header: "Plan", cell: (r) => r.subscription?.plan ?? "—" },
    { key: "ref", header: "Subscription", cell: (r) => r.subscription?.reference_code ?? "—" },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={r.subscription?.is_usable ? "success" : "destructive"}>
          {r.subscription?.status ?? "none"}
        </Badge>
      ),
    },
    {
      key: "fee",
      header: "Monthly fee",
      cell: (r) =>
        r.subscription?.monthly_fee != null
          ? formatCurrency(r.subscription.monthly_fee)
          : r.subscription
            ? formatCurrency(r.subscription.monthly_price)
            : "—",
    },
    {
      key: "sales",
      header: "Sales (month)",
      cell: (r) => formatCurrency(r.kpis?.total_sales ?? 0),
    },
    {
      key: "expires",
      header: "Expires",
      cell: (r) => r.subscription?.expires_at ?? "—",
    },
    {
      key: "actions",
      header: "Actions",
      cell: (r) =>
        canManage ? (
          <Button size="sm" variant="secondary" onClick={() => openEditShop(r)}>
            <Pencil className="h-3 w-3" />
            Edit
          </Button>
        ) : (
          <span className="text-sm text-muted-foreground">View only</span>
        ),
    },
  ];

  const groupTotals = shops.reduce(
    (acc, s) => ({
      sales: acc.sales + (s.kpis?.total_sales ?? 0),
      revenue: acc.revenue + (s.kpis?.revenue ?? 0),
    }),
    { sales: 0, revenue: 0 }
  );

  return (
    <PageLayout
      title={`Platform — ${pageTitle}`}
      description={pageDescription}
      breadcrumbs={["Home", "Platform"]}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={load}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          {canManage && (
            <Button
              size="sm"
              onClick={() => {
                setShowForm((v) => !v);
                setFormError("");
                if (!showForm) {
                  setForm({
                    ...EMPTY_FORM,
                    plan_code: plans[0]?.code ?? "",
                  });
                }
              }}
            >
              <Plus className="h-4 w-4" /> Add Shop
            </Button>
          )}
        </div>
      }
    >
      <PlatformCloudNotice />
      {isGroupManager && shops.length > 0 && (
        <div className="mb-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-sm text-muted-foreground">Shops in group</p>
            <p className="text-2xl font-semibold">{shops.length}</p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-sm text-muted-foreground">Combined sales (month)</p>
            <p className="text-2xl font-semibold">{formatCurrency(groupTotals.sales)}</p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-sm text-muted-foreground">Group</p>
            <p className="text-lg font-semibold">{user?.managed_shop_group?.name ?? "—"}</p>
          </div>
        </div>
      )}
      {formError && !showForm && (
        <p className="mb-4 text-sm text-destructive">{formError}</p>
      )}
      <SubscriptionEditModal
        subscription={editingSub}
        shops={shops}
        plans={plans}
        open={!!editingSub && !editingShop}
        onClose={() => setEditingSub(null)}
        onSaved={load}
      />

      {editingShop && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl">
            <h2 className="text-lg font-semibold">Edit Shop — {editingShop.name}</h2>
            <div className="mt-6">
              <FormGrid>
                <FormField label="Shop name" required>
                  <Input
                    value={editingShop.name}
                    onChange={(e) => setEditingShop({ ...editingShop, name: e.target.value })}
                  />
                </FormField>
                <FormField label="Contact email">
                  <Input
                    type="email"
                    value={editingShop.contact_email}
                    onChange={(e) => setEditingShop({ ...editingShop, contact_email: e.target.value })}
                  />
                </FormField>
                <FormField label="Phone">
                  <Input
                    value={editingShop.contact_phone}
                    onChange={(e) => setEditingShop({ ...editingShop, contact_phone: e.target.value })}
                  />
                </FormField>
                <FormField label="Country">
                  <Input
                    value={editingShop.country}
                    onChange={(e) => setEditingShop({ ...editingShop, country: e.target.value })}
                  />
                </FormField>
                <FormField label="Address" className="md:col-span-2">
                  <Input
                    value={editingShop.address}
                    onChange={(e) => setEditingShop({ ...editingShop, address: e.target.value })}
                  />
                </FormField>
                <FormField label="Status">
                  <Select
                    value={editingShop.is_active ? "active" : "inactive"}
                    onValueChange={(v) =>
                      setEditingShop({ ...editingShop, is_active: v === "active" })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
              </FormGrid>

              {canManage && (
                <div className="mt-8 border-t border-border pt-6">
                  <h3 className="text-base font-semibold text-foreground">Shop group</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Link shops under one owner (e.g. Shop A and Shop B) for a multi-shop manager on the cloud.
                  </p>
                  <FormGrid className="mt-4">
                    <FormField label="Group assignment" className="md:col-span-2">
                      <Select
                        value={editingShop.shop_group_id || "__none__"}
                        onValueChange={(v) =>
                          setEditingShop({
                            ...editingShop,
                            shop_group_id: v === "__none__" ? "" : v,
                          })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="No group" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="__none__">No group</SelectItem>
                          {shopGroups.map((g) => (
                            <SelectItem key={g.id} value={g.id}>
                              {g.name} ({g.shop_count} shops)
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormField>
                  </FormGrid>
                </div>
              )}

              <div className="mt-8 border-t border-border pt-6">
                <h3 className="text-base font-semibold text-foreground">Subscription</h3>
                {editingShop.has_subscription ? (
                  <>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {editingShop.subscription_reference}
                      {editingShop.subscription_expires_at
                        ? ` · expires ${editingShop.subscription_expires_at}`
                        : ""}
                    </p>
                    <FormGrid className="mt-4">
                      <FormField label="Plan" className="md:col-span-2">
                        <div className="flex flex-wrap items-start gap-2">
                          <div className="min-w-[220px] flex-1">
                            <Select
                              value={editingShop.plan_code || undefined}
                              onValueChange={(v) =>
                                setEditingShop({ ...editingShop, plan_code: v })
                              }
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select plan" />
                              </SelectTrigger>
                              <SelectContent>
                                {plans.map((plan) => (
                                  <SelectItem key={plan.code} value={plan.code}>
                                    {plan.name} (default {formatCurrency(plan.monthly_price)}/mo)
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <PlanCreateInline
                            onCreated={(plan) => {
                              setPlans((prev) => [...prev, plan]);
                              setEditingShop((prev) =>
                                prev ? { ...prev, plan_code: plan.code } : prev
                              );
                            }}
                          />
                        </div>
                      </FormField>
                      <FormField label="Subscription status">
                        <Select
                          value={editingShop.subscription_status}
                          onValueChange={(v) =>
                            setEditingShop({ ...editingShop, subscription_status: v })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="trial">Trial</SelectItem>
                            <SelectItem value="active">Active</SelectItem>
                            <SelectItem value="expired">Expired</SelectItem>
                            <SelectItem value="suspended">Suspended</SelectItem>
                          </SelectContent>
                        </Select>
                      </FormField>
                    </FormGrid>
                  </>
                ) : (
                  <>
                    <p className="mt-1 text-sm text-muted-foreground">
                      This shop has no subscription. Assign a plan or existing license below.
                    </p>
                    <FormGrid className="mt-4">
                      <FormField label="Assign subscription" className="md:col-span-2">
                        <Select
                          value={editingShop.subscription_mode}
                          onValueChange={(v) =>
                            setEditingShop({
                              ...editingShop,
                              subscription_mode: v as ShopSubscriptionMode,
                              subscription_id: "",
                            })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="plan">New subscription from plan</SelectItem>
                            <SelectItem value="existing">Use existing license</SelectItem>
                          </SelectContent>
                        </Select>
                      </FormField>
                      {editingShop.subscription_mode === "plan" && (
                        <>
                          <FormField label="Plan" required className="md:col-span-2">
                            <div className="flex flex-wrap items-start gap-2">
                              <div className="min-w-[220px] flex-1">
                                <Select
                                  value={editingShop.plan_code || undefined}
                                  onValueChange={(v) =>
                                    setEditingShop({ ...editingShop, plan_code: v })
                                  }
                                >
                                  <SelectTrigger>
                                    <SelectValue placeholder="Select plan" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {plans.map((plan) => (
                                      <SelectItem key={plan.code} value={plan.code}>
                                        {plan.name} (default {formatCurrency(plan.monthly_price)}/mo)
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <PlanCreateInline
                                onCreated={(plan) => {
                                  setPlans((prev) => [...prev, plan]);
                                  setEditingShop((prev) =>
                                    prev ? { ...prev, plan_code: plan.code } : prev
                                  );
                                }}
                              />
                            </div>
                          </FormField>
                          <FormField label="Subscription status">
                            <Select
                              value={editingShop.subscription_status}
                              onValueChange={(v) =>
                                setEditingShop({ ...editingShop, subscription_status: v })
                              }
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="trial">Trial</SelectItem>
                                <SelectItem value="active">Active</SelectItem>
                              </SelectContent>
                            </Select>
                          </FormField>
                          <FormField label="Initial period (days)" hint="Days until first expiry date.">
                            <Input
                              type="number"
                              min={1}
                              value={editingShop.trial_days}
                              onChange={(e) =>
                                setEditingShop({ ...editingShop, trial_days: e.target.value })
                              }
                            />
                          </FormField>
                        </>
                      )}
                      {editingShop.subscription_mode === "existing" && (
                        <FormField label="Existing license" required className="md:col-span-2">
                          <Select
                            value={editingShop.subscription_id || undefined}
                            onValueChange={(v) =>
                              setEditingShop({ ...editingShop, subscription_id: v })
                            }
                          >
                            <SelectTrigger>
                              <SelectValue
                                placeholder={
                                  unassignedSubs.length ? "Select license" : "No unassigned licenses"
                                }
                              />
                            </SelectTrigger>
                            <SelectContent>
                              {unassignedSubs.map((sub) => (
                                <SelectItem key={sub.id} value={sub.id}>
                                  {sub.reference_code} — {sub.plan}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </FormField>
                      )}
                    </FormGrid>
                  </>
                )}
              </div>
            </div>
            {shopSyncInfo.slug && (
              <div className="mt-4 rounded-lg border border-border bg-muted/40 p-4 text-sm">
                <p className="font-medium">Shop sync credentials (copy to shop PC)</p>
                <p className="mt-2 font-mono">Slug: {shopSyncInfo.slug}</p>
                <p className="mt-1 break-all font-mono">Secret: {shopSyncInfo.sync_secret}</p>
                <p className="mt-2 text-muted-foreground">
                  Last synced: {shopSyncInfo.last_synced_at || "Never"}
                </p>
              </div>
            )}
            {shopEditError && <p className="mt-3 text-sm text-destructive">{shopEditError}</p>}
            <div className="mt-6 flex flex-wrap justify-between gap-2">
              <div className="flex gap-2">
                {editingSub && (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setEditingShop(null);
                    }}
                  >
                    Edit subscription
                  </Button>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => setEditingShop(null)}>
                  Cancel
                </Button>
                <Button loading={shopSaving} onClick={saveShop}>
                  Save Shop
                </Button>
              </div>
            </div>
            {editingSub && (
              <p className="mt-3 text-xs text-muted-foreground">
                Subscription {editingSub.reference_code} — close this dialog and use Subscriptions → Edit for fee and alerts, or{" "}
                <button
                  type="button"
                  className="text-primary underline"
                  onClick={() => {
                    const sub = editingSub;
                    setEditingShop(null);
                    setEditingSub(sub);
                  }}
                >
                  edit subscription now
                </button>
                .
              </p>
            )}
          </div>
        </div>
      )}

      {showForm && (
        <form onSubmit={createShop} className="mb-6">
          <FormSection
            title="New Shop"
            description="Create the shop, assign a subscription, and set up the owner login for the shop manager."
          >
            <FormGrid>
              <FormField label="Shop name" required>
                <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </FormField>
              <FormField label="Contact email">
                <Input
                  type="email"
                  value={form.contact_email}
                  onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                />
              </FormField>
              <FormField label="Phone">
                <Input value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
              </FormField>
              <FormField label="Address" className="md:col-span-2">
                <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
              </FormField>
            </FormGrid>

            {canManage && (
              <div className="mt-8 border-t border-border pt-6">
                <h3 className="text-base font-semibold text-foreground">Shop group</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Optional — group multiple cafeterias under one multi-shop manager account.
                </p>
                <FormGrid className="mt-4">
                  <FormField label="Group" className="md:col-span-2">
                    <Select
                      value={form.shop_group_mode}
                      onValueChange={(v) =>
                        setForm({
                          ...form,
                          shop_group_mode: v as ShopGroupMode,
                          shop_group_id: "",
                          shop_group_name: "",
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No group</SelectItem>
                        <SelectItem value="existing">Link to existing group</SelectItem>
                        <SelectItem value="new">Create new group</SelectItem>
                      </SelectContent>
                    </Select>
                  </FormField>
                  {form.shop_group_mode === "existing" && (
                    <FormField label="Existing group" required className="md:col-span-2">
                      <Select
                        value={form.shop_group_id || undefined}
                        onValueChange={(v) => setForm({ ...form, shop_group_id: v })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder={shopGroups.length ? "Select group" : "No groups yet"} />
                        </SelectTrigger>
                        <SelectContent>
                          {shopGroups.map((g) => (
                            <SelectItem key={g.id} value={g.id}>
                              {g.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormField>
                  )}
                  {form.shop_group_mode === "new" && (
                    <FormField label="New group name" required className="md:col-span-2">
                      <Input
                        required
                        value={form.shop_group_name}
                        onChange={(e) => setForm({ ...form, shop_group_name: e.target.value })}
                        placeholder="e.g. A&M Holdings"
                      />
                    </FormField>
                  )}
                </FormGrid>
              </div>
            )}

            <div className="mt-8 border-t border-border pt-6">
              <h3 className="text-base font-semibold text-foreground">Shop owner account</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Per-shop desktop users use Shop Admin. Multi-Shop Manager logs into the cloud browser only.
              </p>
              <FormGrid className="mt-4">
                <FormField label="Username" required>
                  <Input
                    required
                    value={form.owner_username}
                    onChange={(e) => setForm({ ...form, owner_username: e.target.value })}
                    placeholder="e.g. am_manager"
                  />
                </FormField>
                <FormField label="Password" required hint="Minimum 8 characters. Share securely with the shop manager.">
                  <Input
                    required
                    type="password"
                    minLength={8}
                    value={form.owner_password}
                    onChange={(e) => setForm({ ...form, owner_password: e.target.value })}
                  />
                </FormField>
                <FormField label="Email" hint="Defaults to shop contact email if empty.">
                  <Input
                    type="email"
                    value={form.owner_email}
                    onChange={(e) => setForm({ ...form, owner_email: e.target.value })}
                  />
                </FormField>
                <FormField label="Role">
                  <Select
                    value={form.owner_role_slug}
                    onValueChange={(v) => setForm({ ...form, owner_role_slug: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SHOP_OWNER_ROLES.map((role) => (
                        <SelectItem key={role.slug} value={role.slug}>
                          {role.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="First name">
                  <Input
                    value={form.owner_first_name}
                    onChange={(e) => setForm({ ...form, owner_first_name: e.target.value })}
                  />
                </FormField>
                <FormField label="Last name">
                  <Input
                    value={form.owner_last_name}
                    onChange={(e) => setForm({ ...form, owner_last_name: e.target.value })}
                  />
                </FormField>
              </FormGrid>
            </div>

            <div className="mt-8 border-t border-border pt-6">
              <h3 className="text-base font-semibold text-foreground">Subscription</h3>
              <FormGrid className="mt-4">
              <FormField label="Subscription" className="md:col-span-2">
                <Select
                  value={form.subscription_mode}
                  onValueChange={(v) =>
                    setForm({
                      ...form,
                      subscription_mode: v as ShopSubscriptionMode,
                      subscription_id: "",
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="plan">New subscription from plan</SelectItem>
                    <SelectItem value="existing">Use existing license</SelectItem>
                    <SelectItem value="none">No subscription</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>
              {form.subscription_mode === "plan" && (
                <>
                  <FormField label="Plan" required className="md:col-span-2">
                    <div className="flex flex-wrap items-start gap-2">
                      <div className="min-w-[220px] flex-1">
                        <Select
                          value={form.plan_code || undefined}
                          onValueChange={(v) => setForm({ ...form, plan_code: v })}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder={plans.length ? "Select plan" : "No plans — create one"} />
                          </SelectTrigger>
                          <SelectContent>
                            {plans.map((plan) => (
                              <SelectItem key={plan.code} value={plan.code}>
                                {plan.name} (default {formatCurrency(plan.monthly_price)}/mo)
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <PlanCreateInline
                        onCreated={(plan) => {
                          setPlans((prev) => [...prev, plan]);
                          setForm((prev) => ({ ...prev, plan_code: plan.code }));
                        }}
                      />
                    </div>
                  </FormField>
                  <FormField label="Subscription status">
                    <Select
                      value={form.subscription_status}
                      onValueChange={(v) => setForm({ ...form, subscription_status: v })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="trial">Trial</SelectItem>
                        <SelectItem value="active">Active</SelectItem>
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Initial period (days)" hint="Days until first expiry date.">
                    <Input
                      type="number"
                      min={1}
                      value={form.trial_days}
                      onChange={(e) => setForm({ ...form, trial_days: e.target.value })}
                    />
                  </FormField>
                </>
              )}
              {form.subscription_mode === "existing" && (
                <FormField label="Existing license" required className="md:col-span-2">
                  <Select
                    value={form.subscription_id || undefined}
                    onValueChange={(v) => setForm({ ...form, subscription_id: v })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={unassignedSubs.length ? "Select license" : "No unassigned licenses"} />
                    </SelectTrigger>
                    <SelectContent>
                      {unassignedSubs.map((sub) => (
                        <SelectItem key={sub.id} value={sub.id}>
                          {sub.reference_code} — {sub.plan}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
              )}
              </FormGrid>
            </div>
            {formError && <p className="mt-3 text-sm text-destructive">{formError}</p>}
            <div className="mt-4 flex gap-3">
              <Button type="submit" loading={saving}>
                <Building2 className="h-4 w-4" /> Create Shop
              </Button>
              <Link to="/platform/subscriptions" className="text-sm text-primary hover:underline self-center">
                Manage subscriptions
              </Link>
            </div>
          </FormSection>
        </form>
      )}

      <DataTable
        exportTitle="Platform Shops"
        columns={columns}
        data={shops}
        loading={loading}
        emptyMessage={isGroupManager ? "No shops linked to your group yet." : "No shops yet. Add your first shop."}
        defaultPageSize={10}
      />
    </PageLayout>
  );
}
