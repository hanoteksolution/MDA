# MDA ERP Desktop

Tauri 2 desktop shell wrapping the React frontend (`../frontend`).

The desktop app **starts the Django API automatically** on launch. Installed builds bundle a **standalone `mda-api.exe`** — **no Python required** on POS PCs.

## Prerequisites (build machine only)

1. **Node.js** 18+ and npm
2. **Python** 3.11+ (only to *build* the installer, not on target PCs)
3. **Rust** — [https://rustup.rs](https://rustup.rs)
4. **Visual Studio Build Tools** — C++ workload
5. **WebView2** — on target Windows 10/11 PCs

## Build portable installer (no Python on target PCs)

From the **repository root**:

```powershell
pip install -r backend/requirements/bundle.txt
make install-desktop
make build-desktop
```

This will:

1. Run PyInstaller → `backend/dist/mda-api-x86_64-pc-windows-msvc.exe`
2. Bundle it inside the Tauri installer
3. Produce MSI/NSIS under `desktop/src-tauri/target/release/bundle/`

Copy the installer to any Windows PC and install — **Python is not needed**.

## Development (on your dev machine)

Dev mode still uses system Python (faster iteration):

```powershell
pip install -r backend/requirements/desktop.txt
make dev-desktop
```

On first launch, complete the **setup wizard** to create your company profile and administrator account.

For dev demo data: `make seed-demo` (creates admin / admin12345 + sample catalog).

## Data storage

SQLite database and uploads live at:

`%APPDATA%\com.mda.erp\`

## How it works

```
App launch → bundled mda-api.exe (SQLite in AppData) → UI at 127.0.0.1:8000
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `make build-desktop` fails on PyInstaller | Run `pip install -r backend/requirements/bundle.txt` |
| API timeout on first launch | First start runs migrations — wait up to 2 minutes |
| Port 8000 in use | Close other Django instances |
| Dev mode needs Python | Expected — only *installed* builds are Python-free |
