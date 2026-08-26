import { useCallback, useState } from "react";
import { productsApi } from "@/services/api/catalog";
import { buildProductListDocument, fetchAllProductsForReport } from "@/documents/productList";
import { downloadProductListPdf, printProductListDocument } from "@/documents/engine";

export function useProductListPrint(filters?: {
  search?: string;
  category?: string;
  module_code?: string;
}) {
  const [printing, setPrinting] = useState(false);

  const loadProducts = useCallback(async () => {
    const params: Record<string, string | number | undefined> = {};
    if (filters?.search) params.search = filters.search;
    if (filters?.category) params.category = filters.category;
    if (filters?.module_code) params.module_code = filters.module_code;
    return fetchAllProductsForReport(
      (p) => productsApi.list(p).then((res) => ({ data: res.data })),
      params
    );
  }, [filters?.search, filters?.category, filters?.module_code]);

  const printProductList = useCallback(async () => {
    setPrinting(true);
    try {
      const products = await loadProducts();
      const doc = await buildProductListDocument(products);
      await printProductListDocument(doc);
    } finally {
      setPrinting(false);
    }
  }, [loadProducts]);

  const downloadProductList = useCallback(async () => {
    setPrinting(true);
    try {
      const products = await loadProducts();
      const doc = await buildProductListDocument(products);
      await downloadProductListPdf(doc, "product-list.pdf");
    } finally {
      setPrinting(false);
    }
  }, [loadProducts]);

  return { printing, printProductList, downloadProductList };
}
