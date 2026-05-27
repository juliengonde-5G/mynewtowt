# Référence technique — mynewtowt V3.1

> Version : 3.1 | Date : 2026-05-27 | Statut : **ACTIF**

## 1. Stack technique

| Couche | Technologie | Version |
|--------|------------|---------|
| Backend | FastAPI + Uvicorn | 0.115.6 / 0.34.0 |
| Langage | Python | 3.12 |
| Base de données | PostgreSQL + asyncpg | 16 / 0.30.0 |
| ORM | SQLAlchemy async (`Mapped[]`) | 2.0.36 |
| Migrations | Alembic | 1.14.0 |
| Frontend | HTMX 2 + Alpine.js + Jinja2 | SSR pur |
| Icônes | Lucide (CDN unpkg) | dernière |
| Auth | itsdangerous (signed cookies) + bcrypt + TOTP MFA | — |
| PDF | WeasyPrint | 63.1 |
| Cartographie | MapLibre GL + MapTiler/Mapbox | — |
| IA (chatbot) | Anthropic SDK — claude-sonnet-4-6 | 0.49.0 |
| Reverse proxy | Caddy 2 | TLS automatique Let's Encrypt |
| Containers | Docker + docker-compose | — |
| Observabilité | OpenTelemetry + Prometheus + Sentry | — |

> **V3.1** : Stripe retiré — NEWTOWT facture exclusivement par virement bancaire.
> Nginx remplacé par Caddy (certificats TLS automatiques).

---

## 2. Structure des répertoires

```
mynewtowt/
├── app/
│   ├── __init__.py              # __version__ = "3.1.x"
│   ├── main.py                  # create_app() — middlewares + routers + handlers
│   ├── config.py                # pydantic-settings — .env source of truth
│   ├── database.py              # async engine + get_db() dependency
│   ├── auth.py                  # bcrypt + itsdangerous (staff + client)
│   ├── permissions.py           # RBAC matrix + require_permission() factory
│   ├── csrf.py                  # Double-submit cookie CSRF (towt_csrf)
│   ├── templating.py            # Jinja2 env, filtres money/date/flag, globals
│   ├── i18n/                    # 5 catalogues : fr, en, es, pt-br, vi
│   ├── middlewares/
│   │   ├── security_headers.py  # CSP stricte + HSTS + X-Frame-Options
│   │   ├── maintenance.py       # Toggle via /tmp/.maintenance
│   │   ├── force_password.py    # Redirection si must_change_password=True
│   │   └── __init__.py          # Re-export des 4 middlewares
│   ├── models/                  # 45+ entités SQLAlchemy 2 Mapped[]
│   ├── routers/                 # 25 routers FastAPI
│   ├── schemas/                 # Pydantic DTO (booking.py, leg.py)
│   ├── services/                # 25 services métier
│   ├── utils/                   # file_validation, timezones, pipedrive
│   ├── templates/
│   │   ├── base.html            # Squelette HTML (scripts, modal, toast)
│   │   ├── staff/               # ERP interne (layout + topbar dédiés)
│   │   ├── client/              # Plateforme client /me
│   │   ├── public/              # Landing + routes catalog
│   │   ├── portal/              # /p/{token} portail expéditeur
│   │   ├── pdf/                 # WeasyPrint : BL, PL, invoice, CO2, SOF
│   │   └── errors/              # 403, 404
│   └── static/
│       ├── css/tokens.css       # Design tokens W3C (charte Nouvelle Étoile)
│       ├── css/kairos.css       # Composants UI Kairos
│       └── js/                  # toast, modal, sidebar, clock, csrf-htmx, forms
├── migrations/                  # 19 révisions Alembic (0001 → 0019)
├── scripts/                     # deploy, seed, rollback, reset_password
├── tests/                       # pytest — 25 fichiers unit tests
├── caddy/Caddyfile              # Config Caddy production
├── docker-compose.yml           # 3 services : db, app, caddy
├── Dockerfile                   # Python 3.12 slim
├── requirements.txt             # Dépendances production
└── requirements-dev.txt         # Dépendances dev/test
```

---

## 3. Couche base de données

### 3.1 Connexion

```python
# database.py
engine = create_async_engine(
    settings.database_url,            # postgresql+asyncpg://...
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    pool_recycle=1800,
)
```

La dependency `get_db()` est le seul point d'entrée pour une session.
Elle commit automatiquement en sortie normale, rollback sur exception.

### 3.2 Règle critique

