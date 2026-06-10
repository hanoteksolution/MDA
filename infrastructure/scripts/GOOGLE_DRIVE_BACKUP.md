# Google Drive backup

Back up your MDA ERP **database** and **uploaded media** (product images, etc.) to Google Drive.

## 1. Install Google Drive for Desktop

1. Download [Google Drive for desktop](https://www.google.com/drive/download/).
2. Sign in and let sync finish.
3. Note your synced folder path. On Windows it is often one of:
   - `C:\Users\<you>\Google Drive`
   - `G:\My Drive`
   - `C:\Users\<you>\My Drive`

Create a folder inside it for backups, for example:

```
Google Drive\MDA-Backups
```

## 2. Configure the project

Edit `backend/.env`:

```env
GOOGLE_DRIVE_BACKUP_DIR=C:\Users\NISA\Google Drive\MDA-Backups
BACKUP_RETENTION_DAYS=30
```

Use your real Windows path. Forward slashes also work:

```env
GOOGLE_DRIVE_BACKUP_DIR=C:/Users/NISA/Google Drive/MDA-Backups
```

Optional local staging folder (defaults to `backups/` in the project root):

```env
BACKUP_LOCAL_DIR=
```

## 3. Run a backup

```bash
make backup
```

This will:

1. Export the database (SQLite in dev, PostgreSQL dump in production)
2. Include all files under `backend/media/`
3. Save a timestamped `.zip` to `backups/`
4. Copy the same file to your Google Drive folder (Google sync uploads it to the cloud)
5. Delete backups older than 30 days (local + Drive folder)

## 4. Restore

List available backups:

```bash
make restore-list
```

Restore the latest backup (stops recommended — quit `make dev` first):

```bash
make restore
```

Restore a specific file:

```bash
python infrastructure/scripts/restore.py "C:\Users\NISA\Google Drive\MDA-Backups\mda_erp_backup_20260610_120000.zip" --yes
```

## 5. Schedule daily backups (Windows)

1. Open **Task Scheduler** → **Create Basic Task**.
2. Trigger: Daily (e.g. 11:00 PM).
3. Action: **Start a program**
   - Program: `C:\Users\NISA\AppData\Local\Programs\Python\Python312\python.exe`
   - Arguments: `infrastructure\scripts\backup.py`
   - Start in: `C:\Users\NISA\Desktop\MDA`
4. Finish. Ensure Google Drive for Desktop is running so uploads sync.

## What is backed up

| Included | Not included |
|----------|----------------|
| Database (sales, inventory, users, etc.) | `node_modules/`, build caches |
| `backend/media/` uploads | Source code (use Git for that) |
| | `.env` secrets |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `GOOGLE_DRIVE_BACKUP_DIR does not exist` | Fix the path in `.env` or create the folder |
| Backup works but nothing in cloud | Open Google Drive app; check sync status |
| `pg_dump not found` | Install PostgreSQL client tools, or use SQLite in dev |
| Restore fails on SQLite | Stop Django (`make dev`) so the DB file is not locked |
