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
LLM_PROVIDER=
LLM_API_KEY=
LLM_MODEL=
QUERY_TIMEOUT_SECONDS=10
MAX_ROWS=10000
MAX_REPAIR_RETRIES=2
```

Use synthetic data for the public demo.
