# Deployment

## Important: localhost is NOT your deployed database

If QueryPeek is deployed to Streamlit Cloud or another cloud host, `localhost` means the machine running QueryPeek, not the user's PC.

Therefore a deployed QueryPeek cannot directly connect to a MySQL server running on an end user's laptop.

## Recommended 3-day hackathon architecture

Use two connection modes:

### Mode 1 — Demo Database (default)

Host a small synthetic MySQL database in the cloud:

```text
User Browser
     |
     v
QueryPeek on Streamlit
     |
     v
Hosted MySQL
     |
     v
Demo tables
```

A judge/user does NOT need MySQL installed.

### Mode 2 — Remote MySQL

Optionally allow an advanced user to connect to a remotely reachable MySQL server using host, port, database, username and password.

Do NOT support arbitrary local `localhost` connections from the deployed application.

## Local development

When QueryPeek and MySQL run on the same PC:

```text
QueryPeek -> localhost:3306 -> Local MySQL
```

This works because both processes are local.

## Deployment secrets

Configure these in the deployment platform, not Git:

```text
DEMO_DATABASE_HOST=
DEMO_DATABASE_PORT=3306
DEMO_DATABASE_NAME=
DEMO_DATABASE_USER=
DEMO_DATABASE_PASSWORD=
LLM_PROVIDER=gemini
GEMINI_API_KEY=
LLM_MODEL=gemini-3.6-flash
QUERY_TIMEOUT_SECONDS=10
MAX_ROWS=10000
MAX_REPAIR_RETRIES=2
```

Use synthetic data for the public demo.

## Streamlit Community Cloud checklist

1. Create a hosted MySQL database that accepts connections from Streamlit Cloud.
2. Run `demo_database/setup.sql` with an administrator account.
3. Create a dedicated database user with `SELECT` permission only on
   `querypeek_demo`.
4. Push this repository to a Git provider and create one Streamlit Community
   Cloud app using `app.py` as the entrypoint.
5. Add the keys listed below to the app's Secrets settings. Do not commit
   `.streamlit/secrets.toml` or any real `.env` file.

Required secrets:

```toml
LLM_PROVIDER = "gemini"
GEMINI_API_KEY = "..."
LLM_MODEL = "gemini-3.6-flash"

DEMO_DATABASE_HOST = "..."
DEMO_DATABASE_PORT = "3306"
DEMO_DATABASE_NAME = "querypeek_demo"
DEMO_DATABASE_USER = "querypeek_readonly"
DEMO_DATABASE_PASSWORD = "..."
```

The public app cannot use a developer's `localhost` MySQL server. A real
hosted MySQL endpoint and its network allowlist must be configured before the
public demo can execute queries.

Use the database provider's actual port in `DEMO_DATABASE_PORT`; the current
Aiven demo endpoint uses `11492`, not the default MySQL port `3306`.
