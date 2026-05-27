# Référentiel IA — mynewtowt V3.1
# AI Codebase Reference Document

> **Objectif** : Ce document est la source de vérité pour tout moteur d'IA
> (LLM, agent de code, système RAG) intervenant sur la base de code
> mynewtowt. Il permet :
> - A. L'analyse complète du code dans son intégralité
> - B. Le secours logiciel en cas de défaillance de code
> - C. Le retour à des versions stables en cas d'incident programmatique

> **Version** : 3.1 | **Date** : 2026-05-27 | **Révision HEAD Alembic** : `20260526_0019`

---

## SECTION 1 — IDENTITÉ DU PROJET

```yaml
project: mynewtowt
company: NEWTOWT (TransOceanic Wind Transport)
domain: Transport maritime décarboné à la voile
version: 3.1.0
entrypoint: app/main.py → create_app()
language: Python 3.12
framework: FastAPI 0.115.6
database: PostgreSQL 16 + asyncpg
orm: SQLAlchemy 2.0.36 async
frontend: HTMX 2 + Jinja2 SSR (pas de framework JS lourd)
repository: juliengonde-5g/mynewtowt
branch_main: main
branch_dev: claude/quirky-edison-91j85
```

---

## SECTION 2 — RÈGLES ABSOLUES DU CODE

Ces règles sont des invariants. Toute modification qui les violerait
introduira des bugs silencieux ou des failles de sécurité.

### 2.1 Règles base de données

```
RÈGLE DB-1: JAMAIS await db.commit() dans une route FastAPI.
            get_db() gère le commit automatique. Utiliser flush() uniquement.

RÈGLE DB-2: Toute INSERT/UPDATE doit être suivie de await db.flush()
            pour matérialiser avant une éventuelle lecture en aval.

RÈGLE DB-3: Pattern mutation dans une route :
            valider → modifier → await db.flush() → RedirectResponse(303)

RÈGLE DB-4: Jamais de f-string SQL sur des noms de table/colonne.
            Utiliser une whitelist + bindparams() pour les paramètres dynamiques.
```

### 2.2 Règles sécurité

```
RÈGLE SEC-1: require_permission("module", "C|M|S") sur toute route protégée.

RÈGLE SEC-2: services.activity.record() appelé sur tout write action.
             La table activity_logs est append-only (pas d'UPDATE, pas de DELETE).

RÈGLE SEC-3: Pas de <script> inline. CSP bloque les scripts inline.
             Utiliser un fichier .js dans app/static/js/.

RÈGLE SEC-4: Token portail /p/{token} : jamais stocker en clair.
             SHA-256 uniquement dans portal_access_logs.

RÈGLE SEC-5: Validation upload fichier via services.safe_files.
             Vérifier MIME + taille avant persistence.
```

### 2.3 Règles frontend

```
RÈGLE FE-1: Pas de framework JS lourd (React, Vue, Angular).
            HTMX + Alpine.js uniquement.

RÈGLE FE-2: Pas d'inline styles sauf si nécessaire pour MapLibre.
            Préférer les classes CSS Kairos.

RÈGLE FE-3: Polices autorisées UNIQUEMENT : Manrope, DM Serif Display, JetBrains Mono.
            INTERDITS : Inter, Poppins, Segoe UI.

RÈGLE FE-4: Détection HTMX → request.headers.get("hx-request").
            Renvoyer partial HTML ou HX-Redirect selon le contexte.
```

---

## SECTION 3 — CARTOGRAPHIE FICHIERS CRITIQUES

### 3.1 Fichiers racine du système

| Fichier | Rôle | Criticité |
|---------|------|-----------|
| `app/main.py` | Assemblage app (middlewares, routers, handlers) | CRITIQUE |
| `app/config.py` | Configuration (pydantic-settings, .env) | CRITIQUE |
| `app/database.py` | Engine async + get_db() dependency | CRITIQUE |
| `app/auth.py` | Auth staff + client (cookies signés) | CRITIQUE |
| `app/permissions.py` | Matrice RBAC + require_permission() | CRITIQUE |
| `app/csrf.py` | Middleware CSRF double-submit | HAUTE |
| `app/templating.py` | Jinja2 env + filtres + globals | HAUTE |

