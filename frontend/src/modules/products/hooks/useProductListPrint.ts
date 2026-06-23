import { useCallback, useState } from "react";
import { productsApi } from "@/services/api/catalog";
import { buildProductListDocument, fetchAllProductsForReport } from "@/documents/productList";
import { downloadProductListPdf, printProductListDocument } from "@/documents/engine";

export function useProductListPrint(filters?: { search?: string; category?: string }) {
  const [printing, setPrinting] = useState(false);

  const loadProducts = useCallback(async () => {
    const params: Record<string, string | number | undefined> = {};
    if (filters?.search) params.search = filters.search;
    if (filters?.category) params.category = filters.category;
    return fetchAllProductsForReport(
      (p) => productsApi.list(p).then((res) => ({ data: res.data })),
      params
    );
  }, [filters?.search, filters?.category]);

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
