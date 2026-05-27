# Plan d'Audit — mynewtowt V3.1

> **Date d'établissement** : 2026-05-27
> **Périmètre** : Application web mynewtowt (ERP interne + plateforme client)
> **Normes de référence** : OWASP ASVS v4, ISO 27001, RGPD/GDPR, DORA,
> NIS2, DNV GL (MRV), réglementation maritime UE

---

## 1. Cadre général

### 1.1 Objectifs de l'audit

1. **Sécurité** : vérifier la résistance aux attaques (OWASP Top 10, ASVS)
2. **Conformité RGPD** : traitement des données personnelles (clients B2B, équipage)
3. **Qualité du code** : dette technique, maintenabilité, couverture de tests
4. **Performances** : temps de réponse, concurrence, scalabilité
5. **Opérations** : backup, restauration, haute disponibilité
6. **Réglementation maritime** : MRV, DNV, documentation cargo

### 1.2 Criticité des modules

| Module | Criticité | Justification |
|--------|-----------|---------------|
| Auth + RBAC | CRITIQUE | Contrôle d'accès total |
| Booking + capacité | CRITIQUE | Impact financier direct |
| MRV | ÉLEVÉE | Obligation réglementaire UE |
| Cargo + BL | ÉLEVÉE | Documents juridiquement opposables |
| Finance | ÉLEVÉE | Données financières sensibles |
| Chatbot IA | MOYENNE | Risque injection prompt + coût API |
| Planning | MOYENNE | Coordination opérationnelle |
| Portail /p/{token} | ÉLEVÉE | Accès externe non-authentifié |

---

## 2. Audit Sécurité — OWASP ASVS v4

### 2.1 A01 — Contrôle d'accès (Broken Access Control)

**Tests à conduire :**

| Ref | Test | Statut |
|-----|------|--------|
| ASVS 4.1 | Vérifier require_permission() sur chaque endpoint protégé | À vérifier |
| ASVS 4.2 | IDOR : accès à une ressource d'un autre utilisateur via ID | À tester |
| ASVS 4.3 | Élévation de privilèges : client accède à route staff (/dashboard) | À tester |
| ASVS 4.4 | Accès token portail expiré (> 90 jours) | À tester |
| ASVS 4.5 | Matrice RBAC : vérifier toutes les 8×16 combinaisons | À vérifier |

**Code à auditer :**
- `app/permissions.py` — matrice `_MATRIX`
- Tous les routers `app/routers/*.py` — présence `Depends(require_permission(...))`
- `app/routers/cargo_portal_router.py` — validation token portail

### 2.2 A02 — Cryptographie

| Ref | Test | Statut |
|-----|------|--------|
| ASVS 6.1 | Algorithme bcrypt (cost ≥ 10) | OK (passlib[bcrypt]) |
| ASVS 6.2 | SECRET_KEY ≥ 32 chars validée au démarrage | OK (config.py) |
| ASVS 6.3 | Cookies session : httponly + secure + samesite | À vérifier en prod |
| ASVS 6.4 | Token portail : entropie 96 bits (24 hex = 12 bytes) | OK |
| ASVS 6.5 | SHA-256 pour stockage token portail | À vérifier (cargo_portal_router) |

### 2.3 A03 — Injection

| Ref | Test | Statut |
|-----|------|--------|
| ASVS 5.1 | SQL injection via ORM SQLAlchemy | Couvert (bindparams) |
| ASVS 5.2 | Pas de f-string SQL (règle absolue) | À vérifier par grep |
| ASVS 5.3 | XSS : bleach sur toutes entrées utilisateur affichées | À vérifier |
| ASVS 5.4 | Prompt injection chatbot : INJECTION_PATTERNS | OK (chatbot.py) |
| ASVS 5.5 | SSTI (Server-Side Template Injection) via Jinja2 | À vérifier (autoescape) |

**Commandes de vérification :**
```bash
# Chercher les f-strings SQL potentielles
grep -r "f\"" app/routers/ | grep -i "select\|insert\|update\|delete"
grep -r 'f"' app/services/ | grep -i "select\|insert\|update\|delete"

# Vérifier autoescape Jinja2
grep "autoescape" app/templating.py
```

### 2.4 A04 — Design sécurisé

