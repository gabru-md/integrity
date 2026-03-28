#!/bin/bash

# Array of database prefixes used in the Gabru framework
DB_PREFIXES=("RASBHARI" "EVENTS" "THOUGHTS" "QUEUE" "NOTIFICATIONS")

# Default values for PostgreSQL if specific envs are not set
DEFAULT_PG_USER=${POSTGRES_USER:-"postgres"}
DEFAULT_PG_HOST=${POSTGRES_HOST:-"localhost"}
DEFAULT_PG_PORT=${POSTGRES_PORT:-"5432"}

echo "----------------------------------------------------------"
echo "Starting global PostgreSQL connection cleanup..."
echo "----------------------------------------------------------"

for PREFIX in "${DB_PREFIXES[@]}"; do
    # Dynamically get the DB name from environment variables
    # For example: RASBHARI_POSTGRES_DB
    DB_NAME_VAR="${PREFIX}_POSTGRES_DB"
    DB_NAME="${!DB_NAME_VAR}"
    
    # Also check the USER/HOST/PORT for this specific prefix
    DB_USER_VAR="${PREFIX}_POSTGRES_USER"
    DB_USER="${!DB_USER_VAR:-$DEFAULT_PG_USER}"
    
    DB_HOST_VAR="${PREFIX}_POSTGRES_HOST"
    DB_HOST="${!DB_HOST_VAR:-$DEFAULT_PG_HOST}"
    
    DB_PORT_VAR="${PREFIX}_POSTGRES_PORT"
    DB_PORT="${!DB_PORT_VAR:-$DEFAULT_PG_PORT}"

    if [ -n "$DB_NAME" ]; then
        echo "[+] Cleaning connections for $PREFIX (Database: $DB_NAME) on $DB_HOST:$DB_PORT..."
        
        # SQL to terminate idle connections for this specific database
        # We exclude the current connection (pg_backend_pid)
        # We target the specific database name to avoid killing connections for unrelated apps
        TERMINATE_SQL="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid() AND state = 'idle';"
        
        # Execute via psql. 
        # Note: This assumes you have .pgpass configured or no password is required for the local user.
        PGPASSWORD="${!PREFIX_POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "$TERMINATE_SQL" > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            echo "    Done."
        else
            echo "    Warning: Could not connect or clear $DB_NAME. Check credentials/permissions."
        fi
    else
        echo "[!] Skipping $PREFIX: No database name found in environment ($DB_NAME_VAR is empty)."
    fi
done

# Finally, a general check for the 'integrity' database just in case it's used elsewhere
INTEGRITY_DB="integrity"
echo "[+] Checking general '$INTEGRITY_DB' database..."
psql -h "$DEFAULT_PG_HOST" -p "$DEFAULT_PG_PORT" -U "$DEFAULT_PG_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$INTEGRITY_DB' AND pid <> pg_backend_pid() AND state = 'idle';" > /dev/null 2>&1

echo "----------------------------------------------------------"
echo "Cleanup complete."
echo "----------------------------------------------------------"
