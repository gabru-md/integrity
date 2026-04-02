#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

BACKUP_DIR="${RASBHARI_BACKUP_DIR:-$ROOT_DIR/backups}"
RETENTION_DAYS="${RASBHARI_BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
TARGET_DIR="$BACKUP_DIR/$TIMESTAMP"

mkdir -p "$TARGET_DIR"

if command -v sha256sum >/dev/null 2>&1; then
  CHECKSUM_CMD=(sha256sum)
elif command -v shasum >/dev/null 2>&1; then
  CHECKSUM_CMD=(shasum -a 256)
else
  echo "Neither sha256sum nor shasum is available." >&2
  exit 1
fi

dump_database() {
  local prefix="$1"
  local label="$2"
  local db_var="${prefix}_POSTGRES_DB"
  local user_var="${prefix}_POSTGRES_USER"
  local password_var="${prefix}_POSTGRES_PASSWORD"
  local host_var="${prefix}_POSTGRES_HOST"
  local port_var="${prefix}_POSTGRES_PORT"

  local db_name="${!db_var:-}"
  local db_user="${!user_var:-}"
  local db_password="${!password_var:-}"
  local db_host="${!host_var:-localhost}"
  local db_port="${!port_var:-5432}"
  local dump_file="$TARGET_DIR/${label}.dump"

  if [[ -z "$db_name" || -z "$db_user" || -z "$db_password" ]]; then
    echo "Missing configuration for ${prefix}. Expected ${db_var}, ${user_var}, and ${password_var}." >&2
    exit 1
  fi

  echo "Backing up ${label} (${db_name})..."
  PGPASSWORD="$db_password" pg_dump \
    --format=custom \
    --no-owner \
    --host="$db_host" \
    --port="$db_port" \
    --username="$db_user" \
    --dbname="$db_name" \
    --file="$dump_file"
}

dump_database "EVENTS" "events"
dump_database "QUEUE" "queue"
dump_database "RASBHARI" "rasbhari"
dump_database "NOTIFICATIONS" "notifications"
dump_database "THOUGHTS" "thoughts"

cat >"$TARGET_DIR/manifest.json" <<EOF
{
  "created_at": "$TIMESTAMP",
  "backup_dir": "$TARGET_DIR",
  "retention_days": $RETENTION_DAYS,
  "databases": [
    {"label": "events", "name": "${EVENTS_POSTGRES_DB}", "host": "${EVENTS_POSTGRES_HOST:-localhost}", "port": "${EVENTS_POSTGRES_PORT:-5432}"},
    {"label": "queue", "name": "${QUEUE_POSTGRES_DB}", "host": "${QUEUE_POSTGRES_HOST:-localhost}", "port": "${QUEUE_POSTGRES_PORT:-5432}"},
    {"label": "rasbhari", "name": "${RASBHARI_POSTGRES_DB}", "host": "${RASBHARI_POSTGRES_HOST:-localhost}", "port": "${RASBHARI_POSTGRES_PORT:-5432}"},
    {"label": "notifications", "name": "${NOTIFICATIONS_POSTGRES_DB}", "host": "${NOTIFICATIONS_POSTGRES_HOST:-localhost}", "port": "${NOTIFICATIONS_POSTGRES_PORT:-5432}"},
    {"label": "thoughts", "name": "${THOUGHTS_POSTGRES_DB}", "host": "${THOUGHTS_POSTGRES_HOST:-localhost}", "port": "${THOUGHTS_POSTGRES_PORT:-5432}"}
  ]
}
EOF

(
  cd "$TARGET_DIR"
  "${CHECKSUM_CMD[@]}" ./*.dump > SHA256SUMS
)

ln -sfn "$TARGET_DIR" "$BACKUP_DIR/latest"

find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name "20*" -mtime +"$RETENTION_DAYS" -exec rm -rf {} +

echo "Backup complete: $TARGET_DIR"
echo "Latest symlink: $BACKUP_DIR/latest"
