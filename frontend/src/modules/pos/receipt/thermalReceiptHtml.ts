import type { PosReceipt } from "@/services/api/pos";
import {
  renderPremiumThermalReceipt,
  getThermalPageCss,
  type ThermalAssets,
} from "@/documents/renderers/thermal";
import type { ThermalWidth } from "./receiptFormat";

export type { ThermalAssets };

export function buildThermalReceiptHtml(
  receipt: PosReceipt,
  assets: ThermalAssets,
  width: ThermalWidth = "80mm"
): string {
  return renderPremiumThermalReceipt(receipt, assets, width);
}

export function getThermalPrintStyles(width: ThermalWidth): string {
  return getThermalPageCss(width);
}
