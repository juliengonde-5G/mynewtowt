#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# my_TOWT — Script de déploiement pour VPS OVH
# ═══════════════════════════════════════════════════════════════
#
# Usage:
#   1. cd /home/ubuntu/mytowt
#   2. chmod +x deploy.sh
#   3. ./deploy.sh
#
# Prérequis:
#   - Docker + Docker Compose installés sur le VPS
#   - Accès SSH au VPS
# ═══════════════════════════════════════════════════════════════

set -e

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="towt-app-v2"
DB_NAME="towt-db"

echo "╔═══════════════════════════════════════════════════╗"
echo "║          my_TOWT — Déploiement                   ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# ── 1. Vérifier Docker ──
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

echo "✓ Docker et Docker Compose détectés"
echo ""

# ── 2. Configuration .env ──
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    echo "⚙ Création du fichier .env à partir de .env.example..."
    cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"

    # Générer une SECRET_KEY aléatoire
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
                 openssl rand -hex 32 2>/dev/null || \
                 head -c 64 /dev/urandom | od -An -tx1 | tr -d ' \n' | head -c 64)

    if [ -n "$SECRET_KEY" ]; then
        sed -i "s/change-me-to-a-random-64-char-string/$SECRET_KEY/" "$DEPLOY_DIR/.env"
        echo "  ✓ SECRET_KEY générée automatiquement"
    else
        echo "  ⚠ Veuillez modifier SECRET_KEY manuellement dans .env"
    fi
    echo ""
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║  IMPORTANT: Vérifiez et modifiez .env       ║"
    echo "  ║  avant de continuer si nécessaire.          ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo ""
    read -p "  Appuyez sur Entrée pour continuer (ou Ctrl+C pour annuler)..."
    echo ""
else
    echo "✓ Fichier .env existant détecté"
fi

# ── 3. Vérifier si des containers existent déjà ──
EXISTING_APP=$(docker ps -aq -f name="$APP_NAME" 2>/dev/null)
EXISTING_DB=$(docker ps -aq -f name="$DB_NAME" 2>/dev/null)

if [ -n "$EXISTING_APP" ] || [ -n "$EXISTING_DB" ]; then
    echo "⚠ Des containers existants ont été détectés:"
    [ -n "$EXISTING_APP" ] && echo "  - $APP_NAME"
    [ -n "$EXISTING_DB" ] && echo "  - $DB_NAME"
    echo ""
    read -p "Voulez-vous les arrêter et les remplacer ? (o/N) " REPLY
    if [[ "$REPLY" =~ ^[oOyY]$ ]]; then
        echo "  Arrêt des containers existants..."
        docker stop "$APP_NAME" "$DB_NAME" 2>/dev/null || true
        docker rm "$APP_NAME" "$DB_NAME" 2>/dev/null || true
        echo "  ✓ Containers supprimés"
    else
        echo "Déploiement annulé."
        exit 0
    fi
    echo ""
fi

# ── 4. Build et démarrage ──
echo "🔨 Construction de l'image Docker..."
cd "$DEPLOY_DIR"

# Détecter docker compose v2 vs docker-compose v1
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

$COMPOSE_CMD build --no-cache
echo "✓ Image construite"
echo ""

echo "🚀 Démarrage des services..."
$COMPOSE_CMD up -d
echo ""

# ── 5. Attendre que la DB soit prête ──
echo "⏳ Attente de la base de données..."
for i in $(seq 1 30); do
    if docker exec "$DB_NAME" pg_isready -U towt_admin &>/dev/null; then
        echo "✓ Base de données prête"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "❌ Timeout: la base de données ne répond pas"
        exit 1
    fi
    sleep 1
done
echo ""

# ── 6. Exécuter les migrations ──
if [ -f "$DEPLOY_DIR/migration.sql" ]; then
    echo "📦 Exécution des migrations SQL..."
    docker cp "$DEPLOY_DIR/migration.sql" "$DB_NAME":/tmp/migration.sql
    docker exec "$DB_NAME" psql -U towt_admin -d towt_planning -f /tmp/migration.sql 2>&1 || true
    echo "✓ Migrations exécutées"
    echo ""
fi

# ── 7. Permissions fichiers statiques ──
echo "📁 Configuration des permissions..."
docker exec "$APP_NAME" chmod -R 755 /app/app/static/ 2>/dev/null || true
echo "✓ Permissions configurées"
echo ""

# ── 8. Vérification ──
echo "🔍 Vérification des services..."
sleep 2

APP_STATUS=$(docker inspect -f '{{.State.Status}}' "$APP_NAME" 2>/dev/null)
DB_STATUS=$(docker inspect -f '{{.State.Status}}' "$DB_NAME" 2>/dev/null)

if [ "$APP_STATUS" = "running" ] && [ "$DB_STATUS" = "running" ]; then
    echo "✓ $APP_NAME: $APP_STATUS"
    echo "✓ $DB_NAME: $DB_STATUS"
    echo ""
    echo "╔═══════════════════════════════════════════════════╗"
    echo "║  ✅ Déploiement réussi !                         ║"
    echo "║                                                   ║"
    echo "║  URL: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')  ║"
    echo "║  Login: admin / towt2025                         ║"
    echo "║                                                   ║"
    echo "║  Commandes utiles:                               ║"
    echo "║  - Logs:     docker logs -f $APP_NAME     ║"
    echo "║  - Restart:  docker restart $APP_NAME     ║"
    echo "║  - Stop:     docker-compose down                 ║"
    echo "╚═══════════════════════════════════════════════════╝"
else
    echo "❌ Problème détecté:"
    echo "  $APP_NAME: ${APP_STATUS:-non trouvé}"
    echo "  $DB_NAME: ${DB_STATUS:-non trouvé}"
    echo ""
    echo "Consultez les logs: docker logs $APP_NAME"
    exit 1
fi
