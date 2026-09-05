#!/usr/bin/env bash
# MEZA backup (§48): PostgreSQL dump + uploaded documents + configuration.
set -euo pipefail
cd "$(dirname "$0")/.."
source .env 2>/dev/null || true

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-./storage/backups}"
DEST="$BACKUP_DIR/$TIMESTAMP"
mkdir -p "$DEST"

echo "== MEZA backup -> $DEST =="

if [[ "${DATABASE_URL:-}" == postgresql* ]]; then
  DB_URL_NOASYNC=${DATABASE_URL/+asyncpg/}
  echo "-- Dumping PostgreSQL database..."
  pg_dump "$DB_URL_NOASYNC" -F c -f "$DEST/database.dump" \
    || echo "!! pg_dump failed — check DATABASE_URL / pg_hba.conf. Continuing with other artifacts."
else
  echo "-- SQLite database in use; copying file..."
  DB_PATH=$(echo "$DATABASE_URL" | sed -E 's#sqlite\+aiosqlite:///##')
  [[ -f "$DB_PATH" ]] && cp "$DB_PATH" "$DEST/meza.sqlite.db"
fi

echo "-- Archiving uploaded documents..."
[[ -d "${UPLOAD_DIR:-./storage/uploads}" ]] && tar -czf "$DEST/uploads.tar.gz" -C "$(dirname "${UPLOAD_DIR:-./storage/uploads}")" "$(basename "${UPLOAD_DIR:-./storage/uploads}")"

echo "-- Archiving inbox..."
[[ -d "${INBOX_DIR:-./storage/inbox}" ]] && tar -czf "$DEST/inbox.tar.gz" -C "$(dirname "${INBOX_DIR:-./storage/inbox}")" "$(basename "${INBOX_DIR:-./storage/inbox}")"

echo "-- Copying configuration (.env.example only — never the real .env with secrets)..."
cp .env.example "$DEST/env.example.snapshot"

echo "== Backup complete: $DEST =="
