#!/bin/bash
# Global Database Cleanup (Superuser Version)

# 1. Try to load .env to get actual database names
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
elif [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
fi

# 2. Define the list of databases to clear (based on your project prefixes)
DB_LIST=(
    "${RASBHARI_POSTGRES_DB:-rasbhari_main}"
    "${EVENTS_POSTGRES_DB:-rasbhari_events}"
    "${THOUGHTS_POSTGRES_DB:-rasbhari_thoughts}"
    "${QUEUE_POSTGRES_DB:-rasbhari_queue}"
    "${NOTIFICATIONS_POSTGRES_DB:-rasbhari_notifications}"
)

echo "Starting cleanup as postgres superuser..."

# 3. Loop through each database and clear idle connections
for db in "${DB_LIST[@]}"; do
    echo "Processing $db..."
    # We connect to 'postgres' (maintenance DB) to kill connections in '$db'
    # This prevents 'too many connections' errors when trying to connect to $db itself.
    sudo -u postgres psql -d postgres -t -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
     WHERE datname = '$db' AND state = 'idle';" | grep -v "^$" | wc -l | xargs echo " -> Idle connections closed:"
done

echo "------------------------------------------------"
echo "Cleanup complete."