import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { travelApi, type TravelRecord } from "@/services/api/travel";
import { cn } from "@/utils/cn";

export type Kind = "bookings" | "packages" | "travelers" | "visas" | "insurance" | "vehicles" | "drivers" | "transfers" | "itineraries" | "activities" | "quotations" | "documents" | "payments" | "refunds" | "expenses";
const settings = {
  bookings: { title: "Bookings", fields: ["travel_date", "return_date", "adults", "children", "total_amount", "paid_amount", "currency", "notes"], list: travelApi.bookings, get: travelApi.booking, create: travelApi.createBooking, update: travelApi.updateBooking },
  packages: { title: "Packages", fields: ["name", "code", "duration_days", "base_price", "description", "includes", "excludes"], list: travelApi.packages, get: travelApi.package, create: travelApi.createPackage, update: travelApi.updatePackage },
  travelers: { title: "Travelers", fields: ["full_name", "passport_number", "nationality", "date_of_birth", "phone", "email", "notes"], list: travelApi.travelers, get: travelApi.traveler, create: travelApi.createTraveler, update: travelApi.updateTraveler },
  visas: { title: "Visa applications", fields: ["traveler_id", "booking_id", "visa_type", "country", "fee_amount", "notes"], list: travelApi.visas, get: travelApi.visa, create: travelApi.createVisa, update: travelApi.updateVisa },
  insurance: { title: "Insurance policies", fields: ["booking_id", "traveler_id", "provider", "policy_number", "coverage_type", "start_date", "end_date", "premium_amount", "status", "notes"], list: travelApi.insurance, get: travelApi.insurancePolicy, create: travelApi.createInsurance, update: travelApi.updateInsurance },
  vehicles: { title: "Vehicles", fields: ["code", "make_model", "plate_number", "capacity", "status"], list: travelApi.vehicles, get: travelApi.vehicle, create: travelApi.createVehicle, update: travelApi.updateVehicle },
  drivers: { title: "Drivers", fields: ["full_name", "phone", "license_number", "status"], list: travelApi.drivers, get: travelApi.driver, create: travelApi.createDriver, update: travelApi.updateDriver },
  transfers: { title: "Transfers", fields: ["booking_id", "vehicle_id", "driver_id", "pickup_location", "dropoff_location", "pickup_at", "transfer_type", "amount", "status"], list: travelApi.transfers, get: travelApi.transfer, create: travelApi.createTransfer, update: travelApi.updateTransfer },
  itineraries: { title: "Itineraries", fields: ["package_id", "booking_id", "title", "day_number", "status"], list: travelApi.itineraries, get: travelApi.itinerary, create: travelApi.createItinerary, update: travelApi.updateItinerary },
  activities: { title: "Activities", fields: ["itinerary_id", "name", "location", "start_time", "end_time", "cost", "notes", "sort_order"], list: travelApi.activities, get: travelApi.activity, create: travelApi.createActivity, update: travelApi.updateActivity },
  quotations: { title: "Quotations", fields: ["branch_id", "customer_id", "package_id", "travel_date", "adults", "children", "subtotal", "tax_amount", "total_amount", "valid_until", "notes"], list: travelApi.quotations, get: travelApi.quotation, create: travelApi.createQuotation, update: travelApi.updateQuotation },
  documents: { title: "Travel documents", fields: ["traveler_id", "doc_type", "doc_number", "issued_country", "issued_at", "expires_at", "notes"], list: travelApi.documents, get: travelApi.document, create: travelApi.createDocument, update: travelApi.updateDocument },
  payments: { title: "Travel payments", fields: ["booking_id", "amount", "method", "paid_at", "reference", "status", "notes"], list: travelApi.payments, get: travelApi.payment, create: travelApi.createPayment, update: travelApi.updatePayment },
  refunds: { title: "Travel refunds", fields: ["booking_id", "payment_id", "amount", "reason", "refunded_at", "status", "notes"], list: travelApi.refunds, get: travelApi.refund, create: travelApi.createRefund, update: travelApi.updateRefund },
  expenses: { title: "Travel expenses", fields: ["branch_id", "booking_id", "category", "description", "amount", "expense_date", "status", "notes"], list: travelApi.expenses, get: travelApi.expense, create: travelApi.createExpense, update: travelApi.updateExpense },
};
const label = (row: TravelRecord) => String(row.booking_code || row.quote_number || row.policy_number || row.code || row.name || row.full_name || row.title || row.doc_number || row.visa_type || row.id);