| Faire | Ne pas faire |
|-------|-------------|
| `await db.flush()` — matérialise INSERT/UPDATE | `await db.commit()` dans une route |
| `flush()` + `RedirectResponse(303)` après mutation | `commit()` directement |

`get_db()` gère le commit final. Appeler `commit()` dans une route
court-circuite la gestion transactionnelle de la dependency.

### 3.3 Modèles ORM — inventaire complet

| Modèle | Table | Description |
|--------|-------|-------------|
| `ActivityLog` | `activity_logs` | Audit trail append-only |
| `Booking` | `bookings` | Réservation espace cargo client |
| `BookingItem` | `booking_items` | Lignes de réservation |
| `BookingMessage` | `booking_messages` | Messagerie client ↔ équipe |
| `CargoDocument` | `cargo_documents` | PJ cargo (BL, reçu, etc.) |
| `CashboxClosure` | `cashbox_closures` | Clôtures caisse bord |
| `CashboxMovement` | `cashbox_movements` | Mouvements de caisse |
| `OnboardCashbox` | `onboard_cashboxes` | Caisses bord par devise |
| `ChatConversation` | `chat_conversations` | Sessions chatbot Kairos |
| `ChatMessage` | `chat_messages` | Messages + coût tokens |
| `Claim` | `claims` | Réclamations cargo |
| `ClaimTimelineEntry` | `claim_timeline_entries` | Historique statuts claim |
| `Client` | `clients` | Clients commerciaux |
| `ClientAccount` | `client_accounts` | Comptes espace client (B2B) |
| `ClientInvoice` | `client_invoices` | Factures clients |
| `AnemosCertificate` | `anemos_certificates` | Certificats CO₂ Anemos |
| `CrewAssignment` | `crew_assignments` | Affectations marin → leg |
| `CrewCertification` | `crew_certifications` | Certifications marins |
| `CrewLeave` | `crew_leaves` | Congés équipage |
| `CrewMember` | `crew_members` | Marins |
| `CrewTicket` | `crew_tickets` | Tickets créés par l'équipage |
| `DockerShift` | `docker_shifts` | Vacations docker |
| `EscaleOperation` | `escale_operations` | Opérations portuaires |
| `EtaShift` | `eta_shifts` | Décalages ETA officiels |
| `FeatureFlag` | `feature_flags` | Flags fonctionnels DB-backed |
| `InsuranceContract` | `insurance_contracts` | Contrats d'assurance |
| `KnownDevice` | `known_devices` | Appareils MFA approuvés |
| `Leg` | `legs` | Segment de voyage (POL→POD) |
| `LegFinance` | `leg_finances` | Données financières par leg |
| `LegKPI` | `leg_kpis` | KPI calculés par leg |
| `MfaRecoveryCode` | `mfa_recovery_codes` | Codes de secours MFA |
| `MRVEvent` | `mrv_events` | Événements fuel MRV |
| `MRVParameter` | `mrv_parameters` | Paramètres émissions |
| `NoonReport` | `noon_reports` | Rapports journaliers navigation |
| `Notification` | `notifications` | Notifications in-app |
| `OnboardChecklist` | `onboard_checklists` | Checklists bord |
| `OnboardMessage` | `onboard_messages` | Messagerie commandant ↔ ops |
| `OnboardMessageMention` | `onboard_message_mentions` | Mentions dans messages |
| `OpexParameter` | `opex_parameters` | Coûts d'exploitation journaliers |
| `Order` | `orders` | Ordres transport commercial |
| `OrderAssignment` | `order_assignments` | Affectation ordre → leg |
| `PackingList` | `packing_lists` | Listes de colisage |
| `PackingListAudit` | `packing_list_audits` | Audit trail packing list |
| `PackingListBatch` | `packing_list_batches` | Lots de colisage |
| `PackingListDocument` | `packing_list_documents` | Documents attachés aux PL |
| `PlanningShare` | `planning_shares` | Tokens de partage planning |
| `Port` | `ports` | Ports du monde (UN LOCODE) |
| `PortalAccessLog` | `portal_access_logs` | Accès portail expéditeur (SHA-256) |
| `PortalMessage` | `portal_messages` | Messagerie portail /p/{token} |
| `PortConfig` | `port_configs` | Configuration frais portuaires |
| `RateGrid` | `rate_grids` | Grilles tarifaires |
| `RateGridLine` | `rate_grid_lines` | Lignes de grille |
| `RateOffer` | `rate_offers` | Offres commerciales |
| `RateLimitAttempt` | `rate_limit_attempts` | Tentatives (anti-brute force) |
| `SofEvent` | `sof_events` | Événements SOF (Statement of Facts) |
| `StowageItem` | `stowage_items` | Unités de chargement |
| `StowagePlan` | `stowage_plans` | Plans de chargement par leg |
| `Ticket` | `tickets` | Tickets escale (kanban) |
| `TicketComment` | `ticket_comments` | Commentaires tickets |
| `User` | `users` | Staff NEWTOWT |
| `Vessel` | `vessels` | Navires |
| `VesselPosition` | `vessel_positions` | Positions AIS |
| `VisitorLog` | `visitor_logs` | Journal visites bord |
| `WatchLog` | `watch_logs` | Journal quarts navigation |