### 3.2 Middlewares (ordre dans main.py)

```
1. CORSMiddleware         — allow_origins=[settings.site_url]
2. SecurityHeadersMiddleware — CSP + HSTS + X-Frame-Options
3. MaintenanceMiddleware  — lit /tmp/.maintenance (toggle on/off)
4. CSRFMiddleware         — cookie towt_csrf + header
5. ForcePasswordChangeMiddleware — User.must_change_password=True
6. ForceMfaForAdminMiddleware — MFA obligatoire rôle administrateur
```

### 3.3 Services critiques

| Service | Fichier | Fonction clé |
|---------|---------|-------------|
| Activity | `services/activity.py` | `record(db, action, ...)` |
| Booking | `services/booking.py` | Workflow réservation |
| Booking lifecycle | `services/booking_lifecycle.py` | Machine à états |
| Capacity | `services/capacity.py` | SELECT FOR UPDATE legs |
| Chatbot | `services/chatbot.py` | Claude Sonnet 4.6 + anti-injection |
| MFA | `services/mfa.py` | TOTP setup/verify |
| PDF | `services/pdf_generator.py` | WeasyPrint |
| Planning | `services/planning.py` | Gantt + dates cascade |
| Rate limit | `services/rate_limit.py` | Anti-brute force |
| Safe files | `services/safe_files.py` | Upload sécurisé |

---

## SECTION 4 — MODÈLES ORM — SCHÉMA COMPLET

### 4.1 Entités principales et leurs champs clés

```python
# app/models/user.py — Table: users
class User:
    id: int (PK)
    username: str (unique)
    email: str (unique)
    hashed_password: str
    role: str  # voir RBAC ci-dessous
    is_active: bool
    must_change_password: bool
    totp_secret: str | None
    mfa_enabled: bool
    assigned_vessel_id: int | None (FK vessels)
    created_at: datetime
    updated_at: datetime

# app/models/vessel.py — Table: vessels
class Vessel:
    id: int (PK)
    name: str
    mmsi: str | None  # Maritime Mobile Service Identity
    imo: str | None   # International Maritime Organization number
    flag: str | None  # ISO 2-letter country code
    capacity_m3: float | None
    is_active: bool

# app/models/leg.py — Table: legs
class Leg:
    id: int (PK)
    leg_code: str (unique)  # format: {seq}{vessel_code}{dep_country}{arr_country}{year}
    vessel_id: int (FK vessels)
    departure_port_id: int (FK ports)
    arrival_port_id: int (FK ports)
    etd: datetime (tz)    # Estimated Time of Departure
    eta: datetime (tz)    # Estimated Time of Arrival
    atd: datetime | None  # Actual Time of Departure
    ata: datetime | None  # Actual Time of Arrival
    status: str           # draft/confirmed/in_progress/completed/cancelled
    capacity_m3: float | None
    distance_nm: float | None
    # Champs closure (migration 0018)
    closure_submitted_at: datetime | None
    closure_reviewed_at: datetime | None
    closure_approved_at: datetime | None
    closure_submitted_by: str | None
    closure_reviewed_by: str | None
    closure_notes: str | None

# app/models/booking.py — Table: bookings
class Booking:
    id: int (PK)
    reference: str (unique)  # BK-XXXXXXXX
    leg_id: int (FK legs)
    client_account_id: int (FK client_accounts)
    status: str  # draft/submitted/confirmed/departed/delivered/cancelled
    total_volume_m3: float
    total_weight_kg: float
    total_price_eur: Decimal
    currency: str
    notes: str | None
    submitted_at: datetime | None
    confirmed_at: datetime | None
    departed_at: datetime | None
    delivered_at: datetime | None

# app/models/client_account.py — Table: client_accounts
class ClientAccount:
    id: int (PK)
    email: str (unique)
    hashed_password: str
    company_name: str
    is_verified: bool
    mfa_enabled: bool
    totp_secret: str | None
    preferred_lang: str  # fr/en/es/pt-br/vi

# app/models/port.py — Table: ports
class Port:
    id: int (PK)
    locode: str (unique)  # UN LOCODE (ex: FRFEC)
    name: str
    country: str           # ISO 2-letter
    lat: float | None
    lon: float | None
    is_active: bool
    source: str | None

# app/models/packing_list.py — Tables: packing_lists, packing_list_batches, etc.
class PackingList:
    id: int (PK)
    booking_id: int (FK bookings)
    token: str (unique, 24 hex chars)  # portail /p/{token}
    status: str  # draft/submitted/locked
    shipper_name: str
    shipper_email: str

# app/models/activity_log.py — Table: activity_logs
class ActivityLog:
    id: int (PK)
    action: str
    user_id: int | None
    user_name: str | None     # PII masqué (j***@domain.tld)
    user_role: str | None
    module: str | None
    entity_type: str | None
    entity_id: int | None
    entity_label: str | None  # PII masqué
    detail: str | None        # PII masqué
    ip_address: str | None
    created_at: datetime (auto)
```

