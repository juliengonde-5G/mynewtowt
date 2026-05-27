# Guide utilisateur — Staff NEWTOWT
# Plateforme mynewtowt V3.1

> **Audience** : Collaborateurs internes NEWTOWT (tous rôles)
> **Date** : 2026-05-27 | **Version** : 3.1

---

## 1. Connexion et sécurité

### 1.1 Accès à la plateforme

URL de production : **https://my.newtowt.eu**

1. Entrer votre **email** et **mot de passe**
2. Si MFA activé : saisir le code à 6 chiffres de votre application d'authentification
   (Google Authenticator, Authy, etc.)
3. Le rôle `administrateur` a le MFA **obligatoire**

**Durée de session :**
- Rôles bureau (opération, commercial, etc.) : **8 heures**
- Rôles embarqués (marins, manager_maritime) : **14 jours** (pour les traversées sans connectivité stable)

### 1.2 Premier accès

Lors du premier accès, vous serez redirigé vers le changement de mot de passe.
Choisir un mot de passe d'au moins 12 caractères avec majuscule, chiffre et symbole.

### 1.3 Configuration MFA (recommandé pour tous)

1. Aller dans **Mon compte** (menu en haut à droite)
2. Section **Sécurité → Authentification à deux facteurs**
3. Scanner le QR code avec votre appli d'auth
4. Sauvegarder les **codes de secours** (impression recommandée)

---

## 2. Navigation générale

L'interface est organisée en deux niveaux :
- **Sidebar gauche** : navigation entre les modules
- **Topbar** : compte utilisateur, notifications, horloge

Les modules disponibles dépendent de votre **rôle**. Les items grisés
signifient que vous n'avez pas accès à ce module.

---

## 3. Module Planning

**Accès requis :** rôle `operation`, `armement`, `technique`, `commercial`,
`manager_maritime`, `marins`, `data_analyst`, ou `administrateur`

### 3.1 Vue d'ensemble

Le planning affiche les **legs** (segments de voyage) de tous les navires
sur une vue Gantt ou tableau selon votre préférence.

### 3.2 Créer un leg

1. Cliquer sur **+ Nouveau leg** (nécessite permission Modify)
2. Choisir le navire, le port de départ, le port d'arrivée
3. Renseigner les dates ETD/ETA
4. Enregistrer → le `leg_code` est généré automatiquement

**Format leg_code** : `1CFRBR6` = séquence 1, navire CF, France → Brésil, année 6

### 3.3 Partager le planning

Le planning peut être partagé en lecture seule via un lien tokenisé (90 jours).
Bouton **Partager** sur la vue planning.

---

## 4. Module Commercial

**Accès requis :** `commercial` (CMS), `operation` (CM), `manager_maritime` (CM)

### 4.1 Clients

Création et gestion des fiches clients. Chaque client peut être lié à un
compte Pipedrive (CRM) via l'identifiant Pipedrive.

### 4.2 Grilles tarifaires

Les grilles définissent les tarifs par route, type de cargo, poids/volume.
Une grille peut être assignée à un client spécifique ou être générique.

### 4.3 Offres commerciales

Générer une offre PDF depuis une grille pour un client.
L'offre est valable une durée configurable et peut être convertie en ordre.

### 4.4 Ordres

Un ordre = un engagement de transport confirmé.
L'ordre peut être assigné à un ou plusieurs legs.

---

## 5. Module Cargo / Packing List

**Accès requis :** `cargo` (C/CM/CMS selon rôle)

### 5.1 Gestion des packing lists

Chaque booking client génère une packing list. Les étapes :
1. **Draft** : création par l'opérationnel ou l'expéditeur
2. **Submitted** : soumise par l'expéditeur via le portail
3. **Locked** : validée et verrouillée avant chargement

### 5.2 Portail expéditeur /p/{token}

Un lien de portail est généré automatiquement pour chaque packing list.
L'expéditeur peut via ce portail (sans compte) :
- Renseigner les détails colisage
- Uploader des documents
- Échanger des messages avec l'équipe

Le token est valable **90 jours** et protège l'accès sans nécessiter de compte.

### 5.3 Documents cargo

