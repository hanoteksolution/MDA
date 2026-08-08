import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Armchair, CookingPot, Plus, UtensilsCrossed } from "lucide-react";
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
  restaurantApi,
  type DiningTable,
  type MenuCategory,
  type MenuItem,
  type RestaurantOrder,
  type RestaurantSummary,
} from "@/services/api/restaurant";
import { formatCurrency } from "@/utils/cn";

type Tab = "orders" | "menu" | "tables";

export function RestaurantPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("restaurant.manage");
  const canFloor = hasPermission("restaurant.floor") || canManage;

  const [tab, setTab] = useState<Tab>("orders");
  const [summary, setSummary] = useState<RestaurantSummary | null>(null);
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [tables, setTables] = useState<DiningTable[]>([]);
  const [orders, setOrders] = useState<RestaurantOrder[]>([]);
  const [loading, setLoading] = useState(true);

  const [catForm, setCatForm] = useState({ name: "" });
  const [itemForm, setItemForm] = useState({ name: "", category_id: "", unit_price: "" });
  const [tableForm, setTableForm] = useState({ code: "", label: "", capacity: "4" });
  const [orderForm, setOrderForm] = useState({ table_id: "", menu_item_id: "", quantity: "1" });

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const [sumRes, catRes, itemRes, tableRes, orderRes] = await Promise.all([
        restaurantApi.summary(branchId),
        restaurantApi.categories(1, branchId),
        restaurantApi.items(1, branchId),
        restaurantApi.tables(1, branchId),
        restaurantApi.orders(1, branchId),
      ]);
      setSummary(sumRes.data);
      setCategories(catRes.data.results);
      setItems(itemRes.data.results);
      setTables(tableRes.data.results);
      setOrders(orderRes.data.results);
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const addCategory = async () => {
    if (!branchId || !catForm.name) return;
    await restaurantApi.createCategory({ name: catForm.name, branch_id: branchId });
    setCatForm({ name: "" });
    void reload();
  };

  const addItem = async () => {
    if (!branchId || !itemForm.name || !itemForm.category_id) return;
    await restaurantApi.createItem({
      name: itemForm.name,
      branch_id: branchId,
      category_id: itemForm.category_id,
      unit_price: Number(itemForm.unit_price) || 0,
    });
    setItemForm({ name: "", category_id: "", unit_price: "" });
    void reload();
  };

  const addTable = async () => {
    if (!branchId || !tableForm.code) return;
    await restaurantApi.createTable({
      code: tableForm.code,
      label: tableForm.label,
      capacity: Number(tableForm.capacity) || 4,
      branch_id: branchId,
    });
    setTableForm({ code: "", label: "", capacity: "4" });
    void reload();
  };

  const addOrder = async () => {
    if (!branchId || !orderForm.menu_item_id) return;
    await restaurantApi.createOrder({
      branch_id: branchId,
      table_id: orderForm.table_id || undefined,
      lines: [
        {
          menu_item_id: orderForm.menu_item_id,
          quantity: Number(orderForm.quantity) || 1,
        },
      ],
    });
    setOrderForm({ table_id: "", menu_item_id: "", quantity: "1" });
    void reload();
  };

  const orderColumns: Column<RestaurantOrder>[] = [
    {
      key: "number",
      header: "Order",
      cell: (r) => <span className="font-medium">{r.order_number}</span>,
    },
    {
      key: "table",
      header: "Table",
      cell: (r) => r.table_code || "Takeaway",
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant="secondary">{r.status}</Badge>,
    },
    {
      key: "waiter",
      header: "Waiter",
      cell: (r) => r.waiter_name || "—",
    },
    {
      key: "subtotal",
      header: "Subtotal",
      cell: (r) => formatCurrency(r.subtotal),
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        canFloor && r.status !== "paid" && r.status !== "cancelled" ? (
          <div className="flex gap-1 justify-end">
            {r.status === "open" ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => restaurantApi.updateOrderStatus(r.id, "sent").then(reload)}
              >
                Send
              </Button>
            ) : null}
            {r.status === "sent" || r.status === "ready" ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => restaurantApi.updateOrderStatus(r.id, "served").then(reload)}
              >
                Serve
              </Button>
            ) : null}
            <Button
              size="sm"
              onClick={() => restaurantApi.updateOrderStatus(r.id, "paid").then(reload)}
            >
              Mark paid
            </Button>
          </div>
        ) : null,
    },
  ];

  const itemColumns: Column<MenuItem>[] = [
    { key: "name", header: "Item", cell: (r) => r.name },
    { key: "category", header: "Category", cell: (r) => r.category_name },
    { key: "price", header: "Price", cell: (r) => formatCurrency(r.unit_price) },
    {
      key: "avail",
      header: "Available",
      cell: (r) => (
        <Badge variant={r.is_available ? "success" : "secondary"}>
          {r.is_available ? "Yes" : "No"}
        </Badge>
      ),
    },
  ];

  const tableColumns: Column<DiningTable>[] = [
    { key: "code", header: "Code", cell: (r) => r.code },
    { key: "label", header: "Label", cell: (r) => r.label },
    { key: "capacity", header: "Seats", cell: (r) => r.capacity },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={r.status === "occupied" ? "warning" : "secondary"}>{r.status}</Badge>
      ),
    },
  ];

  return (
    <PageLayout
      title="Restaurant"
      description="Floor tables, menu, and open tickets. Checkout stays on Universal POS."
      breadcrumbs={["Home", "Restaurant"]}
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link to="/pos">Open POS</Link>
        </Button>
      }
    >
      <KpiGrid columns={4}>
        <KpiCard
          index={0}
          accent="primary"
          title="Open orders"
          value={String(summary?.orders_open ?? 0)}
          icon={<CookingPot className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={1}
          accent="warning"
          title="Tables occupied"
          value={`${summary?.tables_occupied ?? 0}/${summary?.tables ?? 0}`}
          icon={<Armchair className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={2}
          accent="info"
          title="Menu items"
          value={String(summary?.menu_items ?? 0)}
          icon={<UtensilsCrossed className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={3}
          accent="success"
          title="Orders today"
          value={String(summary?.orders_today ?? 0)}
          icon={<CookingPot className="h-5 w-5" />}
          loading={loading}
        />
      </KpiGrid>

      <div className="mb-4 flex gap-2">
        {(["orders", "menu", "tables"] as Tab[]).map((t) => (
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

      {tab === "orders" ? (
        <ContentSection title="Orders" description="Open floor tickets (pay via POS later)">
          {canFloor ? (
            <FormGrid className="mb-4">
              <FormField label="Table">
                <Select
                  value={orderForm.table_id || "__none"}
                  onValueChange={(v) =>
                    setOrderForm((f) => ({ ...f, table_id: v === "__none" ? "" : v }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Takeaway" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none">Takeaway</SelectItem>
                    {tables.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.label} ({t.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Item">
                <Select
                  value={orderForm.menu_item_id}
                  onValueChange={(v) => setOrderForm((f) => ({ ...f, menu_item_id: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select item" />
                  </SelectTrigger>
                  <SelectContent>
                    {items.map((i) => (
                      <SelectItem key={i.id} value={i.id}>
                        {i.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Qty">
                <Input
                  value={orderForm.quantity}
                  onChange={(e) => setOrderForm((f) => ({ ...f, quantity: e.target.value }))}
                />
              </FormField>
              <div className="flex items-end">
                <Button onClick={addOrder}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  New order
                </Button>
              </div>
            </FormGrid>
          ) : null}
          <DataTable
            columns={orderColumns}
            data={orders}
            loading={loading}
            emptyMessage="No orders yet."
          />
        </ContentSection>
      ) : null}

      {tab === "menu" ? (
        <ContentSection title="Menu" description="Categories and sellable items">
          {canManage ? (
            <>
              <FormGrid className="mb-4">
                <FormField label="New category">
                  <Input
                    value={catForm.name}
                    onChange={(e) => setCatForm({ name: e.target.value })}
                    placeholder="Drinks"
                  />
                </FormField>
                <div className="flex items-end">
                  <Button variant="outline" onClick={addCategory}>
                    Add category
                  </Button>
                </div>
              </FormGrid>
              <FormGrid className="mb-4">
                <FormField label="Item name">
                  <Input
                    value={itemForm.name}
                    onChange={(e) => setItemForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </FormField>
                <FormField label="Category">
                  <Select
                    value={itemForm.category_id}
                    onValueChange={(v) => setItemForm((f) => ({ ...f, category_id: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Category" />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.map((c) => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Price">
                  <Input
                    value={itemForm.unit_price}
                    onChange={(e) => setItemForm((f) => ({ ...f, unit_price: e.target.value }))}
                  />
                </FormField>
                <div className="flex items-end">
                  <Button onClick={addItem}>Add item</Button>
                </div>
              </FormGrid>
            </>
          ) : null}
          <DataTable
            columns={itemColumns}
            data={items}
            loading={loading}
            emptyMessage="No menu items yet."
          />
        </ContentSection>
      ) : null}

      {tab === "tables" ? (
        <ContentSection title="Floor tables" description="Dining room layout">
          {canManage ? (
            <FormGrid className="mb-4">
              <FormField label="Code">
                <Input
                  value={tableForm.code}
                  onChange={(e) => setTableForm((f) => ({ ...f, code: e.target.value }))}
                  placeholder="T1"
                />
              </FormField>
              <FormField label="Label">
                <Input
                  value={tableForm.label}
                  onChange={(e) => setTableForm((f) => ({ ...f, label: e.target.value }))}
                />
              </FormField>
              <FormField label="Capacity">
                <Input
                  value={tableForm.capacity}
                  onChange={(e) => setTableForm((f) => ({ ...f, capacity: e.target.value }))}
                />
              </FormField>
              <div className="flex items-end">
                <Button onClick={addTable}>Add table</Button>
              </div>
            </FormGrid>
          ) : null}
          <DataTable
            columns={tableColumns}
            data={tables}
            loading={loading}
            emptyMessage="No tables yet."
          />
        </ContentSection>
      ) : null}
    </PageLayout>
  );
}
