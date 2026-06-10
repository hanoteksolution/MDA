# MDA ERP Desktop

Tauri 2 desktop shell wrapping the React frontend (`../frontend`).

## Prerequisites (Windows)

1. **Node.js** 18+ and npm
2. **Rust** — [https://rustup.rs](https://rustup.rs)
   ```powershell
   winget install Rustlang.Rustup
   rustup default stable
   ```
3. **Visual Studio Build Tools** — C++ workload (required for Rust on Windows)
4. **WebView2** — pre-installed on Windows 10/11

## Quick start

From the **repository root**:

```bash
make install-desktop   # npm install in desktop/
make dev-desktop       # Tauri dev (starts Vite + desktop window)
```

Or from `desktop/`:

```bash
npm install
npm run dev
```

Ensure the Django API is running (`make run-backend`) for full functionality.

## Build installer

```bash
make build-desktop
```

Output: `desktop/src-tauri/target/release/bundle/`

- **NSIS installer**: `nsis/MDA ERP_0.1.0_x64-setup.exe`
- **MSI**: `msi/MDA ERP_0.1.0_x64_en-US.msi`

## Project layout

```
desktop/
├── package.json          # Tauri CLI scripts
├── app-icon.png          # Source icon for tauri icon
├── src-tauri/
│   ├── Cargo.toml        # Rust dependencies
│   ├── tauri.conf.json   # Window, bundle, frontend paths
│   ├── src/              # Rust entry + commands
│   ├── icons/            # Generated app icons
│   └── capabilities/     # Tauri 2 permissions
└── sync/                 # (Phase 9) Offline SQLite sync engine
```

## Architecture

```
React UI (frontend/) → Tauri WebView → Rust shell → OS (print, files, updates)
                              ↓
                    Django API (when online)
```

Offline sync (`sync/`) is planned for Phase 9. The desktop app currently runs the full web UI against the local API.
