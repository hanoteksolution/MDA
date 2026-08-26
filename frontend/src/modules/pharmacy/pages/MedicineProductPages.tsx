import { useParams } from "react-router-dom";
import { ProductFormPage, ProductsPage } from "@/modules/products/pages/ProductsPage";

/** Pharmacy medicines list — same catalog API, pharmacy-specific chrome. */
export function MedicineProductsPage() {
  return <ProductsPage profile="pharmacy" />;
}

export function MedicineFormPage({ editId }: { editId?: string }) {
  return <ProductFormPage profile="pharmacy" editId={editId} />;
}

export function MedicineEditPage() {
  const { id } = useParams();
  return <MedicineFormPage editId={id} />;
}
