# Deploy MDA ERP on Hostinger VPS (88.222.220.238)



Step-by-step guide from a fresh Ubuntu VPS to a running cloud API with PostgreSQL.



---



## Before you start



You need:



| Item | Example |

|------|---------|

| VPS IP | `88.222.220.238` |

| SSH user | `root` or `ubuntu` (from Hostinger panel) |

| SSH key or password | From Hostinger → VPS → SSH access |

| Your project | Git repo URL, or upload ZIP via SFTP |



Generate a strong secret (run on your PC):



```bash

python -c "import secrets; print(secrets.token_urlsafe(48))"

```



Save that value — you will use it as `SECRET_KEY`.



---



## Step 1 — Log in to the VPS



From **PowerShell** or **Terminal** on your PC:



```bash

ssh root@88.222.220.238

```



Replace `root` with your Hostinger SSH username if different.



If this is your first login, accept the host key when prompted.



---



## Step 2 — Update the server



```bash

sudo apt update && sudo apt upgrade -y

```



---



## Step 3 — Install Docker



```bash

sudo apt install -y docker.io docker-compose-plugin git curl

sudo systemctl enable docker

sudo systemctl start docker

```



Add your user to the docker group (skip if you are `root`):



```bash

sudo usermod -aG docker $USER

```



If you added yourself to the group, **log out and SSH back in** so Docker works without `sudo`.



Verify:



```bash

docker --version

docker compose version

```



---



## Step 4 — Upload the project



**Option A — Git (recommended)**



```bash

sudo mkdir -p /opt/mda

sudo chown $USER:$USER /opt/mda

git clone <YOUR_REPO_URL> /opt/mda

cd /opt/mda

```



**Option B — SFTP**



1. In Hostinger: VPS → File Manager or use FileZilla

2. Upload the whole `MDA` folder to `/opt/mda`

3. SSH in: `cd /opt/mda`



---



## Step 5 — Create cloud environment file



```bash

cd /opt/mda

cp backend/.env.cloud.example backend/.env.cloud

nano backend/.env.cloud

```



Set these values:



```env

SECRET_KEY=paste-your-long-random-secret-here

DEBUG=False

ALLOWED_HOSTS=88.222.220.238,localhost,127.0.0.1

DB_NAME=mda_erp

DB_USER=mda

DB_PASSWORD=choose-a-strong-db-password

DB_HOST=db

DB_PORT=5432

CORS_ALLOWED_ORIGINS=http://88.222.220.238:8010,http://localhost:5173,https://tauri.localhost,http://tauri.localhost

```



Save: `Ctrl+O`, Enter, `Ctrl+X`.



---



## Step 6 — Open firewall ports



```bash

sudo ufw allow 22

sudo ufw allow 8010/tcp

sudo ufw enable

```



Port `5432` stays **closed** to the internet. You reach the database through an SSH tunnel (Step 10).



---



## Step 7 — Build and start containers



```bash

cd /opt/mda/infrastructure/docker

docker compose up -d --build

```



Wait until both containers are running:



```bash

docker compose ps

```



You should see `api` and `db` with status `running`.



Check API logs if needed:



```bash

docker compose logs -f api

```



Press `Ctrl+C` to stop following logs.



---



## Step 8 — Initialize the database



Run these **once** on first deploy:



```bash

docker compose exec api python manage.py migrate --settings=config.settings.production

docker compose exec api python manage.py bootstrap_system --settings=config.settings.production

docker compose exec api python manage.py bootstrap_platform --settings=config.settings.production

```



---



## Step 9 — Verify the API



From the VPS:



```bash

curl http://127.0.0.1:8010/api/v1/health/

```



Expected: JSON with `"status": "ok"` (or similar success response).



From your PC browser:



```

http://88.222.220.238:8010/api/v1/health/

```



### First-time setup



Use the **desktop app** in cloud mode:



1. Install MDA ERP on your PC

2. **Settings → Connection**

3. API URL: `http://88.222.220.238:8010/api/v1`

4. Save and restart the app

5. Complete the setup wizard (creates your platform admin account)



---



## Step 10 — Access PostgreSQL (manage the database)



PostgreSQL is only exposed on the VPS localhost. Use an **SSH tunnel** from your PC.



**PowerShell / Terminal on your PC:**



```bash

ssh -L 5432:127.0.0.1:5432 root@88.222.220.238

```



Keep that window open. In **DBeaver** or **pgAdmin**:



| Field | Value |

|-------|-------|

| Host | `localhost` |

| Port | `5432` |

| Database | `mda_erp` |

| User | `mda` |

| Password | value from `DB_PASSWORD` in `.env.cloud` |



---



## Step 11 — Connect shop desktops to the cloud



On each shop PC:



1. Install `MDA ERP_0.1.0_x64-setup.exe`

2. **Settings → Connection**

3. API URL: `http://88.222.220.238:8010/api/v1`

4. Save and **restart** the app

5. Log in with the shop user account



For **offline-only** shops, leave the default local URL (`http://127.0.0.1:8000/api/v1`).



---



## Step 12 — Staff performance & manager evaluations



Shop managers open **Staff Performance** in the sidebar:



- View sales, revenue, logins per worker

- Click **Evaluate** to set a 1–5 star rating and manager notes

- Evaluations are saved per period (Today / Week / Month / Year)



---



## Updating after code changes



On the VPS:



```bash

cd /opt/mda

git pull

cd infrastructure/docker

docker compose up -d --build

docker compose exec api python manage.py migrate --settings=config.settings.production

docker compose exec api python manage.py bootstrap_system --settings=config.settings.production

```



---



## Troubleshooting



### API not reachable from browser



```bash

docker compose ps

docker compose logs api --tail 100

sudo ufw status

```



Ensure port `8010` is allowed and the `api` container is running.



### `ALLOWED_HOSTS` error



Edit `backend/.env.cloud` and add your IP or domain to `ALLOWED_HOSTS`, then:



```bash

docker compose up -d --force-recreate api

```



### Database connection failed



```bash

docker compose logs db --tail 50

```



Confirm `DB_HOST=db` in `.env.cloud` (not `localhost` inside Docker).



### Reset everything (destructive)



```bash

cd /opt/mda/infrastructure/docker

docker compose down -v

docker compose up -d --build

# Re-run migrate + bootstrap from Step 8

```



---



## Roles



| Role | Access |

|------|--------|

| **Platform admin** | All shops, subscriptions, remote supervision |

| **Shop super admin** | One shop, staff performance + evaluations |

| **Branch manager** | Staff performance for their branch |



## Monthly subscriptions



Platform → **All Shops** → view plan/status/expiry.



API: `PUT /api/v1/platform/tenants/{id}/subscription/`



```json

{ "status": "active", "last_paid_at": "2026-06-01", "expires_at": "2026-07-01" }

```



Default plans: Starter ($29), Business ($79), Enterprise ($149).