export function List({ kind }: { kind: Kind }) {
  const [rows, setRows] = useState<TravelRecord[]>([]);
  const [search, setSearch] = useState("");
  const spec = settings[kind];
  const load = () => spec.list(1, search).then((r) => setRows(r.data.results));
  useEffect(() => { void load(); }, [search]);
  return <PageLayout title={spec.title} breadcrumbs={["Travel", spec.title]} actions={<Button asChild><Link to={`/travel/${kind}/new`}>New</Link></Button>}><ContentSection><Input value={search} placeholder="Search" onChange={(e) => setSearch(e.target.value)} /><div className="mt-4 space-y-2">{rows.map((row) => <Link key={row.id} className="block rounded border p-3 hover:bg-muted" to={`/travel/${kind}/${row.id}`}>{label(row)} <span className="text-muted-foreground">· {String(row.status || "")}</span></Link>)}</div></ContentSection></PageLayout>;
}
export function Form({ kind, edit }: { kind: Kind; edit?: boolean }) {
  const { id } = useParams(); const nav = useNavigate(); const spec = settings[kind]; const [form, setForm] = useState<Record<string, string>>({});
  useEffect(() => { if (edit && id) void spec.get(id).then((r) => setForm(Object.fromEntries(Object.entries(r.data).map(([k, v]) => [k, v == null ? "" : String(v)])))); }, [edit, id]);
  const save = async () => { const result = edit && id ? await spec.update(id, form) : await spec.create(form); nav(`/travel/${kind}/${result.data.id}`); };
  return (
    <PageLayout title={`${edit ? "Edit" : "New"} ${spec.title}`} breadcrumbs={["Travel", spec.title]}>
      <ContentSection title={`${edit ? "Edit" : "Create"} ${spec.title.toLowerCase()}`}>
        <div className="grid grid-cols-1 gap-x-6 gap-y-5 md:grid-cols-2 xl:grid-cols-3">
          {spec.fields.map((field) => (
            <label key={field} className={cn("space-y-2 text-sm", /notes|description|includes|excludes|reason/.test(field) && "md:col-span-2 xl:col-span-3")}>
              <span className="font-medium capitalize">{field.replace(/_/g, " ")}</span>
              <Input value={form[field] || ""} onChange={(e) => setForm({ ...form, [field]: e.target.value })} />
            </label>
          ))}
        </div>
        <div className="mt-6 flex gap-3">
          <Button onClick={() => void save()}>Save</Button>
          <Button type="button" variant="secondary" onClick={() => nav(`/travel/${kind}`)}>Cancel</Button>
        </div>
      </ContentSection>
    </PageLayout>
  );
}
export function Detail({ kind }: { kind: Kind }) {
  const { id } = useParams(); const nav = useNavigate(); const spec = settings[kind]; const [row, setRow] = useState<TravelRecord | null>(null);
  useEffect(() => { if (id) void spec.get(id).then((r) => setRow(r.data)); }, [id]);
  const setQuoteStatus = async (status: string) => { if (id) { await travelApi.setQuotationStatus(id, status); setRow((await spec.get(id)).data); } };
  const convertQuote = async () => { if (id) { const booking = await travelApi.convertQuotation(id); nav(`/travel/bookings/${booking.data.id}`); } };
  const postBooking = async () => { if (id) { await travelApi.postBookingAccounting(id); setRow((await spec.get(id)).data); } };
  const postTransaction = async () => { if (id) { if (kind === "payments") await travelApi.postPaymentAccounting(id); if (kind === "refunds") await travelApi.postRefundAccounting(id); setRow((await spec.get(id)).data); } };
  const previewBooking = async () => { if (id) { const result = await travelApi.bookingAccountingPreview(id); window.alert(JSON.stringify(result.data.lines, null, 2)); } };
  return <PageLayout title={row ? label(row) : "Loading"} breadcrumbs={["Travel", spec.title]} actions={row ? <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => nav(`/travel/${kind}/${row.id}/edit`)}>Edit</Button>{kind === "quotations" && <><Button onClick={() => void setQuoteStatus("sent")}>Send</Button><Button onClick={() => void setQuoteStatus("accepted")}>Accept</Button><Button variant="outline" onClick={() => void setQuoteStatus("rejected")}>Reject</Button><Button variant="outline" onClick={() => void setQuoteStatus("expired")}>Expire</Button><Button onClick={() => void convertQuote()}>Convert</Button></>}{kind === "bookings" && <><Button asChild variant="outline"><Link to="/travel/payments">Payments</Link></Button><Button asChild variant="outline"><Link to="/travel/refunds">Refunds</Link></Button><Button variant="outline" onClick={() => void previewBooking()}>Ledger preview</Button><Button onClick={() => void postBooking()}>Post to ledger</Button></>}{(kind === "payments" || kind === "refunds") && <Button onClick={() => void postTransaction()}>Post to ledger</Button>}</div> : undefined}><ContentSection>{row && <dl className="grid gap-3 md:grid-cols-2">{Object.entries(row).map(([key, value]) => <div key={key}><dt className="text-xs text-muted-foreground">{key.replace(/_/g, " ")}</dt><dd>{String(value ?? "—")}</dd></div>)}</dl>}</ContentSection></PageLayout>;
}
