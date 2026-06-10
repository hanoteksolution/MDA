import QRCode from "qrcode";
import JsBarcode from "jsbarcode";

export async function generateQrDataUrl(data: string, size = 160): Promise<string> {
  return QRCode.toDataURL(data, {
    width: size,
    margin: 1,
    color: { dark: "#111827", light: "#ffffff" },
    errorCorrectionLevel: "M",
  });
}

export function generateBarcodeDataUrl(value: string, width = 1.4, height = 48): string {
  const canvas = document.createElement("canvas");
  JsBarcode(canvas, value, {
    format: "CODE128",
    width,
    height,
    displayValue: false,
    margin: 4,
    background: "#ffffff",
    lineColor: "#111827",
  });
  return canvas.toDataURL("image/png");
}
