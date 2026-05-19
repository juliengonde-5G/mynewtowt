# CLAUDE.md — my_newtowt Project Guide

## What is this project?

**my_newtowt** is a maritime operations management platform for **NEWTOWT** (TransOceanic Wind Transport, post-restructuration), a French sailing cargo company pioneering decarbonised wind-powered shipping since 2011. It manages vessel planning, commercial orders, cargo logistics, port calls, onboard operations, crew scheduling, MRV emissions reporting, and financial tracking.

> v3.0.0 — Passenger activity has been removed following the corporate restructuring.

**Production URL**: http://51.178.59.174 (VPS OVH)
**Default login**: admin / towt2025
**Brand assets**: `Design/` (NEWTOWT logos PNG, design tokens W3C JSON)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12), async |
| Database | PostgreSQL 16 via SQLAlchemy async + asyncpg |
| Frontend | Jinja2 templates + HTMX (no JS framework) |
| Auth | Cookie sessions, bcrypt, itsdangerous |
| CSS | Single `app/static/css/app.css` design system (NEWTOWT charte) |
| Fonts | Manrope (UI/print), DM Serif Display (accent) |
| Branding | Teal #0D5966 · Vert #87BD29 · Cuivre #B47148 · Sable #EFE6D6 |
| Deployment | Docker on VPS OVH, behind nginx reverse proxy |

## Project Structure

```
mytowt/
├── app/
│   ├── main.py              # FastAPI app, router registration
│   ├── config.py             # Settings via pydantic-settings (.env)
│   ├── database.py           # Async engine, session factory, Base
│   ├── auth.py               # Password hashing, session tokens, get_current_user
│   ├── permissions.py        # Role-based matrix (9 roles × 10 modules)
│   ├── templating.py         # Jinja2 config + custom filters (|flag)
│   ├── i18n/                 # Translations (fr, en, es, pt-br, vi)
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── user.py           # User
│   │   ├── vessel.py         # Vessel (fleet: Anemos, Artemis, Atlantis, Atlas)
│   │   ├── port.py           # Port (UN/LOCODE, coordinates)
│   │   ├── leg.py            # Leg (voyage segment: ETD/ETA/ATD/ATA)
│   │   ├── order.py          # Order + OrderAssignment
│   │   ├── operation.py      # EscaleOperation + DockerShift
│   │   ├── packing_list.py   # PackingList + PackingListBatch + PackingListAudit
│   │   ├── onboard.py        # SofEvent, OnboardNotification, CargoDocument
│   │   ├── crew.py           # CrewMember + CrewAssignment
│   │   ├── finance.py        # PortConfig, OpexParameter, LegFinance
│   │   ├── kpi.py            # LegKPI
│   │   ├── claim.py          # Claim (réclamations cargo)
│   │   ├── mrv.py            # MRV emissions reporting
│   │   ├── commercial.py     # CommClient (Pipedrive sync)
│   │   ├── stowage.py        # StowagePlan, StowageItem
│   │   ├── planning_share.py # PlanningShareLink
│   │   ├── vessel_position.py # VesselPosition (tracking)
│   │   ├── activity_log.py   # ActivityLog (audit trail)
│   │   ├── activity.py       # Activity (user activity tracking)
│   │   ├── co2_variable.py   # CO2 emission variables
│   │   ├── emission_parameter.py # EmissionParameter (CO2 factors)
│   │   ├── notification.py   # Notification (system notifications)
│   │   ├── portal_message.py # PortalMessage (client portal messaging)
│   │   └── portal_access_log.py # PortalAccessLog (portal token access audit)
│   ├── routers/              # One router per module
│   │   ├── planning_router.py    # /planning
│   │   ├── planning_ext_router.py # /planning/share/{token} (public)
│   │   ├── commercial_router.py  # /commercial
│   │   ├── cargo_router.py       # /cargo + /p/{token} (client portal)
│   │   ├── escale_router.py      # /escale
│   │   ├── onboard_router.py     # /onboard
│   │   ├── crew_router.py        # /crew
│   │   ├── finance_router.py     # /finance
│   │   ├── kpi_router.py         # /kpi
│   │   ├── claim_router.py       # /claims (cargo claims)
│   │   ├── mrv_router.py         # /mrv (emissions)
│   │   ├── pricing_router.py     # /pricing (grilles tarifaires)
│   │   ├── stowage_router.py     # /stowage (plan d'arrimage)
│   │   ├── tracking_router.py    # /tracking (API vessel positions)
│   │   ├── admin_router.py       # /admin
│   │   ├── dashboard_router.py   # /
│   │   ├── auth_router.py        # /login, /logout
│   │   └── api_ports.py          # /api/ports (autocomplete)
│   ├── templates/            # Jinja2 templates per module
│   │   ├── base.html         # Layout with sidebar
│   │   └── {module}/         # Module templates
│   ├── static/
│   │   ├── css/app.css       # Full design system (NEWTOWT charte)
│   │   ├── img/              # NEWTOWT logos PNG + favicon SVG
│   │   └── BILL_OF_LADING_TEMPLATE.docx
│   └── utils/
│       ├── file_validation.py # File upload validation
│       ├── navigation.py     # Navigation helpers
│       ├── notifications.py  # Notification system
│       ├── pipedrive.py      # Pipedrive CRM integration
│       ├── portal_security.py # Portal token security (cargo)
│       ├── timezones.py      # Timezone utilities
│       └── activity.py       # Activity logging
├── Design/                  # NEWTOWT brand assets
│   ├── logo_NEWTOWT_web.png
│   ├── logo_NEWTOWT_web_dark.png
│   ├── logo_NEWTOWT_web_white.png
│   └── newtowt-design-tokens.json   # W3C draft design tokens (canonical)
├── scripts/
│   ├── backup_db.sh          # Database backup (pg_dump + rotation)
│   ├── import_crew.py        # Import 44 crew members
│   ├── import_tonnage.py     # Import vessel tonnage data
│   ├── purge_access_logs.py  # Purge old portal access logs
│   └── seed_demo_data.py     # Seed demo data
├── rapports/                 # Daily audit reports
├── CLAUDE.md                 # This file
├── README.md
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── presentation_mytowt.html  # Seminar slideshow (14 slides, HTML/CSS)
├── .env.example
└── .gitignore
```

