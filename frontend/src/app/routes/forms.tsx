import { useParams } from "react-router-dom";
import { CustomerFormPage } from "@/modules/customers/pages/CustomersPage";
import { SupplierFormPage } from "@/modules/suppliers/pages/SuppliersPage";
import { PurchaseFormPage } from "@/modules/purchases/pages/PurchasesPage";
import { UserFormPage, RoleFormPage } from "@/modules/admin/pages/AdminFormsPage";
import { BranchFormPage } from "@/modules/settings/pages/BranchFormPage";

export function CustomerEditPage() {
  const { id } = useParams();
  return <CustomerFormPage editId={id} />;
}

export function SupplierEditPage() {
  const { id } = useParams();
  return <SupplierFormPage editId={id} />;
}

export function PurchaseEditPage() {
  const { id } = useParams();
  return <PurchaseFormPage editId={id} />;
}

export function UserEditPage() {
  const { id } = useParams();
  return <UserFormPage editId={id} />;
}

export function RoleEditPage() {
  const { id } = useParams();
  return <RoleFormPage editId={id} />;
}

export function BranchEditPage() {
  const { id } = useParams();
  return <BranchFormPage editId={id} />;
}

export {
  CustomerFormPage,
  SupplierFormPage,
  PurchaseFormPage,
  UserFormPage,
  RoleFormPage,
  BranchFormPage,
};