### 4.2 Matrice RBAC complète

```python
# Rôles disponibles
ROLES = (
    "administrateur",   # Accès total à tous les modules
    "operation",        # Planning, commercial, escale, cargo, captain, crew, claims, mrv
    "armement",         # Planning(C), escale(C), captain(C), crew(CMS), rh(CM)
    "technique",        # Escale(CMS), captain(CM), mrv(CM), tickets(CM)
    "data_analyst",     # Finance(CMS), analytics(CMS), lecture tous modules
    "marins",           # Lecture : planning, escale, kpi, captain, crew, cargo, mrv, rh
    "commercial",       # Commercial(CMS), booking(CMS), cargo(CM)
    "manager_maritime", # Captain(CMS), tickets(CMS), analytics(CM), admin(C)
)

# Notation niveaux :
# C = Consult (lecture seule)
# M = Modify (lecture + écriture)
# S = Suppress (+ suppression)
# CMS = accès complet
```

---

## SECTION 5 — POINTS DE DÉFAILLANCE COURANTS ET REMÈDES

### 5.1 Erreurs de démarrage

```
PROBLÈME: "SECRET_KEY must be at least 32 characters"
CAUSE:    .env manquant ou SECRET_KEY trop courte
REMÈDE:   Générer: python -c "import secrets; print(secrets.token_urlsafe(32))"
          Ajouter dans .env: SECRET_KEY=<valeur générée>

PROBLÈME: "DATABASE_URL must use the async driver: postgresql+asyncpg://"
CAUSE:    DATABASE_URL commence par postgresql:// sans +asyncpg
REMÈDE:   Corriger: DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

PROBLÈME: "Production refusing to start: DATABASE_URL password is in the weak list"
CAUSE:    Mot de passe DB dans WEAK_DB_PASSWORDS = {towt_secure_2025, change_me_local, ...}
REMÈDE:   Générer un mot de passe fort dans .env
```

### 5.2 Erreurs 500 fréquentes

```
PROBLÈME: SQLAlchemy MissingGreenlet / "greenlet_spawn has not been called"
CAUSE:    Accès lazy-load à un attribut ORM hors contexte async
REMÈDE:   Utiliser selectinload() ou joinedload() dans la query :
          result = await db.execute(
              select(Booking).options(selectinload(Booking.items))
              .where(Booking.id == booking_id)
          )

PROBLÈME: "CSRF validation failed" sur formulaire POST
CAUSE:    Token CSRF manquant ou expiré
REMÈDE:   Vérifier que csrf-htmx.js est chargé dans base.html
          Pour un formulaire HTML statique, ajouter:
          <input type="hidden" name="csrf_token" value="{{ csrf_token }}">

PROBLÈME: "AuthRequired" / redirect login en boucle
CAUSE:    Cookie towt_session expiré ou secret_key changé
REMÈDE:   Effacer le cookie, se reconnecter.
          En prod: ne pas changer SECRET_KEY (invalide toutes les sessions)

PROBLÈME: "Permission denied: module/level" (403)
CAUSE:    require_permission() bloque un rôle insuffisant
REMÈDE:   Vérifier la matrice RBAC dans permissions.py
          Ajouter le tuple (role, module): "CM" si besoin
```