### 3.4 Migrations Alembic

| Révision | Description |
|----------|-------------|
| `20260518_0001` | Baseline — schéma complet initial |
| `20260518_0002` | Planning shares tokens |
| `20260518_0003` | Ports source |
| `20260518_0004` | Tickets escale |
| `20260518_0005` | Big drop — nettoyage tables orphelines |
| `20260518_0006` | Ports is_active flag |
| `20260519_0001` | Leg transit params |
| `20260519_0002` | Phase 2 ERP — modules enrichis |
| `20260519_0003` | Notifications in-app |
| `20260519_0004` | Leg port stay |
| `20260519_0005` | Drop Stripe — retrait paiement en ligne |
| `20260519_0006` | Doc signatures |
| `20260519_0007` | User assigned_vessel |
| `20260519_0008` | Port config contacts |
| `20260519_0009` | MFA recovery codes |
| `20260519_0010` | WebAuthn credentials |
| `20260519_0011` | Known devices |
| `20260519_0012` | Anemos rebrand (CO₂ certificats) |
| `20260519_0013` | Booking status timestamps |
| `20260519_0014` | Leg distance |
| `20260519_0015` | Notification client target |
| `20260519_0016` | Doc booking link |
| `20260519_0017` | Booking messages |
| `20260526_0018` | Voyage closure fields |
| `20260526_0019` | Drop WebAuthn — retrait passkey |

**Révision HEAD** : `20260526_0019`

---

## 4. Sécurité

### 4.1 Chaîne de middlewares (ordre d'exécution)

```
Request → CORS → SecurityHeaders → Maintenance → CSRF → ForcePasswordChange → ForceMfaForAdmin → Router
```

### 4.2 Authentification

Deux contextes indépendants, un cookie signé chacun :

| Contexte | Cookie | Table | TTL |
|----------|--------|-------|-----|
| Staff | `towt_session` | `users` | 8h bureau / 14j marins |
| Client | `towt_client_session` | `client_accounts` | 30j |
| MFA pending staff | `towt_staff_mfa_pending` | — | 5 min |
| MFA pending client | `towt_client_mfa_pending` | — | 5 min |

Sérialisation : `itsdangerous.URLSafeTimedSerializer` avec sel par contexte.
Hash password : `passlib[bcrypt]`.
TOTP MFA : `pyotp` — URI RFC 6238.
Codes de secours MFA : stockés hashés en base.

### 4.3 RBAC — matrice résumée

**8 rôles** : `administrateur`, `operation`, `armement`, `technique`,
`data_analyst`, `marins`, `commercial`, `manager_maritime`

**16 modules** : `planning`, `commercial`, `escale`, `cargo`, `finance`,
`kpi`, `captain`, `crew`, `claims`, `mrv`, `rh`, `booking`, `tickets`,
`analytics`, `chat`, `admin`

**3 niveaux** : C (Consult) < M (Modify) < S (Suppress)

Usage :
```python
@router.post("/legs/{id}/edit")
async def edit_leg(user = Depends(require_permission("planning", "M"))):
    ...
```

### 4.4 CSRF

Double-submit cookie `towt_csrf`. Middleware `CSRFMiddleware` vérifie
l'en-tête sur toute requête non-GET. `csrf-htmx.js` injecte automatiquement
l'en-tête HTMX.

### 4.5 CSP

```
default-src 'self'
script-src 'self' https://unpkg.com
style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com
font-src 'self' https://fonts.gstatic.com
img-src 'self' data: blob: [OSM, Mapbox, MapTiler]
connect-src 'self' [Mapbox, MapTiler, OSM Nominatim]
frame-ancestors 'self'
object-src 'none'
```

Pas de scripts inline. Pas de CDN externe non-listé.

### 4.6 Audit trail

