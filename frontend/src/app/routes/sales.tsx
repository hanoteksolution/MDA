import { useParams } from "react-router-dom";
import { InvoiceFormPage, QuotationFormPage } from "@/modules/sales/pages/SaleFormPage";

export function InvoiceEditPage() {
  const { id } = useParams();
  return <InvoiceFormPage editId={id} />;
}

export function QuotationEditPage() {
  const { id } = useParams();
  return <QuotationFormPage editId={id} />;
}

export { InvoiceFormPage, QuotationFormPage };
