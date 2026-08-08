# MDA Gym Member (React Native)

Expo-based member app for gym tenants. Consumes the STEP 27 mobile API foundation and STEP 28 member portal endpoints.

## Features (v0.1 + PHASE 24)

- Tenant slug + username/password login (`X-Tenant-Slug` on API host)
- Session bootstrap (`GET /mobile/bootstrap/`) → `enabled_modules` + `mobile_nav`
- Home dashboard (membership, check-in status); nav buttons from server `mobile_nav.screens`
- Membership QR code for reception scan (`mem:{membership_number}`)
- Attendance history
- Assigned workouts
- Class bookings
- Soft-gate when gym module / member portal is unavailable

## Prerequisites

- Node 18+
- Expo CLI (`npx expo`)
- Backend running at `http://127.0.0.1:8000` (or configure `extra.apiBase` in `app.json`)

## Setup

```bash
cd mobile/gym-member
npm install
npx expo start
```

## Member account provisioning

1. Create a gym tenant (web ERP or onboarding).
2. Create a gym member record.
3. Create a user with role **Gym Member** (`gym_member`) on that tenant.
4. Link the user to the member (staff API or admin):

```python
from apps.gym.services.member_portal_service import MemberPortalService
MemberPortalService.link_user(member=member, user=user)
```

5. Sign in from the app with tenant slug, username, and password.

## API endpoints used

| Screen | Endpoint |
|--------|----------|
| Login | `POST /api/v1/auth/login/` |
| Bootstrap / nav | `GET /api/v1/mobile/bootstrap/` |
| Home | `GET /api/v1/mobile/gym/home/` |
| QR | `GET /api/v1/mobile/gym/qr/` |
| Attendance | `GET /api/v1/mobile/gym/attendance/` |
| Workouts | `GET /api/v1/mobile/gym/workouts/` |
| Classes | `GET /api/v1/mobile/gym/classes/` |

## Configuration

Set defaults in `app.json`:

```json
{
  "expo": {
    "extra": {
      "apiBase": "http://127.0.0.1:8000/api/v1",
      "tenantSlug": "powergym"
    }
  }
}
```

For Android emulator, use `http://10.0.2.2:8000/api/v1` instead of `127.0.0.1`.
