import type { jsPDF } from "jspdf";
import { isTauri } from "@/utils/platform";

function normalizeFilename(filename: string): string {
  return filename.endsWith(".pdf") ? filename : `${filename}.pdf`;
}

/** Save a jsPDF document in browser or Tauri desktop (native save dialog). */
export async function savePdfDocument(doc: jsPDF, filename: string): Promise<boolean> {
  const safeName = normalizeFilename(filename);
  const bytes = new Uint8Array(doc.output("arraybuffer"));

  if (isTauri()) {
    const { invoke } = await import("@tauri-apps/api/core");
    const savedPath = await invoke<string | null>("save_pdf_file", {
      filename: safeName,
      data: Array.from(bytes),
    });
    return savedPath != null;
  }

  const blob = new Blob([bytes], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = safeName;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  return true;
}