## Critical Patterns

### Database
- Session via `get_db()` dependency — auto-commit on success, rollback on error
- **Use `await db.flush()`** inside routes, NEVER `await db.commit()` (handled by middleware)
- Schema init via `Base.metadata.create_all` at startup
- Migrations: raw SQL `ALTER TABLE` (no Alembic yet)

### Routing
- Write endpoints: validate → modify → `await db.flush()` → redirect
- HTMX detection: `request.headers.get("HX-Request")` → return `HX-Redirect` header
- Non-HTMX: standard `RedirectResponse(status_code=303)`

### Templates
- Extend `base.html`, use `{% block topbar_actions %}` and `{% block content %}`
- Inline `<style>` per template (no separate CSS per page)
- Custom filter `|flag` converts country code → emoji flag

### Permissions
- 8 roles: administrateur, operation, armement, technique, data_analyst, marins, commercial, manager_maritime
- 10 modules: planning, commercial, escale, finance, kpi, captain, crew, cargo, claims, mrv
- Levels: C (consult), M (modify), S (suppress)
- Route dependency: `Depends(require_permission("module", "C"))` — enforced on ALL routes (GET=C, POST=M, DELETE=S)
- Sidebar visibility: `has_any_access(user, 'module')` in base.html
- Admin access: roles administrateur + data_analyst can access /admin/settings

### Security
- **SQL injection prevention**: `admin_router.py` uses `ALLOWED_TABLES` whitelist + parameterized queries (`.bindparams()`) for all dynamic table references
- **Route-level permissions**: ALL endpoints in planning, commercial, escale, cargo, crew, finance, kpi routers enforce `require_permission()` — GET requires C, POST requires M, DELETE requires S
- **External routes** (`/p/{token}` — cargo client portal) are excluded from permission checks (public access via token)
- **CORS**: Configured in `main.py` — restrict `allow_origins` in production