| Ref | Test | Statut |
|-----|------|--------|
| ASVS 1.1 | Modèle de menace documenté | À produire |
| ASVS 1.2 | Séparation contextes auth (staff vs client) | OK |
| ASVS 1.3 | Audit trail append-only (ActivityLog) | OK |
| ASVS 1.4 | Feature flags pour fonctionnalités risquées | OK (FeatureFlag) |

### 2.5 A05 — Configuration

| Ref | Test | Statut |
|-----|------|--------|
| ASVS 2.1 | Docs FastAPI désactivés en production | OK (main.py) |
| ASVS 2.2 | HSTS activé (max-age=31536000 + preload) | OK (security_headers.py) |
| ASVS 2.3 | CSP restrictive (no unsafe-inline scripts) | OK |
| ASVS 2.4 | X-Frame-Options: SAMEORIGIN | OK |
| ASVS 2.5 | Permissions-Policy désactive camera/micro/géo | OK |
| ASVS 2.6 | Debug=False en production | À vérifier (.env prod) |

### 2.6 A07 — Authentification et identité

| Ref | Test | Statut |
|-----|------|--------|
| ASVS 3.1 | Brute-force : rate limiting sur /login | À tester (rate_limit.py) |
| ASVS 3.2 | Compte verrouillé après N échecs | À vérifier |
| ASVS 3.3 | MFA TOTP : dérivé pyotp (RFC 6238) | OK |
| ASVS 3.4 | Codes de secours MFA : hashés en DB | OK |
| ASVS 3.5 | Session invalidée à la déconnexion | À vérifier (cookie supprimé ?) |
| ASVS 3.6 | Durée session par rôle (8h bureau, 14j marins) | OK |

### 2.7 A08 — Intégrité logicielle

| Ref | Test | Statut |
|-----|------|--------|
| ASVS 10.1 | Versions dépendances figées (requirements.txt) | OK |
| ASVS 10.2 | Pas de dépendances avec CVE critique connue | À scanner (safety) |
| ASVS 10.3 | Dockerfile minimal (pas de root en production) | À vérifier |

**Commande :**
```bash
pip install safety
safety check -r requirements.txt
```

### 2.8 A09 — Logging et monitoring

| Ref | Test | Statut |
|-----|------|--------|
| ASVS 7.1 | Logs structurés (loguru) | OK |
| ASVS 7.2 | PII masqués dans les logs (emails → j***@domain) | OK (activity.py) |
| ASVS 7.3 | Sentry configuré en production | À vérifier (SENTRY_DSN) |
| ASVS 7.4 | Prometheus metrics actifs | OK |
| ASVS 7.5 | Alertes sur error rate > 1% | À configurer (Grafana) |

### 2.9 A10 — SSRF

| Ref | Test | Statut |
|-----|------|--------|
| ASVS 12.1 | Validation URL avant appel httpx externe | À vérifier (weather.py, pipedrive.py) |
| ASVS 12.2 | Pas de fetch vers IP interne possible | À tester |

---

## 3. Audit RGPD/GDPR

### 3.1 Inventaire des données personnelles traitées

| Catégorie | Données | Localisation | Base légale |
|-----------|---------|-------------|-------------|
| Clients B2B | Email, nom entreprise, contact | `client_accounts` | Contrat |
| Équipage | Nom, prénom, nationalité, passeport | `crew_members` | Contrat travail |
| Expéditeurs | Email, nom (packing list) | `packing_lists` | Contrat transport |
| Logs d'activité | IP, user_name masqué | `activity_logs` | Intérêt légitime |
| Logs accès portail | IP, timestamp | `portal_access_logs` | Sécurité |
| Chatbot | Messages utilisateur | `chat_messages` | Consentement |

### 3.2 Checklist RGPD

| Article | Exigence | Statut |
|---------|---------|--------|
| Art. 5 | Minimisation des données | À vérifier |
| Art. 6 | Base légale documentée | À formaliser |
| Art. 12-15 | Droits d'accès et portabilité | À implémenter |
| Art. 17 | Droit à l'effacement | À implémenter (purge ciblée) |
| Art. 25 | Privacy by design | Partiellement OK |
| Art. 32 | Mesures techniques de sécurité | OK (bcrypt, HTTPS, CSP) |
| Art. 33-34 | Notification de violation (72h) | Procédure à documenter |
| Art. 35 | Analyse d'impact (DPIA) | À réaliser |

