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

    const pad = options.width === "58mm" ? "2mm 2mm" : "3mm 3mm";
    const baseFont = options.width === "58mm" ? "11px" : "13px";

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
    @page { margin: 0; }
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
      padding: ${pad};
      font-size: ${baseFont};
    }
    .mda-thermal {
      width: 100% !important;
      max-width: 100% !important;
      margin: 0;
      padding: 0;
    }
    .th-table { width: 100%; table-layout: fixed; }
    .th-table .item-name { word-break: break-word; }
    .th-barcode img { width: 100%; max-width: 100%; height: auto; min-height: 36px; }
  </style>
</head>
<body class="thermal-print thermal-${options.width.replace("mm", "")}">
${bodyHtml}
</body>
</html>`);
    doc.close();

    const runPrint = () => {
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