### 5.3 Erreurs de migration Alembic

```
PROBLÈME: "Target database is not up to date"
CAUSE:    Migrations non appliquées
REMÈDE:   docker compose exec app alembic upgrade head

PROBLÈME: "Can't locate revision" après rollback
CAUSE:    Migration supprimée localement mais présente en DB
REMÈDE:   alembic stamp <revision_id>  # forcer l'état
          puis alembic upgrade head

PROBLÈME: "DuplicateTable" au démarrage dev
CAUSE:    init_db() tente create_all sur tables existantes
REMÈDE:   Normal en dev (checkfirst=True implicite).
          En prod, ne pas utiliser init_db() — Alembic uniquement.
```

### 5.4 Erreurs PDF WeasyPrint

```
PROBLÈME: "cannot load library 'libgobject-2.0'" au démarrage
CAUSE:    Dépendances système WeasyPrint manquantes dans le container
REMÈDE:   Vérifier Dockerfile — installer libgobject, libcairo, libpango

PROBLÈME: PDF vide ou tronqué
CAUSE:    Template Jinja2 avec erreur silencieuse
REMÈDE:   Tester d'abord le rendu HTML pur :
          response = templates.TemplateResponse("pdf/invoice.html", ctx)
          Puis activer WeasyPrint une fois le HTML validé
```

### 5.5 Erreurs chatbot Kairos AI

```
PROBLÈME: "ANTHROPIC_API_KEY not configured"
CAUSE:    Variable d'environnement absente
REMÈDE:   Ajouter ANTHROPIC_API_KEY dans .env

PROBLÈME: "Injection attempt detected" — refus systématique
CAUSE:    Message contient un pattern de prompt injection
REMÈDE:   Vérifier INJECTION_PATTERNS dans services/chatbot.py
          Pas de faux positif ? Retirer le pattern concerné

PROBLÈME: Coût API excessif
CAUSE:    Prompt cache désactivé ou mauvaise configuration
REMÈDE:   Vérifier cache_control={"type":"ephemeral"} dans les appels API
          Utiliser claude-sonnet-4-6 (modèle configuré, pas d'autre)
```

---

## SECTION 6 — PROCÉDURES DE RÉCUPÉRATION

### 6.1 Retour à une version stable

```bash
# Lister les commits stables (merges PR)
git log --oneline --merges

# Points de retour sûrs identifiés :
# 75dc0d8 — feat(public): redesign route detail (stable, post-PR-9)
# e828a38 — Merge PR#9 (stable)
# ff4d518 — feat: supprime WebAuthn (stable, post-PR-7)
# 7a3a3b7 — feat(analytics): 3 dashboards (stable)
# 9e112e6 — Merge Sprint 2 & 3 — ERP KPI/Finance (stable)

# Retour à un commit stable :
git checkout <commit_hash>           # Détached HEAD (lecture seule)
# ou pour créer une branche de récupération :
git checkout -b recovery/<date> <commit_hash>

# Vérifier l'état des migrations correspondant à ce commit :
git show <commit_hash>:migrations/versions/ | head -20
```

### 6.2 Récupération base de données

```bash
# Backup manuel immédiat
docker compose exec db pg_dump -U towt towt > backup_$(date +%Y%m%d_%H%M).sql

# Rollback migration Alembic (downgrade d'une version)
docker compose exec app alembic downgrade -1

# Rollback à une révision spécifique
docker compose exec app alembic downgrade 20260519_0017

# Restore depuis backup
cat backup_20260527_1200.sql | docker compose exec -T db psql -U towt towt
```

### 6.3 Récupération mot de passe admin

```bash
# Script dédié (reset sans UI)
docker compose exec app python scripts/reset_password.py --username admin --password NewPass!2026
```

### 6.4 Mode maintenance d'urgence

```bash
# Activer
docker compose exec app touch /tmp/.maintenance

# Désactiver
docker compose exec app rm /tmp/.maintenance

# Via script
./scripts/maintenance.sh on
./scripts/maintenance.sh off
```

