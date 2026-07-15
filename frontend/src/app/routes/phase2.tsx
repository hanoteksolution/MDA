import { useParams } from "react-router-dom";
import { ProductsPage, ProductFormPage } from "@/modules/products/pages/ProductsPage";
import { CategoriesPage } from "@/modules/products/pages/CategoriesPage";
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
  CategoriesPage,
  InventoryDashboardPage,
  StockPage,
  AdjustmentsPage,
  WarehousesPage,
};