`services.activity.record()` — à appeler sur toute action write.
Table `activity_logs` append-only (pas de UPDATE ni DELETE).
PII scrubbing : emails masqués en `j***@domain.tld`.
Token portail : jamais en clair — SHA-256 uniquement dans `portal_access_logs`.

---

## 5. Routers — cartographie complète

| Router | Préfixe | Module RBAC | Audience |
|--------|---------|-------------|----------|
| `public_router` | `/`, `/routes`, `/about`, `/fleet` | — | Public |
| `api_v1_router` | `/api/v1` | — | API publique |
| `staff_auth_router` | `/login`, `/logout` | — | Staff |
| `staff_dashboard_router` | `/dashboard` | — | Staff |
| `staff_booking_router` | `/bookings` (staff) | `booking/C` | Staff |
| `planning_router` | `/planning` | `planning` | Staff |
| `cargo_router` | `/cargo` | `cargo` | Staff |
| `commercial_router` | `/commercial` | `commercial` | Staff |
| `cargo_packing_router` | `/cargo/packing` | `cargo` | Staff |
| `crew_router` | `/crew` | `crew` | Staff |
| `escale_router` | `/escale` | `escale` | Staff |
| `captain_router` | `/captain`, `/onboard` | `captain` | Staff |
| `stowage_router` | `/stowage` | `cargo` | Staff |
| `claims_router` | `/claims` | `claims` | Staff |
| `mrv_router` | `/mrv` | `mrv` | Staff |
| `kpi_router` | `/kpi` | `kpi` | Staff |
| `finance_router` | `/finance` | `finance` | Staff |
| `admin_router` | `/admin` | `admin` | Staff |
| `notifications_router` | `/notifications` | — | Staff |
| `tickets_router` | `/tickets` | `tickets` | Staff |
| `cashbox_router` | `/cashbox` | `captain` | Staff |
| `modules_router` | `/rh` + stubs | `rh` | Staff |
| `chat_router` | `/chat` | `chat` | Staff |
| `cargo_portal_router` | `/p/{token}` | — (token) | Portail |
| `tracking_router` | `/api/tracking/upload` | — (X-API-Token) | Externe |
| `client_auth_router` | `/me/login`, `/me/logout` | — | Client |
| `client_dashboard_router` | `/me` | — | Client |
| `booking_router` | `/booking` | — | Client |
| `erp_scaffold_router` | `/erp` | — | Debug |

---

## 6. Services métier — inventaire

| Service | Fichier | Rôle |
|---------|---------|------|
| `activity` | `services/activity.py` | Audit trail append-only |
| `anemos` | `services/anemos.py` | Certificats CO₂ Anemos |
| `booking` | `services/booking.py` | Création/modification réservations |
| `booking_lifecycle` | `services/booking_lifecycle.py` | Machine à états booking |
| `capacity` | `services/capacity.py` | Vérification capacité leg (SELECT FOR UPDATE) |
| `cashbox` | `services/cashbox.py` | Gestion caisse bord |
| `chatbot` | `services/chatbot.py` | Kairos AI — Claude Sonnet 4.6 |
| `co2` | `services/co2.py` | Calcul émissions CO₂ |
| `commercial` | `services/commercial.py` | Grilles, offres, ordres |
| `device_detection` | `services/device_detection.py` | Détection appareil MFA connu |
| `documents` | `services/documents.py` | Gestion pièces jointes |
| `email` | `services/email.py` | Envoi emails SMTP (async) |
| `feature_flags` | `services/feature_flags.py` | Feature flags DB-backed |
| `invoicing` | `services/invoicing.py` | Génération factures clients |
| `kpi` | `services/kpi.py` | Calcul KPI auto par leg |
| `messaging` | `services/messaging.py` | Messagerie interne unifiée |
| `mfa` | `services/mfa.py` | TOTP setup/verify/recovery |
| `mrv_export` | `services/mrv_export.py` | Export CSV DNV pour MRV |
| `notifications` | `services/notifications.py` | Notifications in-app |
| `packing_list` | `services/packing_list.py` | Gestion listes de colisage |
| `pdf_generator` | `services/pdf_generator.py` | WeasyPrint PDF |
| `planning` | `services/planning.py` | Gantt, legs, dates, cascade |
| `ports` | `services/ports.py` | Recherche/gestion ports UN LOCODE |
| `pricing` | `services/pricing.py` | Calcul tarifs selon grilles |
| `rate_limit` | `services/rate_limit.py` | Anti-brute force (login) |
| `safe_files` | `services/safe_files.py` | Upload sécurisé (MIME + taille) |
| `security_alerts` | `services/security_alerts.py` | Alertes sécurité (rate-limit dépassé) |
| `signature` | `services/signature.py` | Signatures documents PDF |
| `stowage` | `services/stowage.py` | Algorithme glouton chargement 18 zones |
| `tickets` | `services/tickets.py` | Kanban tickets escale |
| `vessel_position` | `services/vessel_position.py` | Positions AIS |
| `weather` | `services/weather.py` | Données météo Windy |