Depuis la vue détail d'une packing list, générer en PDF :
- **Bill of Lading** (BL)
- **Notice of Readiness** (NOR)
- **Mate's Receipt**
- **Letter of Protest** (LOP)

---

## 6. Module Escale (Port Call)

**Accès requis :** `escale` (C/CMS selon rôle)

### 6.1 Vue d'ensemble

L'escale regroupe toutes les opérations portuaires d'un leg :
- Arrivée navire (ATA)
- Opérations de chargement/déchargement
- Vacations dockers
- Départ (ATD)

### 6.2 Statement of Facts (SOF)

Le SOF est la chronologie officielle de l'escale. Chaque événement est
horodaté et peut être signé numériquement par le commandant.

Exporter en PDF via le bouton **Exporter SOF**.

### 6.3 Verrouillage escale

Une escale peut être verrouillée pour empêcher toute modification
une fois le navire parti. Permission S (Suppress) requise.

---

## 7. Module Captain / Onboard

**Accès requis :** `captain` (C/CM/CMS selon rôle)

Ce module est conçu pour les **marins embarqués** et les opérations.

### 7.1 Navigation

- **Noon reports** : rapport journalier de position et consommation
- **Watch logs** : journal des quarts
- **Checklists bord** : checklists pré-départ

### 7.2 Messagerie bord

Communication sécurisée entre le navire et l'équipe à terre.
Mentions possibles avec @nom.

### 7.3 Clôture de voyage

Workflow de clôture en 3 étapes :
1. Commandant soumet la clôture
2. Opération revoit
3. Administration approuve

---

## 8. Module Équipage (Crew)

**Accès requis :** `crew` (C/CM/CMS selon rôle)

### 8.1 Fiches marins

Chaque marin a une fiche avec :
- Informations personnelles et contractuelles
- Certifications (STCW, etc.) avec dates d'expiration
- Historique des affectations

### 8.2 Affectations

Assigner un marin à un leg avec sa fonction à bord.

### 8.3 Compliance Schengen

Vue de conformité automatique : les marins hors-Schengen ont un quota
de **90 jours sur 180 jours** dans l'espace Schengen.
La plateforme calcule et affiche les jours restants.

### 8.4 Calendrier

Vue calendrier des présences par navire.

---

## 9. Module Stowage (Plan de chargement)

**Accès requis :** `cargo` (CM)

### 9.1 Création d'un plan

Le plan de chargement répartit les unités cargo dans les **18 zones** du navire.
L'algorithme glouton propose une répartition optimisée (poids, stabilité).

### 9.2 Contraintes

- Limite de poids par zone
- Contraintes de matières dangereuses
- Compatibilité entre lots de cargo

---

## 10. Module Claims

**Accès requis :** `claims` (C/CM/CMS selon rôle)

### 10.1 Workflow réclamation

6 statuts : `new` → `under_review` → `investigation` → `resolution` → `closed` / `rejected`

Chaque changement de statut est tracé dans la timeline de la réclamation.

### 10.2 Documents

Joindre des photos, expertises, correspondances à la réclamation.

---

## 11. Module MRV

**Accès requis :** `mrv` (CM)

### 11.1 Saisie des données

Chaque traversée génère des données MRV (Monitoring, Reporting, Verification
selon la réglementation UE sur les émissions des navires).

Saisir pour chaque leg :
- Consommation fuel (MDO, HFO, etc.)
- Distance parcourue
- Temps en mer

### 11.2 Export DNV

Exporter les données au format CSV compatible avec DNV (société de classification)
pour la vérification annuelle.

---

## 12. Module Finance

**Accès requis :** `finance` (CMS pour data_analyst)

### 12.1 LegFinance

Données financières par leg : recettes, OPEX (coût journalier × durée),
marge brute.

### 12.2 Paramètres OPEX

Configurer le coût journalier d'exploitation par navire.
Ces paramètres sont utilisés automatiquement dans le calcul LegFinance.

### 12.3 Configuration portuaire

Frais portuaires par port (pilotage, remorquage, droits de port, agents, etc.).

---

## 13. Module KPI

**Accès requis :** `kpi` (C)