### 3.3 Actions RGPD prioritaires

1. **Politique de conservation** : définir la durée de rétention par type de données
2. **Registre des traitements** : formaliser selon Art. 30
3. **Procédure violation** : définir le processus d'alerte CNIL en < 72h
4. **Droit à l'effacement** : implémenter la purge ciblée `scripts/purge_legs.py`
   doit couvrir également les données personnelles associées

---

## 4. Audit Qualité du Code

### 4.1 Métriques à mesurer

```bash
# Couverture de tests
pytest --cov=app --cov-report=html --cov-fail-under=70

# Analyse statique
ruff check app/                          # linting (pyproject.toml)
mypy app/ --ignore-missing-imports       # typage statique

# Complexité cyclomatique
pip install radon
radon cc app/ -a -nb                     # score > 10 = à refactoriser

# Sécurité statique
bandit -r app/ -ll                       # vulnérabilités courantes
```

### 4.2 Critères de qualité acceptables

| Métrique | Cible | Actuel |
|----------|-------|--------|
| Couverture tests | ≥ 70 % | À mesurer |
| Score Ruff | 0 erreurs | À vérifier |
| Score Mypy | 0 erreurs critiques | À vérifier |
| Complexité cyclomatique max | < 15 | À mesurer |
| Bandit score | 0 HIGH | À vérifier |

### 4.3 Dette technique identifiée

| Élément | Localisation | Priorité |
|---------|-------------|----------|
| Stripe lib présente mais désactivé | `requirements.txt` ligne stripe | BASSE (supprimer si non utilisé) |
| Module RH en stub | `app/routers/modules_router.py` | BASSE (backlog) |
| Module KPI partiel | `app/routers/kpi_router.py` | MOYENNE |
| Architecture doc référence nginx | `docs/architecture/01-architecture.md` | BASSE (doc obsolète) |
| Schémas Pydantic incomplets | `app/schemas/` (seulement booking + leg) | MOYENNE |

---

## 5. Audit Performances

### 5.1 Tests de charge

```bash
# Outil recommandé : k6 ou locust
# Scénario : 50 utilisateurs simultanés, 5 minutes

# Points de mesure prioritaires :
# 1. GET /planning (Gantt charge principale)
# 2. POST /booking/new (step 3, vérification capacité)
# 3. GET /cargo/packing-lists (liste avec joins)
# 4. POST /chat/messages (appel Anthropic API)
# 5. GET /api/v1/routes (page publique cacheable)
```

### 5.2 Cibles de performance

| Endpoint | P95 cible | Note |
|----------|-----------|------|
| Pages HTML (ERP) | < 500 ms | Avec DB |
| API publique | < 200 ms | Avec cache |
| Génération PDF | < 3 s | WeasyPrint |
| Chat IA | < 5 s TTFB | Anthropic API |
| Upload fichier | < 2 s | 10 Mo max |

### 5.3 Optimisations à examiner

- **Pool DB** : `pool_size=10, max_overflow=10` — adéquat pour charge actuelle
- **Queries N+1** : vérifier les `selectinload` manquants dans les listes
- **Index DB** : vérifier les index sur `legs.leg_code`, `bookings.reference`, `ports.locode`
- **Cache** : pas de cache HTTP actuellement — envisager pour `/api/v1/routes`

---

## 6. Audit Opérationnel

### 6.1 Backup et restauration

| Contrôle | Exigence | Statut |
|----------|---------|--------|
| Fréquence backup | Quotidien | À vérifier (cron) |
| Rétention | 7 jours min (paramétrable) | `BACKUP_RETENTION_DAYS=7` |
| Chiffrement backup | GPG recommandé | `BACKUP_GPG_RECIPIENT` si configuré |
| Test de restauration | Mensuel | À planifier |
| RPO (Recovery Point Objective) | ≤ 24h | OK si backup quotidien |
| RTO (Recovery Time Objective) | ≤ 4h | À tester |

**Test restauration à planifier :**
```bash
# 1. Arrêter l'app
# 2. Restaurer le backup dans un environnement test
# 3. Lancer alembic upgrade head
# 4. Vérifier les données critiques (bookings confirmés, legs actifs)
# 5. Mesurer le temps total → RTO réel
```