### CSS Design System (NEWTOWT charte "Nouvelle Étoile")
- Font: **Manrope** for UI/print, **DM Serif Display** for accents (citations, exergues)
- Canonical CSS variables: `--newtowt-teal`, `--newtowt-vert`, `--newtowt-cuivre`, `--newtowt-sable`, `--newtowt-bleu-marine`, etc.
- Backward-compat aliases: `--towt-blue` → `--newtowt-teal`, `--towt-green` → `--newtowt-vert`, etc. (existing inline styles in templates still work, mapped to new palette)
- Color ratio: 60% teal · 20% vert · 10% cuivre · 10% neutres
- Utility classes in `app.css`: `.card`, `.card-title`, `.alert`, `.alert-success`, `.alert-error`, `.field-label`, `.field-value`, `.btn-outline`, `.leg-code`, `.account-grid`
- Prefer CSS classes over inline styles for consistency
- Source of truth: `Design/newtowt-design-tokens.json`

### Forms
- Standard HTML `<form method="POST">`
- Helpers `pf()` (parse float), `pi()` (parse int) in cargo_router for form values

### External (no-auth) routes
- `/p/{token}` — client cargo packing list portal

## Deployment

### Current (VPS OVH)
```bash
docker-compose up -d          # Start
docker restart towt-app-v2    # Restart after changes
```

### Database migrations
```bash
docker exec towt-app-v2 python3 -c "
import asyncio
from app.database import engine
from sqlalchemy import text
async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE x ADD COLUMN y TYPE'))
asyncio.run(migrate())
"
```

### Static files permissions
```bash
docker exec towt-app-v2 chmod -R 755 /app/app/static/
```

### Database backup
```bash
./scripts/backup_db.sh        # Manual backup
# Or via cron (daily at 2am):
# 0 2 * * * /path/to/mytowt/scripts/backup_db.sh >> /var/log/towt-backup.log 2>&1
```

## Maritime Glossary

| Term | Meaning |
|------|---------|
| Leg | Voyage segment (port A → port B) |
| leg_code | `{seq}{vessel_code}{dep_country}{arr_country}{year_digit}` e.g. `1AFRUS6` |
| ETD/ETA | Estimated Time of Departure/Arrival |
| ATD/ATA | Actual Time of Departure/Arrival |
| Escale | Port call (period vessel is in port) |
| SOF | Statement of Facts (port operations log) |
| BL/BOL | Bill of Lading (cargo document) |
| POL/POD | Port of Loading / Discharge |
| LOCODE | UN port code (e.g. FRFEC = Fécamp) |
| OPEX | Operating expenditure (daily vessel cost) |
| Docker shift | Stevedore work shift |
| Palette | Pallet: EPAL 120×80, USPAL 120×100 |

## Planned Enhancements (backlog)

1. Global activity logging system (journal d'activité admin)
2. Cargo: structured addresses (shipper/notify/consignee split into name/address/postal/city/country)
3. Cargo: description_of_goods field for Bill of Lading
4. Cargo: mandatory dimensions with helptexts
5. BL format: `TUAW_{voyage_id}_{bl_no}`, packages format, Number of OBL: 3
6. Arrival Notice generation from packing list
7. Packing List Excel template system (download/upload/auto-import)
8. Escale timeline split into 2 flows (operational + parallel activities)

## Do / Don't

**DO:**
- Run `docker restart towt-app-v2` after any Python file change
- Provide migration SQL when adding/modifying DB columns
- Use CSS utility classes (`.card`, `.alert`, `.field-label`, etc.) instead of inline styles
- Use parameterized queries (`.bindparams()`) for any dynamic SQL
- Add `require_permission("module", "C"/"M"/"S")` to every new endpoint
- Test on Docker before pushing

**DON'T:**
- Never call `await db.commit()` in routes — the session handles it
- Never modify `routers/__init__.py` — it must stay empty
- Never hardcode credentials in source — use .env
- Don't add heavy JS frameworks — the app uses HTMX
- Never use f-strings to interpolate table/column names in SQL — use `ALLOWED_TABLES` whitelist
- Don't use `Segoe UI`, `Inter` or `Poppins` (legacy) — always use `Manrope` with `system-ui` fallback for UI/PDF, `DM Serif Display` for accent serif
- Don't reintroduce a `passengers` module — passenger activity has been removed in v3.0.0 post-restructuration
