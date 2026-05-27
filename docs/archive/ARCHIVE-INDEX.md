# Index d'archives — Documentation obsolète

> **Date d'archivage** : 2026-05-27
> Ce répertoire référence les documents qui ne sont plus à jour
> ou qui correspondent à des versions antérieures (V2, V3.0).

---

## Documents V2 (obsolètes — référence historique uniquement)

Ces documents sont localisés dans `Versions TOWT/docs/v2/` et correspondent
à l'application V2, qui a été remplacée par V3 en 2026.

| Document | Chemin | Raison d'obsolescence |
|----------|--------|----------------------|
| Roadmap V2 | `Versions TOWT/docs/v2/roadmap.md` | Remplacé par `docs/strategy/00-vision.md` |
| Router audit V2 | `Versions TOWT/docs/v2/router-audit.md` | Architecture V3 totalement différente |
| User guide V2 | `Versions TOWT/docs/v2/user-guide.md` | Remplacé par `docs/user/01-user-guide-staff.md` |
| Chatbot spec V2 | `Versions TOWT/docs/v2/chatbot-spec.md` | Kairos AI V3 (Claude Sonnet 4.6) différent |
| Ticketing spec V2 | `Versions TOWT/docs/v2/ticketing-spec.md` | Module tickets V3 livré |

## Code V2 archivé (référence technique uniquement)

Le répertoire `Versions TOWT/old/` contient l'intégralité du code V2.
**Ne pas utiliser comme base de développement.**

| Élément | Note |
|---------|------|
| `Versions TOWT/old/app/` | Code V2 complet (routers, models, services) |
| `Versions TOWT/old/CLAUDE.md` | Guide dev V2 — remplacé par CLAUDE.md racine |
| `Versions TOWT/old/README.md` | README V2 — remplacé par README.md racine |

## Documents V3.0 partiellement obsolètes (corrections à apporter)

Ces documents existent et sont globalement à jour, mais contiennent
des références obsolètes identifiées lors de l'audit du 2026-05-27.

| Document | Chemin | Correction requise |
|----------|--------|-------------------|
| Architecture | `docs/architecture/01-architecture.md` | ~~Stripe~~ (retiré V3.1), ~~nginx~~ → Caddy, ~~worker Celery~~ (non déployé) |

## Documents V3.0 actifs et à jour

| Document | Chemin | Statut |
|----------|--------|--------|
| Vision produit | `docs/strategy/00-vision.md` | ✅ Actif |
| Plan de déploiement | `docs/strategy/01-deployment-plan.md` | ✅ Actif |
| Vérification avant livraison | `docs/strategy/04-verification-before-completion.md` | ✅ Actif |
| Optimisation processus | `docs/strategy/08-process-optimization.md` | ✅ Actif |
| Architecture | `docs/architecture/01-architecture.md` | ⚠️ Corrections mineures |
| Design handoff | `docs/design/01-design-handoff.md` | ✅ Actif |
| Redesign brief | `docs/design/02-redesign-brief.md` | ✅ Actif |
| Runbook | `docs/operations/01-runbook.md` | ✅ Actif |
| Debugging playbook | `docs/operations/debugging-playbook.md` | ✅ Actif |
| Defect board | `docs/operations/defect-board.md` | ✅ Actif |
| Personas | `docs/personas/01-personas.md` | ✅ Actif |
| Security review | `docs/security/01-security-review.md` | ✅ Actif |
| Booking platform | `docs/booking/01-cale-booking-platform.md` | ✅ Actif |
| Data strategy | `docs/analytics/01-data-strategy.md` | ✅ Actif |
| PRODUCTION-NOTEBOOK | `docs/PRODUCTION-NOTEBOOK.md` | ✅ Actif (journal continu) |

## Nouveaux documents créés le 2026-05-27

| Document | Chemin | Type |
|----------|--------|------|
| Référence technique V3.1 | `docs/technical/01-technical-reference.md` | Technique développeur |
| Guide utilisateur staff | `docs/user/01-user-guide-staff.md` | Guide utilisateur |
| Référentiel IA | `docs/ai-reference/CODEBASE-REFERENCE.md` | Référence IA / récupération |
| Plan d'audit | `docs/audit/01-audit-plan.md` | Audit sécurité/conformité |

---

## Note sur la continuité opérationnelle

Le document `Versions TOWT/NOTE_TECHNIQUE_CONTINUITE_OPERATIONNELLE.md`
est le **Plan de Continuité d'Activité (PCA)** officiel. Il reste la
référence pour les spécifications module-par-module et le backlog actif.

Le nouveau document `docs/ai-reference/CODEBASE-REFERENCE.md` le complète
en apportant une vue technique approfondie orientée récupération de code
et intégration dans des infrastructures IA.