### 6.2 Haute disponibilité

| Composant | Mode actuel | Recommandation |
|-----------|------------|----------------|
| Application | 1 instance | 2 replicas derrière load balancer (V3.2) |
| Base de données | Standalone | Réplique lecture + failover (V3.2) |
| Caddy | 1 instance | OK (stateless, auto-redémarrage) |
| Volumes | Local | Backup S3 chiffré |

### 6.3 Procédures d'urgence

```bash
# Vérifier le statut : scripts/smoke-tests.sh
# Mode maintenance : scripts/maintenance.sh on|off
# Rollback version : scripts/rollback.sh
# Reset mot de passe admin : scripts/reset_password.py
```

---

## 7. Audit Réglementaire Maritime

### 7.1 MRV (Monitoring, Reporting, Verification — Règlement UE 2015/757)

| Exigence | Contrôle | Statut |
|---------|---------|--------|
| Données fuel par traversée | `mrv_events` table | OK |
| Paramètres émissions configurables | `mrv_parameters` | OK |
| Export CSV format DNV | `services/mrv_export.py` | OK |
| Vérification annuelle DNV | Interface admin export | OK |
| Traçabilité données | `activity_logs` | OK |

### 7.2 Documents cargo — valeur juridique

| Document | Template | Valeur légale |
|----------|----------|---------------|
| Bill of Lading | `pdf/bill_of_lading.html` | Titre de propriété |
| Packing List | `pdf/packing_list.html` | Liste de colisage officielle |
| SOF | `pdf/sof_captain.html` | Acte notarié de l'escale |
| Notice of Readiness | `pdf/cargo_doc_nor.html` | Notification officielle |

**Point d'attention** : La signature numérique des SOF (service `signature.py`)
doit être auditée pour vérifier sa valeur juridique selon le droit maritime français.

---

## 8. Calendrier d'audit recommandé

| Période | Audit | Responsable |
|---------|-------|-------------|
| **Immédiat** | Scan CVE dépendances (`safety check`) | Dev |
| **Immédiat** | Vérification inject SQL (`grep` + test) | Dev |
| **Mois 1** | Audit OWASP ASVS Sections 2.1 à 2.6 | Sécurité interne |
| **Mois 1** | Test restauration backup | Ops |
| **Mois 2** | Audit RGPD complet + registre traitements | DPO |
| **Mois 2** | Test de charge (50 users, 5 min) | Dev |
| **Mois 3** | Audit externe sécurité (pentesting) | Prestataire spécialisé |
| **Annuel** | Revue matrice RBAC | Sécurité + Métier |
| **Annuel** | Vérification MRV (avant soumission DNV) | Ops maritime |

---

## 9. Rapport d'audit — Template

Pour chaque finding, documenter :

```markdown
## FINDING-XXX : [Titre]

**Sévérité** : CRITIQUE / HAUTE / MOYENNE / BASSE / INFO
**Norme** : OWASP ASVS X.X / RGPD Art. XX / ISO 27001 A.XX
**Module** : [module concerné]
**Fichier** : `app/path/to/file.py:line_number`

### Description
[Description technique du problème]

### Impact
[Impact potentiel si exploité]

### Preuve
```[code ou screenshot]```

### Remédiation
[Correction recommandée avec exemple de code si applicable]

### Statut
- [ ] À corriger
- [ ] En cours (PR #XX)
- [ ] Corrigé (commit XXXXXXX)
- [ ] Accepté comme risque résiduel
```

---

## 10. Outils d'audit recommandés

| Catégorie | Outil | Commande |
|-----------|-------|---------|
| CVE scan | safety | `safety check -r requirements.txt` |
| Sécurité statique | bandit | `bandit -r app/ -ll` |
| Linting | ruff | `ruff check app/` |
| Typage | mypy | `mypy app/` |
| Couverture | pytest-cov | `pytest --cov=app` |
| Complexité | radon | `radon cc app/ -a` |
| Pentest web | OWASP ZAP | Scan automatisé + manuel |
| SQL injection | sqlmap | Test sur endpoints formulaires |
| Dépendances | pip-audit | `pip-audit -r requirements.txt` |
| Secrets exposés | trufflehog | `trufflehog git file://.` |
