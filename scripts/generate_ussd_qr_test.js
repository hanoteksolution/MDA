const path = require("path");
const QR = require(path.join(__dirname, "..", "frontend", "node_modules", "qrcode"));
const fs = require("fs");

const outDir = path.join(__dirname, "..", "backend", "media", "subscription_qr");
fs.mkdirSync(outDir, { recursive: true });

const amount = process.argv[2] || "25";
const ussd = `*789*608833*${amount}#`;
const dial = `tel:*789*608833*${amount}%23`;

async function main() {
  const pngPath = path.join(outDir, `test-dial-ussd-${amount}.png`);
  const htmlPath = path.join(outDir, "test-dial-ussd.html");
  await QR.toFile(pngPath, dial, {
    width: 512,
    margin: 2,
    errorCorrectionLevel: "M",
    color: { dark: "#0f172a", light: "#ffffff" },
  });
  const dataUrl = await QR.toDataURL(dial, {
    width: 360,
    margin: 2,
    errorCorrectionLevel: "M",
  });

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MDA USSD QR Test</title>
  <style>
    body {
      font-family: system-ui, sans-serif;
      max-width: 420px;
      margin: 2rem auto;
      padding: 1rem;
      text-align: center;
      background: #0f172a;
      color: #e2e8f0;
    }
    img {
      background: #fff;
      padding: 12px;
      border-radius: 12px;
      width: 280px;
      height: 280px;
    }
    code {
      display: block;
      margin: 0.75rem 0;
      padding: 0.75rem;
      background: #1e293b;
      border-radius: 8px;
      word-break: break-all;
    }
    .ok { color: #34d399; }
    .hint { opacity: 0.75; font-size: 14px; line-height: 1.45; }
  </style>
</head>
<body>
  <h1>Scan to test dial</h1>
  <p class="ok">Expected dialer: <strong>${ussd}</strong></p>
  <img src="${dataUrl}" alt="USSD dial QR" />
  <p>QR payload</p>
  <code>${dial}</code>
  <p>USSD</p>
  <code>${ussd}</code>
  <p class="hint">
    Keep this page open on your PC. Scan with your phone camera (or Waafi scanner).
    You should get a prompt to dial ${ussd}. Confirm only if you intend to pay.
  </p>
</body>
</html>`;

  fs.writeFileSync(htmlPath, html, "utf8");
  console.log(JSON.stringify({ pngPath, htmlPath, ussd, dial }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
