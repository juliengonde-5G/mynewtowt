#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# my_TOWT — Script de sauvegarde de la base de données
# ═══════════════════════════════════════════════════════════════
#
# Usage: ./backup.sh [répertoire_de_sortie]
# Par défaut les sauvegardes vont dans ./backups/
# ═══════════════════════════════════════════════════════════════

set -e

BACKUP_DIR="${1:-$(dirname "$0")/backups}"
DB_CONTAINER="towt-db"
DB_USER="towt_admin"
DB_NAME="towt_planning"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/towt_backup_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "📦 Sauvegarde de la base de données my_TOWT..."
echo "   Container: $DB_CONTAINER"
echo "   Base:      $DB_NAME"
echo "   Fichier:   $BACKUP_FILE"
echo ""

docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl > "$BACKUP_FILE"

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Sauvegarde réussie: $BACKUP_FILE ($SIZE)"

    # Compresser
    gzip "$BACKUP_FILE"
    SIZE_GZ=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
    echo "   Compressé: ${BACKUP_FILE}.gz ($SIZE_GZ)"

    # Garder les 10 dernières sauvegardes
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/towt_backup_*.sql.gz 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 10 ]; then
        echo "   Nettoyage des anciennes sauvegardes..."
        ls -1t "$BACKUP_DIR"/towt_backup_*.sql.gz | tail -n +11 | xargs rm -f
        echo "   ✓ Conservé les 10 dernières sauvegardes"
    fi
else
    echo "❌ Échec de la sauvegarde"
    rm -f "$BACKUP_FILE"
    exit 1
fi
