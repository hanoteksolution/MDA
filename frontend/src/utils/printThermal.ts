const FRAME_ID = "mda-thermal-print-frame";

export interface PrintThermalOptions {
  /** Roll width hint — content uses 100% of the printer printable area. */
  width: "58mm" | "80mm";
  css: string;
}

/**
 * Print thermal receipt via an isolated iframe document.
 * Avoids scaling the app UI and fits POS roll printers (72mm / 80mm).
 */
export function printThermalDocument(bodyHtml: string, options: PrintThermalOptions): Promise<void> {
  return new Promise((resolve) => {
    const existing = document.getElementById(FRAME_ID);
    if (existing) existing.remove();

    const pad = options.width === "58mm" ? "0.5mm 1mm" : "1mm 1.5mm";
    const baseFont = options.width === "58mm" ? "10px" : "11px";

    const frame = document.createElement("iframe");
    frame.id = FRAME_ID;
    frame.setAttribute("aria-hidden", "true");
    frame.style.cssText =
      "position:fixed;left:0;top:0;width:0;height:0;border:0;opacity:0;pointer-events:none;";
    document.body.appendChild(frame);

    const doc = frame.contentDocument;
    const win = frame.contentWindow;
    if (!doc || !win) {
      frame.remove();
      resolve();
      return;
    }

    const cleanup = () => {
      setTimeout(() => frame.remove(), 800);
      resolve();
    };

    doc.open();
    doc.write(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Receipt</title>
  <style>
    ${options.css}
    @page { margin: 0; size: auto; }
    * { box-sizing: border-box; }
    html, body {
      margin: 0 !important;
      padding: 0 !important;
      width: 100% !important;
      height: auto !important;
      min-height: 0 !important;
      background: #fff !important;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    body {
      padding: ${pad} !important;
      font-size: ${baseFont};
    }
    .mda-thermal {
      width: 100% !important;
      max-width: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      overflow: hidden;
    }
    .th-table { width: 100%; table-layout: fixed; border: none !important; }
    .th-table td, .th-table th { border: none !important; }
    .th-table thead th { border-bottom: 1px solid #000 !important; }
    .th-table .item-name { word-break: break-word; overflow-wrap: anywhere; }
    .th-meta .row,
    .th-totals .row,
    .th-merchant-row {
      gap: 2px;
      padding: 0;
    }
  </style>
</head>
<body class="thermal-print thermal-${options.width.replace("mm", "")}">
${bodyHtml}
</body>
</html>`);
    doc.close();

    let printed = false;
    const runPrint = () => {
      if (printed) return;
      printed = true;
      try {
        win.focus();
        win.print();
      } catch {
        /* ignore */
      }
      cleanup();
    };

    const img = doc.querySelector<HTMLImageElement>(".th-barcode img");
    if (img && !img.complete) {
      img.onload = () => setTimeout(runPrint, 50);
      img.onerror = () => setTimeout(runPrint, 50);
      setTimeout(runPrint, 600);
    } else {
      setTimeout(runPrint, 120);
    }
  });
}
