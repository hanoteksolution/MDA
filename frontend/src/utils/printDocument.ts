const PRINT_ROOT_ID = "mda-print-root";
const PRINT_STYLE_ID = "mda-print-style";

/**
 * Print HTML content using an inline container (works in browser and Tauri desktop).
 * Pass a fragment: `<style>...</style><div>...</div>` — not a full HTML document.
 */
export function printHtmlDocument(
  html: string,
  options?: { pageCss?: string; width?: string }
) {
  const existing = document.getElementById(PRINT_ROOT_ID);
  if (existing) existing.remove();
  const existingStyle = document.getElementById(PRINT_STYLE_ID);
  if (existingStyle) existingStyle.remove();

  const container = document.createElement("div");
  container.id = PRINT_ROOT_ID;
  container.innerHTML = html;
  document.body.appendChild(container);

  const width = options?.width ?? "210mm";
  const pageCss = options?.pageCss ?? "";

  const style = document.createElement("style");
  style.id = PRINT_STYLE_ID;
  style.textContent = `
    @page { size: A4 portrait; margin: 0; }
    ${pageCss}
    @media print {
      html, body { margin: 0 !important; padding: 0 !important; background: #fff !important; }
      body * { visibility: hidden !important; }
      #${PRINT_ROOT_ID}, #${PRINT_ROOT_ID} * { visibility: visible !important; }
      #${PRINT_ROOT_ID} {
        position: absolute;
        left: 0;
        top: 0;
        width: ${width};
        background: #fff;
        color: #111;
      }
    }
    @media screen {
      #${PRINT_ROOT_ID} { display: none; }
    }
  `;
  document.head.appendChild(style);

  window.print();

  setTimeout(() => {
    container.remove();
    style.remove();
  }, 600);
}