---

## 7. Patterns de développement

### 7.1 Route avec mutation

```python
@router.post("/legs/{id}/edit")
async def edit_leg(
    id: int,
    form: FormData = Depends(),
    db: AsyncSession = Depends(get_db),
    user = Depends(require_permission("planning", "M")),
):
    # 1. Valider
    leg = await db.get(Leg, id)
    if not leg:
        raise HTTPException(404)
    # 2. Modifier
    leg.etd = form.etd
    # 3. Flush (jamais commit)
    await db.flush()
    # 4. Audit
    await activity.record(db, action="edit_leg", entity_id=id, user_id=user.id)
    # 5. Redirect 303
    if request.headers.get("hx-request"):
        return Response(headers={"HX-Redirect": f"/planning/legs/{id}"})
    return RedirectResponse(f"/planning/legs/{id}", 303)
```

### 7.2 HTMX détection

```python
is_htmx = request.headers.get("hx-request") == "1"
if is_htmx:
    return templates.TemplateResponse("staff/planning/_leg_row.html", ctx)
return templates.TemplateResponse("staff/planning/index.html", ctx)
```

### 7.3 Composants Kairos disponibles

`.card`, `.btn`, `.pill`, `.badge`, `.alert`, `.kpi-card`, `.stat-card`,
`.vessel-tabs`, `.year-selector`, `.leg-chip`, `.leg-summary`,
`.vessel-status-badge`, `.bordee-grid`, `.dash-notif-card`, `.progress-bar`,
`.toast`, `.modal-card`, `.sidebar-clock`, `.sidebar-userbadge`,
`.port-badge`

---

## 8. Tests

```bash
# Lancer les tests
pytest -q

# Avec couverture
pytest --cov=app --cov-report=term-missing

# Un seul module
pytest tests/unit/test_planning_service.py -v
```

**25 fichiers de tests** couvrant :
auth, cookies, CSRF, booking workflow, client journey, CO₂, commercial,
config safety, delete leg, device detection, file validation, i18n,
MRV export, packing list, permissions, planning, ports, pricing,
signatures, stowage, tickets, timezones, admin users template.

---

## 9. Démarrage local

```bash
git clone git@github.com:juliengonde-5g/mynewtowt.git
cd mynewtowt
cp .env.example .env           # Éditer SECRET_KEY, DATABASE_URL
docker compose up -d
docker compose exec app alembic upgrade head
# Optionnel : données démo
docker compose exec app python scripts/seed_demo.py
open http://localhost:8000
```

Variables `.env` minimales requises :
- `SECRET_KEY` : chaîne aléatoire ≥ 32 caractères
- `DATABASE_URL` : `postgresql+asyncpg://towt:password@db:5432/towt`
- `APP_ENV` : `development`

---

## 10. Design system Kairos / Charte Nouvelle Étoile

Tokens définis dans `Versions TOWT/newtowt-design-tokens.json`
et exposés dans `app/static/css/tokens.css`.

| Variable | Code | Ratio | Usage |
|----------|------|-------|-------|
| `--teal` | `#0D5966` | 60 % | Couleur dominante (header, nav) |
| `--vert` | `#87BD29` | 20 % | Succès, actions positives |
| `--cuivre` | `#B47148` | 10 % | Signal transition, warning |
| `--sable` | `#EFE6D6` | 10 % | Fond éditorial, surfaces |

Polices : **Manrope** (UI/print), **DM Serif Display** (accents titres),
**JetBrains Mono** (codes `leg_code`, MMSI, IMO).

**Interdits** : Inter, Poppins, Segoe UI. Pas de scripts inline (CSP).
Pas de framework JS lourd.

---

## 11. Internationalisation

5 catalogues : `fr` (défaut), `en`, `es`, `pt-br`, `vi`.

Usage dans les templates :
```jinja2
{{ t("booking.status.confirmed", lang) }}
```

Usage dans le code Python :
```python
from app.i18n import get_translation
msg = get_translation("booking.created", lang="fr")
```
