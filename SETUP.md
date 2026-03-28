# Rasbhari Setup Guide

Rasbhari is a modular, event-driven Application OS built on the Gabru Framework. This guide will help you set up the environment from scratch.

## 1. System Requirements

- **Python**: `3.9+`
- **PostgreSQL**: `12+` (Ensure `pg_config` is in your PATH for `psycopg2` installation)
- **OS**: Linux (Ubuntu/Debian/Raspberry Pi OS) or macOS.

## 2. Installation

```bash
# Clone the repository
git clone <your-repo-url> integrity
cd integrity

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Database Configuration

Rasbhari uses a multi-tenant database architecture. You need to create 5 distinct databases:

```sql
-- Run these as postgres superuser
CREATE DATABASE rasbhari;
CREATE DATABASE events;
CREATE DATABASE queue;
CREATE DATABASE notifications;
CREATE DATABASE thoughts;
```

## 4. Environment Setup

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

### Essential Variables to Set:
- **DB Settings**: Update `*_POSTGRES_DB`, `*_POSTGRES_USER`, and `*_POSTGRES_PASSWORD` for all 5 databases.
- **Security**: Set a strong `FLASK_SECRET_KEY`.
- **Paths**: Set `LOG_DIR` and `SERVER_FILES_FOLDER` to valid absolute paths.

## 5. First Run & User Approval

1. **Start the server**:
   ```bash
   python server.py
   ```
2. **Create your account**:
   - Navigate to `http://localhost:5000/signup`.
   - The first user created in the system is automatically considered an admin.
3. **Approval Flow**:
   - Subsequent users who sign up will see a "Pending Approval" message.
   - Admins can approve users via the database (setting `is_active = True` in the `users` table) or via the Admin dashboard (if enabled).

### Claiming Existing Events
If you have events that were created before user-scoping was enabled, run this SQL to associate them with your account:
```sql
UPDATE events SET user_id = (SELECT id FROM users WHERE username = 'your_username') WHERE user_id IS NULL;
```

## 6. Public Access (Optional)

To access your Rasbhari instance from outside your local network using ngrok:

1. Install ngrok: `brew install ngrok/ngrok/ngrok` (macOS) or follow Linux instructions.
2. Authenticate: `ngrok config add-authtoken <YOUR_TOKEN>`
3. Start tunnel: `ngrok http 5000`

## 7. Verification

### Test Event Creation
```bash
curl -X POST http://localhost:5000/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "system:ping",
    "description": "Rasbhari Heartbeat",
    "tags": "setup, test"
  }'
```

---
**Note**: Rasbhari is designed for the **Gabru Framework**. For architectural details, refer to `agents.md`.
