import { useParams } from "react-router-dom";
import { ProductsPage, ProductFormPage } from "@/modules/products/pages/ProductsPage";
import {
  InventoryDashboardPage,
  StockPage,
  AdjustmentsPage,
  WarehousesPage,
} from "@/modules/inventory/pages/InventoryPages";

export function ProductEditPage() {
  const { id } = useParams();
  return <ProductFormPage editId={id} />;
}

export {
  ProductsPage,
  ProductFormPage,
  InventoryDashboardPage,
  StockPage,
  AdjustmentsPage,
  WarehousesPage,
};