### 6.5 Diagnostic rapide en production

```bash
# Health check
curl https://my.newtowt.eu/health
# Réponse attendue: {"status":"ok","version":"3.1.x","env":"production"}

# Logs applicatifs en temps réel
docker compose logs -f app --tail=100

# Logs erreurs uniquement
docker compose logs app | grep -E "ERROR|CRITICAL|500"

# Métriques Prometheus
curl https://my.newtowt.eu/metrics | grep -E "http_requests|error"

# État DB
docker compose exec db pg_isready -U towt

# Connexions DB actives
docker compose exec db psql -U towt -c "SELECT count(*) FROM pg_stat_activity WHERE datname='towt';"
```

---

## SECTION 7 — INVENTAIRE DES VARIABLES D'ENVIRONNEMENT CRITIQUES

```bash
# OBLIGATOIRES (app ne démarre pas sans elles)
SECRET_KEY=                     # >= 32 chars, random, ne JAMAIS changer en prod
DATABASE_URL=                   # postgresql+asyncpg://user:pass@host:5432/db
APP_ENV=                        # development | staging | production

# SÉCURITÉ (obligatoires en production)
POSTGRES_PASSWORD=              # Ne pas utiliser: towt_secure_2025, change_me_local
INITIAL_ADMIN_PASSWORD=        # Changer immédiatement après premier boot

# OPTIONNELLES MAIS FONCTIONNELLEMENT CRITIQUES
ANTHROPIC_API_KEY=              # Sans ça: /chat désactivé, chatbot Kairos inopérant
SMTP_HOST=                      # Sans ça: aucun email envoyé (booking confirmé, etc.)
MAPTILER_TOKEN=                 # Sans ça: cartes vides (routes, fleet, tracking)
TRACKING_API_TOKEN=             # Sans ça: /api/tracking/upload retourne 503

# OBSERVABILITÉ
SENTRY_DSN=                     # Sans ça: erreurs non tracées en production
```

---

## SECTION 8 — ARCHITECTURE DE SÉCURITÉ DÉTAILLÉE

### 8.1 Cookies de session

```python
# Staff : cookie towt_session
# - Signé avec itsdangerous.URLSafeTimedSerializer(SECRET_KEY, salt="staff-session")
# - max_age: 480 min (8h) pour bureau, 14 jours pour rôles marins/manager_maritime
# - httponly=True, secure=True (prod), samesite="lax"

# Client : cookie towt_client_session
# - Signé avec salt="client-session"
# - max_age: settings.client_session_days * 86400 (30j par défaut)
# - httponly=True, secure=True (prod), samesite="lax"

# CRITIQUE : Changer SECRET_KEY invalide TOUTES les sessions actives.
```

### 8.2 Flux MFA TOTP

```
1. POST /login → vérif password → créer cookie towt_staff_mfa_pending (5 min)
2. GET /login/mfa → formulaire TOTP
3. POST /login/mfa → vérif TOTP → effacer mfa_pending → créer towt_session
```

### 8.3 Portail expéditeur /p/{token}

```
- token : UUID hex 24 caractères (= 12 bytes = 96 bits d'entropie)
- Durée : 90 jours
- Stockage DB : token haché SHA-256 uniquement
- Accès audité : PortalAccessLog (IP, user-agent, timestamp)
- Le token en clair n'est jamais persisté
```

### 8.4 CSRF

```python
# Middleware CSRFMiddleware (app/csrf.py)
# Cookie: towt_csrf (SameSite=Strict, HttpOnly=False pour lecture JS)
# Header attendu: X-CSRF-Token (injecté par csrf-htmx.js sur toute requête HTMX)
# Les routes GET sont exemptées automatiquement
```

---

## SECTION 9 — DÉPENDANCES TECHNIQUES ET VERSIONS FIGÉES

