# Backup & Restore (§48)

## Backup

```bash
make backup
# or directly:
./scripts/backup.sh
```

Writes a timestamped folder under `storage/backups/<timestamp>/` containing:

- `database.dump` (PostgreSQL, via `pg_dump -F c`) or `meza.sqlite.db`
- `uploads.tar.gz` — everything under `UPLOAD_DIR`
- `inbox.tar.gz` — everything under `INBOX_DIR`
- `env.example.snapshot` — the **example** env file only, never real secrets

`storage/backups/` is git-ignored — back these up to external/offsite
storage separately (this is intentionally out of scope for the git repo).

## Restore

```bash
make restore FILE=storage/backups/20260905_120000
# or:
./scripts/restore.sh storage/backups/20260905_120000
```

Asks for confirmation, then restores the database (`pg_restore --clean` or
a SQLite file copy) and unpacks the uploads/inbox archives. Restart MEZA
(`make dev`) afterwards.

## Recommended cadence

For a single-Mac-mini deployment, a daily cron/launchd job calling `make
backup` plus periodic copies to an external drive or NAS is sufficient
for the current scale. Revisit if/when MEZA moves to a always-on server
with more demanding RPO/RTO requirements.
