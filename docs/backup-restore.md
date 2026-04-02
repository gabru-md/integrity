# Backup And Restore

This is the recommended backup and restore workflow for a Raspberry Pi-hosted Rasbhari with PostgreSQL running outside containers.

It is designed around the current Rasbhari architecture:

- five PostgreSQL databases
- a Pi-hosted app server
- remote access through Tailscale
- operator recovery primarily inside Rasbhari, but backup and restore outside Rasbhari

Backups stay outside the product on purpose. Rasbhari can help you observe and recover product-level issues, but database backup and restore are still infrastructure concerns.

## What Should Be Backed Up

At minimum, back up all five Rasbhari PostgreSQL databases:

- `rasbhari`
- `events`
- `queue`
- `notifications`
- `thoughts`

If you want a full disaster-recovery path, also preserve:

- your `.env`
- your `systemd` service units
- uploaded files from `SERVER_FILES_FOLDER`
- logs only if you want operator history

## Recommended Default

Use the bundled script:

```bash
./scripts/backup_rasbhari_postgres.sh
```

It will:

- load the current `.env`
- back up all five PostgreSQL databases
- write custom-format dump files
- generate a `manifest.json`
- generate `SHA256SUMS`
- maintain a `latest` symlink
- prune old backup directories based on retention

By default it writes backups to:

```text
./backups
```

For Raspberry Pi use, set an explicit backup location in `.env`:

```bash
RASBHARI_BACKUP_DIR=/var/backups/rasbhari
RASBHARI_BACKUP_RETENTION_DAYS=14
```

## Environment Variables

- `RASBHARI_BACKUP_DIR`
- `RASBHARI_BACKUP_RETENTION_DAYS`
- `ENV_FILE` optionally overrides which env file the script loads

The script expects the normal PostgreSQL env variables already used by Rasbhari:

- `EVENTS_POSTGRES_*`
- `QUEUE_POSTGRES_*`
- `RASBHARI_POSTGRES_*`
- `NOTIFICATIONS_POSTGRES_*`
- `THOUGHTS_POSTGRES_*`

## Backup Layout

Each backup run creates a timestamped directory like:

```text
/var/backups/rasbhari/20260402-231500/
```

That directory contains:

- `events.dump`
- `queue.dump`
- `rasbhari.dump`
- `notifications.dump`
- `thoughts.dump`
- `manifest.json`
- `SHA256SUMS`

And the backup root also keeps:

```text
/var/backups/rasbhari/latest
```

pointing to the newest backup.

## Recommended Schedule

For a personal Pi-hosted Rasbhari, the practical schedule is:

- nightly automated backup
- one manual backup before upgrades or schema-heavy work

Example cron entry:

```cron
15 3 * * * cd /home/pi/integrity && ./scripts/backup_rasbhari_postgres.sh >> /var/log/rasbhari-backup.log 2>&1
```

If you prefer `systemd`, the command can be wrapped in a dedicated oneshot service and timer.

## Backup Verification

A backup is not trustworthy unless it is checked.

After each run, verify:

1. the latest backup directory exists
2. all five `.dump` files exist
3. `SHA256SUMS` exists
4. checksums verify cleanly

Example:

```bash
cd /var/backups/rasbhari/latest
sha256sum -c SHA256SUMS
```

On macOS systems that do not ship `sha256sum`, use:

```bash
shasum -a 256 -c SHA256SUMS
```

You should also periodically test a real restore on a non-production PostgreSQL instance. A backup that has never been restored is only partially trusted.

## Restore Workflow

The restore flow is intentionally explicit. This is not a one-click in-product action.

### 1. Stop Rasbhari Writes

Before an in-place restore, stop the Rasbhari server and any queue processors that may still write:

- stop the Rasbhari `systemd` service
- stop any separately managed workers if you run them outside the main server process

Do not restore while the app is actively writing.

### 2. Choose The Backup

Pick a specific backup directory, for example:

```text
/var/backups/rasbhari/20260402-231500
```

Verify the checksums before restoring:

```bash
cd /var/backups/rasbhari/20260402-231500
sha256sum -c SHA256SUMS
```

### 3. Restore Each Database

Rasbhari uses custom-format dumps, so restore with `pg_restore`.

Example restore for the main Rasbhari database:

```bash
PGPASSWORD="$RASBHARI_POSTGRES_PASSWORD" pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --host="$RASBHARI_POSTGRES_HOST" \
  --port="$RASBHARI_POSTGRES_PORT" \
  --username="$RASBHARI_POSTGRES_USER" \
  --dbname="$RASBHARI_POSTGRES_DB" \
  /var/backups/rasbhari/20260402-231500/rasbhari.dump
```

Repeat the same pattern for:

- `events.dump`
- `queue.dump`
- `notifications.dump`
- `thoughts.dump`

Mapping:

- `events.dump` -> `EVENTS_POSTGRES_DB`
- `queue.dump` -> `QUEUE_POSTGRES_DB`
- `rasbhari.dump` -> `RASBHARI_POSTGRES_DB`
- `notifications.dump` -> `NOTIFICATIONS_POSTGRES_DB`
- `thoughts.dump` -> `THOUGHTS_POSTGRES_DB`

### 4. Restart Rasbhari

After restore:

1. start the Rasbhari service again
2. log in to `/admin`
3. check:
   - server availability
   - process runtime
   - queue drift
   - dependency status
4. verify that `/` and `/dashboard` load correctly

### 5. Reconcile Queue State If Needed

If the restore rolls queue state backward relative to prior runtime behavior, use the admin `Processes` page to:

- replay from `0`
- jump to latest
- restart processors

That is one reason the product-level recovery controls and the backup workflow belong together.

## Trusted Workflow For Pi Remote Use

For a Raspberry Pi setup that you want to rely on remotely, the safe minimum is:

1. nightly backup job
2. explicit backup directory on persistent storage
3. periodic checksum verification
4. at least one tested restore on a non-production database
5. clear operator notes for how to stop the service and restore

That is the difference between "I have dumps somewhere" and "this setup is actually safe to rely on."