```toml
# requirements.txt (production) — versions figées pour reproductibilité

# Core
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
pydantic-settings==2.7.0
python-multipart==0.0.20

# Database
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.0
pgvector==0.3.6

# Security
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
itsdangerous==2.2.0
pyotp==2.9.0
segno==1.6.1
cryptography==44.0.0

# Templating
jinja2==3.1.5
babel==2.16.0

# HTTP / External
httpx==0.28.1
stripe==11.4.1   # NOTE: lib présente mais Stripe désactivé en V3.1

# Documents
openpyxl==3.1.5
python-docx==1.1.2
reportlab==4.2.5
weasyprint==63.1

# AI
anthropic==0.49.0   # Claude Sonnet 4.6

# Observabilité
sentry-sdk[fastapi]==2.20.0
opentelemetry-instrumentation-fastapi==0.50b0
opentelemetry-instrumentation-sqlalchemy==0.50b0
opentelemetry-exporter-otlp==1.29.0
prometheus-fastapi-instrumentator==7.0.0
loguru==0.7.3

# Utilities
python-magic==0.4.27
bleach==6.2.0
phonenumbers==8.13.50
email-validator==2.2.0
```

---

## SECTION 10 — INFRASTRUCTURE DE DÉPLOIEMENT

### 10.1 docker-compose.yml — services

```yaml
# 3 services en production :
db:       PostgreSQL 16-alpine, volume pgdata (persistant)
app:      FastAPI/Uvicorn, expose 8000 (interne uniquement)
caddy:    Caddy 2-alpine, ports 80/443/443-udp (HTTP/3), TLS auto Let's Encrypt

# Volumes persistants :
pgdata:       Données PostgreSQL
uploads:      Fichiers uploadés (packing list docs, pièces)
caddy_data:   Certificats TLS + état Let's Encrypt
caddy_config: Configuration Caddy
```

### 10.2 Dockerfile (simplifié)

```
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# [Dépendances système WeasyPrint: libgobject, libcairo, libpango, libffi]
COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.3 Commandes opérationnelles

```bash
# Démarrage complet
docker compose up -d

# Migrations
docker compose exec app alembic upgrade head

# Seed démo (dev uniquement)
docker compose exec app python scripts/seed_demo.py

# Arrêt propre
docker compose down

# Rebuild après modification Dockerfile/requirements.txt
docker compose build app && docker compose up -d app

# Smoke tests post-déploiement
./scripts/smoke-tests.sh
```

---

## SECTION 11 — CATALOGUE DES TEMPLATES PDF

| Template | Chemin | Usage |
|----------|--------|-------|
| Base PDF | `templates/pdf/_base.html` | Héritage commun |
| Bill of Lading | `templates/pdf/bill_of_lading.html` | BL officiel |
| Packing List | `templates/pdf/packing_list.html` | Liste de colisage |
| Invoice | `templates/pdf/invoice.html` | Facture client (virement) |
| Certificat Anemos | `templates/pdf/anemos_certificate.html` | Certificat CO₂ |
| NOR | `templates/pdf/cargo_doc_nor.html` | Notice of Readiness |
| LOP | `templates/pdf/cargo_doc_lop.html` | Letter of Protest |
| Mate's Receipt | `templates/pdf/cargo_doc_mates_receipt.html` | Reçu du second |
| SOF Captain | `templates/pdf/sof_captain.html` | SOF signé commandant |
| SOF Escale | `templates/pdf/sof_escale.html` | SOF escale ops |

---

## SECTION 12 — GLOSSAIRE TECHNIQUE MARITIME

| Terme | Définition technique |
|-------|---------------------|
| `leg_code` | `{seq}{vessel_code}{dep_country}{arr_country}{year_digit}` ex: `1CFRBR6` |
| `ETD/ETA` | Estimated Time of Departure/Arrival (tz-aware datetime) |
| `ATD/ATA` | Actual Time of Departure/Arrival (tz-aware datetime) |
| `LOCODE` | Code UN port 5 chars : `FR` + `FEC` = Fécamp = `FRFEC` |
| `MMSI` | 9 digits, identifiant AIS navire |
| `IMO` | 7 digits, numéro permanent navire (IMO + 7 chiffres) |
| `SOF` | Statement of Facts : chronologie notariée du temps en port |
| `MRV` | EU Monitoring, Reporting, Verification (émissions navires) |
| `MDO` | Marine Diesel Oil (carburant de secours) |
| `ROB` | Remaining On Board (fuel restant en fin de traversée) |
| `BL/BOL` | Bill of Lading : titre de transport et propriété cargo |
| `POL/POD` | Port of Loading / Port of Discharge |
| `OPEX` | Operating Expenditure (coût journalier exploitation navire) |
| `EOSP/SOSP` | End/Start of Sea Passage (départ/arrivée pilote) |
| `NOR` | Notice of Readiness (navire prêt à charger) |
| `LOP` | Letter of Protest (réserves écrites sur incident cargo) |

---

## SECTION 13 — HISTORIQUE GIT — POINTS DE STABILITÉ

```
# Commits stables pour retour arrière (du plus récent au plus ancien) :

