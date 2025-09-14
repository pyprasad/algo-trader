#!/bin/bash
# backup.sh - Backup critical system files

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/backup_$BACKUP_DATE"

echo "📦 Creating backup: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Backup critical files
cp -r configs/ "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"
cp -r logs/ "$BACKUP_DIR/"
cp -r results/ "$BACKUP_DIR/"

# Compress backup
tar -czf "backup_$BACKUP_DATE.tar.gz" "$BACKUP_DIR/"
rm -rf "$BACKUP_DIR/"

echo "✅ Backup created: backup_$BACKUP_DATE.tar.gz"
