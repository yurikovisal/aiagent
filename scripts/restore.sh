#!/usr/bin/env bash
# MEZA restore (§48): restores a backup produced by scripts/backup.sh.
# Usage: scripts/restore.sh storage/backups/<timestamp>
set -euo pipefail
cd "$(dirname "$0")/.."
source .env 2>/dev/null || true

SRC="${1:?Usage: scripts/restore.sh <backup-directory>}"
[[ -d "$SRC" ]] || { echo "Backup directory not found: $SRC"; exit 1; }

echo "== Restoring MEZA from $SRC =="
read -r -p "This will overwrite the current database and storage. Continue? [y/N] " CONFIRM
[[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]] || { echo "Aborted."; exit 1; }

if [[ -f "$SRC/database.dump" && "${DATABASE_URL:-}" == postgresql* ]]; then
  DB_URL_NOASYNC=${DATABASE_URL/+asyncpg/}
  echo "-- Restoring PostgreSQL database..."
  pg_restore --clean --if-exists -d "$DB_URL_NOASYNC" "$SRC/database.dump"
elif [[ -f "$SRC/meza.sqlite.db" ]]; then
  DB_PATH=$(echo "$DATABASE_URL" | sed -E 's#sqlite\+aiosqlite:///##')
  cp "$SRC/meza.sqlite.db" "$DB_PATH"
fi

[[ -f "$SRC/uploads.tar.gz" ]] && tar -xzf "$SRC/uploads.tar.gz" -C "$(dirname "${UPLOAD_DIR:-./storage/uploads}")"
[[ -f "$SRC/inbox.tar.gz" ]] && tar -xzf "$SRC/inbox.tar.gz" -C "$(dirname "${INBOX_DIR:-./storage/inbox}")"

echo "== Restore complete. Restart MEZA (make dev) to pick up the restored data. =="