Tableaux de bord de performance :
- **Taux de remplissage** par leg/vessel
- **On-time performance** (ETD vs ATD, ETA vs ATA)
- **Émissions CO₂** par tonne-nautique
- **Délais escale** vs standard

---

## 14. Module Analytics

**Accès requis :** `analytics` (C/CM selon rôle)

3 dashboards :
1. **Exécutif** : vue d'ensemble revenues, voyages, CO₂
2. **Commercial** : bookings, clients actifs, conversion, recettes
3. **Opérations** : ponctualité, escales, temps de traversée

---

## 15. Module Tickets Escale

**Accès requis :** `tickets` (C/CM/CMS selon rôle)

Kanban à 4 colonnes : **Nouveau** → **En cours** → **En attente** → **Résolu**

**Niveaux de priorité :**
- P1 (rouge) : critique, impact sur chargement/départ
- P2 (orange) : important, SLA 4h
- P3 (vert) : normal, SLA 24h

---

## 16. Module Caisse Bord (Cashbox)

**Accès requis :** `captain` (C/CM)

Gestion des caisses à bord en EUR, USD et VND.
Mouvements enregistrés par catégorie (provisions, carburant, frais portuaires...).
Clôture journalière avec solde et justificatifs.

---

## 17. Chat Kairos AI

**Accès requis :** `chat` (C/CM selon rôle)

L'assistant IA **Kairos** répond aux questions sur les données de la plateforme :
- "Où est le navire Anemos ?"
- "Quels bookings sont confirmés pour le leg BRFR7 ?"
- "Récapitule l'escale de Fécamp du 15 mai"

L'IA n'a accès qu'aux données autorisées pour votre rôle.
Elle détecte et refuse les tentatives de manipulation.

---

## 18. Administration

**Accès requis :** rôle `administrateur` uniquement (sauf admin/C pour manager_maritime)

### 18.1 Gestion des utilisateurs

- Créer/modifier/désactiver des comptes staff
- Assigner les rôles
- Forcer un changement de mot de passe
- Voir l'historique de connexion

### 18.2 Journal d'activité

Historique complet de toutes les actions sur la plateforme.
Filtrable par module, utilisateur, date, type d'action.
Ce journal est **immuable** (append-only).

### 18.3 Tableau de bord sécurité

- Tentatives de connexion échouées
- Alertes rate-limit
- Sessions actives

### 18.4 Mode maintenance

Active une page de maintenance pour les utilisateurs extérieurs.
L'accès staff reste fonctionnel.

---

## 19. Espace client — Plateforme /me

Les **clients B2B** ont leur propre espace accessible via `/me/login`.

Fonctionnalités disponibles pour les clients :
- **Tableau de bord** : état des réservations en cours
- **Réservation en ligne** : wizard 3 étapes (itinéraire → détails → confirmation)
- **Suivi de traversée** : carte en temps réel + timeline statuts
- **Documents** : BL, factures, certificats CO₂, upload pièces
- **Messagerie** : échanges avec l'équipe NEWTOWT
- **Factures** : historique et téléchargement PDF
- **Certificats Anemos** : certificats CO₂ pour chaque traversée

---

## 20. Touches pratiques

| Raccourci | Action |
|-----------|--------|
| `Ctrl+K` | Recherche rapide (si activée) |
| `Échap` | Fermer les modales |
| Clic hors modal | Fermer la modale |

**Notifications** : le badge cloche en topbar affiche les alertes non lues.
Cliquer pour voir le détail.

**Horloge** : l'horloge en sidebar affiche l'heure locale ET l'heure UTC.
Les dates et heures dans la plateforme sont toujours en heure locale
avec la timezone affichée.

---

## 21. Bonnes pratiques

- **Sécurité** : ne jamais partager vos identifiants. Chaque compte est nominatif.
- **Déconnexion** : utilisez toujours le bouton Déconnexion (pas simplement fermer l'onglet).
- **Données sensibles** : les emails des clients sont partiellement masqués dans les logs d'audit.
- **Upload de fichiers** : formats acceptés = PDF, JPEG, PNG, DOCX, XLSX. Taille max 10 Mo.
- **Support** : en cas de problème, créer un ticket P2 dans le module Tickets
  ou contacter ops@newtowt.eu.