SHA       DATE        DESCRIPTION                        STABILITÉ
6f40fca   2026-05-27  fix(i18n): basculement langue       STABLE  ← HEAD
458c5ee   2026-05-27  feat(public): redesign Anemos       STABLE
e828a38   2026-05-26  Merge PR#9                          STABLE ✓ (merge)
75dc0d8   2026-05-26  feat(public): route detail redesign STABLE
d0b7d9c   2026-05-25  fix(planning): submit button wizard STABLE
366d6da   2026-05-25  Merge PR#8                          STABLE ✓ (merge)
ff4d518   2026-05-25  feat: supprime WebAuthn             STABLE
9209bcf   2026-05-24  Merge PR#7                          STABLE ✓ (merge)
7a3a3b7   2026-05-24  feat(analytics): 3 dashboards       STABLE
c112cae   2026-05-23  fix(ui): 6 corrections interface    STABLE
c9dd0d8   2026-05-23  Merge PR#6                          STABLE ✓ (merge)
9e112e6   2026-05-22  Merge Sprint 2 & 3 — KPI/Finance    STABLE ✓ (merge)

# Pour revenir à un point de merge stable :
git checkout <SHA_du_merge>
```

---

## SECTION 14 — CHECKLIST D'INTÉGRATION NOUVELLE INFRASTRUCTURE IA

Pour intégrer ce projet dans une nouvelle infrastructure IA ou un nouvel
agent de code, valider chaque point :

```
□ 1. Lire ce document en premier (CODEBASE-REFERENCE.md)
□ 2. Lire CLAUDE.md (règles de développement)
□ 3. Vérifier les règles absolues Section 2 (DB, sécurité, frontend)
□ 4. Configurer .env avec les variables Section 7
□ 5. Lancer les tests : pytest -q (25 tests doivent passer)
□ 6. Vérifier la révision Alembic HEAD : 20260526_0019
□ 7. Vérifier le health check : GET /health → {"status":"ok"}
□ 8. Vérifier le point d'entrée : app/main.py → create_app()
□ 9. Ne jamais modifier la matrice RBAC sans review sécurité
□ 10. Tout write action → services.activity.record() obligatoire
□ 11. Modèle IA chatbot : claude-sonnet-4-6 (ne pas changer)
□ 12. Pas de commit() dans les routes (RÈGLE DB-1 absolue)
```

---

## SECTION 15 — CONTACTS ET RESSOURCES

```yaml
repository: https://github.com/juliengonde-5g/mynewtowt
production: https://my.newtowt.eu
health: https://my.newtowt.eu/health
security_contact: mailto:communication@towt.eu
security_txt: https://my.newtowt.eu/.well-known/security.txt

documentation:
  technical: docs/technical/01-technical-reference.md
  user_guide: docs/user/01-user-guide-staff.md
  architecture: docs/architecture/01-architecture.md
  runbook: docs/operations/01-runbook.md
  security: docs/security/01-security-review.md
  audit_plan: docs/audit/01-audit-plan.md

key_files:
  entrypoint: app/main.py
  config: app/config.py
  models: app/models/__init__.py
  permissions: app/permissions.py
  design_tokens: Versions TOWT/newtowt-design-tokens.json
  migrations_head: migrations/versions/20260526_0019_drop_webauthn.py
```
