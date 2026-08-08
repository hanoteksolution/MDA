import { useCallback, useEffect, useState } from "react";
import { Building2, DoorOpen, Plus, Wrench } from "lucide-react";
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
import { useWorkspaceTab } from "@/hooks/useWorkspaceTab";
import { useAuthStore } from "@/store/authStore";
import {
  propertyApi,
  type MaintenanceTicket,
  type PropertyAsset,
  type PropertyBuilding,
  type PropertySummary,
  type PropertyUnit,
} from "@/services/api/property";
import { formatCurrency } from "@/utils/cn";

type Tab = "units" | "properties" | "maintenance";

const PROPERTY_TAB_PATHS: Record<string, Tab> = {
  units: "units",
  properties: "properties",
  maintenance: "maintenance",
};

export function PropertyPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("property_management.manage");
  const canMaint =
    hasPermission("property_management.maintenance") || canManage;

  const [tab, setTab] = useWorkspaceTab<Tab>("/property", PROPERTY_TAB_PATHS, "units");
  const [summary, setSummary] = useState<PropertySummary | null>(null);
  const [properties, setProperties] = useState<PropertyAsset[]>([]);
  const [buildings, setBuildings] = useState<PropertyBuilding[]>([]);
  const [units, setUnits] = useState<PropertyUnit[]>([]);
  const [tickets, setTickets] = useState<MaintenanceTicket[]>([]);
  const [loading, setLoading] = useState(true);

  const [propForm, setPropForm] = useState({ name: "", kind: "mixed", address: "" });
  const [bldgForm, setBldgForm] = useState({ name: "", property_id: "", floors: "1" });
  const [unitForm, setUnitForm] = useState({
    code: "",
    building_id: "",
    kind: "residential",
    rent_amount: "",
  });
  const [maintForm, setMaintForm] = useState({ unit_id: "", title: "", priority: "normal" });

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const [sumRes, propRes, bldgRes, unitRes, maintRes] = await Promise.all([
        propertyApi.summary(branchId),
        propertyApi.properties(1, branchId),
        propertyApi.buildings(1, branchId),
        propertyApi.units(1, branchId),
        propertyApi.maintenance(1, branchId),
      ]);
      setSummary(sumRes.data);
      setProperties(propRes.data.results);
      setBuildings(bldgRes.data.results);
      setUnits(unitRes.data.results);
      setTickets(maintRes.data.results);
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const addProperty = async () => {
    if (!branchId || !propForm.name) return;
    await propertyApi.createProperty({
      branch_id: branchId,
      name: propForm.name,
      kind: propForm.kind,
      address: propForm.address,
    });
    setPropForm({ name: "", kind: "mixed", address: "" });
    void reload();
  };

  const addBuilding = async () => {
    if (!branchId || !bldgForm.name || !bldgForm.property_id) return;
    await propertyApi.createBuilding({
      branch_id: branchId,
      property_id: bldgForm.property_id,
      name: bldgForm.name,
      floors: Number(bldgForm.floors) || 1,
    });
    setBldgForm({ name: "", property_id: "", floors: "1" });
    void reload();
  };

  const addUnit = async () => {
    if (!branchId || !unitForm.code || !unitForm.building_id) return;
    await propertyApi.createUnit({
      branch_id: branchId,
      building_id: unitForm.building_id,
      code: unitForm.code,
      kind: unitForm.kind,
      rent_amount: Number(unitForm.rent_amount) || 0,
    });
    setUnitForm({ code: "", building_id: "", kind: "residential", rent_amount: "" });
    void reload();
  };

  const addMaintenance = async () => {
    if (!branchId || !maintForm.unit_id || !maintForm.title) return;
    await propertyApi.createMaintenance({
      branch_id: branchId,
      unit_id: maintForm.unit_id,
      title: maintForm.title,
      priority: maintForm.priority,
    });
    setMaintForm({ unit_id: "", title: "", priority: "normal" });
    void reload();
  };

  const unitColumns: Column<PropertyUnit>[] = [
    { key: "code", header: "Unit", cell: (r) => <span className="font-medium">{r.code}</span> },
    { key: "building", header: "Building", cell: (r) => r.building_name },
    { key: "kind", header: "Kind", cell: (r) => r.kind },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant="secondary">{r.status}</Badge>,
    },
    { key: "rent", header: "Rent", cell: (r) => formatCurrency(r.rent_amount) },
  ];

  const propColumns: Column<PropertyAsset>[] = [
    { key: "name", header: "Property", cell: (r) => r.name },
    { key: "kind", header: "Kind", cell: (r) => r.kind },
    { key: "city", header: "City", cell: (r) => r.city || "—" },
    { key: "owner", header: "Owner", cell: (r) => r.owner_name || "—" },
  ];

  const maintColumns: Column<MaintenanceTicket>[] = [
    { key: "title", header: "Ticket", cell: (r) => r.title },
    { key: "unit", header: "Unit", cell: (r) => r.unit_code },
    {
      key: "priority",
      header: "Priority",
      cell: (r) => <Badge variant="secondary">{r.priority}</Badge>,
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant="secondary">{r.status}</Badge>,
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        canMaint && (r.status === "open" || r.status === "in_progress") ? (
          <div className="flex justify-end gap-1">
            {r.status === "open" ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => propertyApi.updateMaintenanceStatus(r.id, "in_progress").then(reload)}
              >
                Start
              </Button>
            ) : null}
            <Button
              size="sm"
              onClick={() => propertyApi.updateMaintenanceStatus(r.id, "done").then(reload)}
            >
              Done
            </Button>
          </div>
        ) : null,
    },
  ];

  return (
    <PageLayout
      title="Property"
      description="Shared property core — buildings, units, and maintenance. Leases come next."
      breadcrumbs={["Home", "Property"]}
    >
      <KpiGrid columns={4}>
        <KpiCard
          index={0}
          accent="primary"
          title="Properties"
          value={String(summary?.properties ?? 0)}
          icon={<Building2 className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={1}
          accent="success"
          title="Vacant units"
          value={`${summary?.units_vacant ?? 0}/${summary?.units ?? 0}`}
          icon={<DoorOpen className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={2}
          accent="info"
          title="Occupied"
          value={String(summary?.units_occupied ?? 0)}
          icon={<Building2 className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={3}
          accent="warning"
          title="Open maintenance"
          value={String(summary?.maintenance_open ?? 0)}
          icon={<Wrench className="h-5 w-5" />}
          loading={loading}
        />
      </KpiGrid>

      <div className="mb-4 flex gap-2">
        {(["units", "properties", "maintenance"] as Tab[]).map((t) => (
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

      {tab === "units" ? (
        <ContentSection title="Units" description="Rentable inventory across buildings">
          {canManage ? (
            <FormGrid className="mb-4">
              <FormField label="Code">
                <Input
                  value={unitForm.code}
                  onChange={(e) => setUnitForm((f) => ({ ...f, code: e.target.value }))}
                />
              </FormField>
              <FormField label="Building">
                <Select
                  value={unitForm.building_id}
                  onValueChange={(v) => setUnitForm((f) => ({ ...f, building_id: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select building" />
                  </SelectTrigger>
                  <SelectContent>
                    {buildings.map((b) => (
                      <SelectItem key={b.id} value={b.id}>
                        {b.property_name} · {b.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Kind">
                <Select
                  value={unitForm.kind}
                  onValueChange={(v) => setUnitForm((f) => ({ ...f, kind: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="residential">Residential</SelectItem>
                    <SelectItem value="office">Office</SelectItem>
                    <SelectItem value="retail">Retail</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Rent">
                <Input
                  value={unitForm.rent_amount}
                  onChange={(e) => setUnitForm((f) => ({ ...f, rent_amount: e.target.value }))}
                />
              </FormField>
              <div className="flex items-end">
                <Button onClick={addUnit}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Add unit
                </Button>
              </div>
            </FormGrid>
          ) : null}
          <DataTable columns={unitColumns} data={units} loading={loading} emptyMessage="No units." />
        </ContentSection>
      ) : null}

      {tab === "properties" ? (
        <ContentSection title="Properties & buildings" description="Portfolio hierarchy">
          {canManage ? (
            <>
              <FormGrid className="mb-4">
                <FormField label="Property name">
                  <Input
                    value={propForm.name}
                    onChange={(e) => setPropForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </FormField>
                <FormField label="Kind">
                  <Select
                    value={propForm.kind}
                    onValueChange={(v) => setPropForm((f) => ({ ...f, kind: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="residential">Residential</SelectItem>
                      <SelectItem value="commercial">Commercial</SelectItem>
                      <SelectItem value="mixed">Mixed</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Address">
                  <Input
                    value={propForm.address}
                    onChange={(e) => setPropForm((f) => ({ ...f, address: e.target.value }))}
                  />
                </FormField>
                <div className="flex items-end">
                  <Button onClick={addProperty}>
                    <Plus className="h-4 w-4 mr-1.5" />
                    Add property
                  </Button>
                </div>
              </FormGrid>
              <FormGrid className="mb-4">
                <FormField label="Building name">
                  <Input
                    value={bldgForm.name}
                    onChange={(e) => setBldgForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </FormField>
                <FormField label="Property">
                  <Select
                    value={bldgForm.property_id}
                    onValueChange={(v) => setBldgForm((f) => ({ ...f, property_id: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select property" />
                    </SelectTrigger>
                    <SelectContent>
                      {properties.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Floors">
                  <Input
                    value={bldgForm.floors}
                    onChange={(e) => setBldgForm((f) => ({ ...f, floors: e.target.value }))}
                  />
                </FormField>
                <div className="flex items-end">
                  <Button variant="outline" onClick={addBuilding}>
                    <Plus className="h-4 w-4 mr-1.5" />
                    Add building
                  </Button>
                </div>
              </FormGrid>
            </>
          ) : null}
          <DataTable
            columns={propColumns}
            data={properties}
            loading={loading}
            emptyMessage="No properties."
          />
        </ContentSection>
      ) : null}

      {tab === "maintenance" ? (
        <ContentSection title="Maintenance" description="Work orders against units">
          {canMaint ? (
            <FormGrid className="mb-4">
              <FormField label="Unit">
                <Select
                  value={maintForm.unit_id}
                  onValueChange={(v) => setMaintForm((f) => ({ ...f, unit_id: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select unit" />
                  </SelectTrigger>
                  <SelectContent>
                    {units.map((u) => (
                      <SelectItem key={u.id} value={u.id}>
                        {u.code} · {u.building_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Title">
                <Input
                  value={maintForm.title}
                  onChange={(e) => setMaintForm((f) => ({ ...f, title: e.target.value }))}
                />
              </FormField>
              <FormField label="Priority">
                <Select
                  value={maintForm.priority}
                  onValueChange={(v) => setMaintForm((f) => ({ ...f, priority: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>
              <div className="flex items-end">
                <Button onClick={addMaintenance}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  New ticket
                </Button>
              </div>
            </FormGrid>
          ) : null}
          <DataTable
            columns={maintColumns}
            data={tickets}
            loading={loading}
            emptyMessage="No maintenance tickets."
          />
        </ContentSection>
      ) : null}
    </PageLayout>
  );
}
