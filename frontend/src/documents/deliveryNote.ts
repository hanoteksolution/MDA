import type { DeliveryNote } from "@/services/api/sales";
import { getDocumentBranding } from "./branding";
import type { DeliveryNotePayload, DocumentBranding, EnterpriseDocument } from "./types";

function formatDocDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function buildDeliveryNotePayload(
  note: DeliveryNote,
  branding: DocumentBranding
): DeliveryNotePayload {
  const deliverLines = [
    note.customer_address || "",
    note.customer_phone ? `Phone: ${note.customer_phone}` : "",
  ].filter(Boolean);

  const rows = (note.items ?? []).map((item, i) => ({
    index: i + 1,
    name: item.name,
    quantityOrdered: item.quantity_ordered,
    quantityDelivered: item.quantity_delivered,
    unit: item.unit || "Pcs",
  }));

  return {
    branding,
    deliveryNumber: note.delivery_number,
    deliverTo: {
      title: "Deliver To",
      name: note.customer_name,
      lines: deliverLines,
    },
    metaRows: [
      { label: "Order No", value: note.order_number },
      { label: "Delivery Date", value: formatDocDate(note.delivery_date) },
      { label: "Sales Person", value: note.sales_person },
      { label: "Vehicle No", value: note.vehicle_no || "—" },
    ],
    rows,
    companyPhone: note.company?.phone,
    companyEmail: note.company?.email,
    companyWebsite: note.company?.website,
  };
}

export function documentFromDeliveryNote(
  note: DeliveryNote,
  branding: DocumentBranding
): EnterpriseDocument {
  const payload = buildDeliveryNotePayload(note, branding);
  return {
    type: "delivery_note",
    branding,
    meta: {
      documentNumber: note.delivery_number,
      documentTitle: "Delivery Note",
      issueDate: formatDocDate(note.delivery_date),
      generatedBy: note.sales_person,
      branch: note.branch?.name,
      status: "sent",
    },
    deliveryNotePayload: payload,
    columns: [],
    rows: [],
    confidential: false,
  };
}

export async function buildDeliveryNoteDocument(note: DeliveryNote): Promise<EnterpriseDocument> {
  const branding = await getDocumentBranding({
    name: note.branch?.name,
    address: note.branch?.address,
    phone: note.company?.phone,
  });
  return documentFromDeliveryNote(note, branding);
}
