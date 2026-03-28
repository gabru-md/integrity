#!/bin/bash
# Global Database Cleanup Script for Rasbhari / Integrity

# 1. Source the .env file if it exists
if [ -f .env ]; then
    echo "Sourcing .env file..."
    # This command safely sources the .env file while ignoring comments
    export $(grep -v '^#' .env | xargs)
fi

# Function to clear idle connections for a given DB
clear_db() {
    local PREFIX=$1
    local DB_VAR="${PREFIX}_POSTGRES_DB"
    local USER_VAR="${PREFIX}_POSTGRES_USER"
    local PASSWORD_VAR="${PREFIX}_POSTGRES_PASSWORD"
    local HOST_VAR="${PREFIX}_POSTGRES_HOST"
    
    # Get values from variables (with defaults)
    local DB_NAME="${!DB_VAR}"
    local DB_USER="${!USER_VAR:-postgres}"
    export PGPASSWORD="${!PASSWORD_VAR}"
    local DB_HOST="${!HOST_VAR:-localhost}"

    if [ -n "$DB_NAME" ]; then
        echo "------------------------------------------------"
        echo "Clearing idle connections for: $DB_NAME ($PREFIX)"
        
        psql -h "$DB_HOST" -U "$DB_USER" -d postgres -t -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
         WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid() AND state = 'idle';" | sed '/^\s*$/d' | wc -l | xargs echo "Connections closed:"
    fi
}

# List of prefixes from your .env.example
PREFIXES=("RASBHARI" "EVENTS" "THOUGHTS" "QUEUE" "NOTIFICATIONS")

for p in "${PREFIXES[@]}"; do
    clear_db "$p"
done

# Cleanup
unset PGPASSWORD
echo "------------------------------------------------"
echo "Done."
