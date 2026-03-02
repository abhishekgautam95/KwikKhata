# KwikKhata

Terminal-first Hinglish ledger assistant for local shopkeepers.  
Built for fast udhaar/jama entry, balance lookup, and now WhatsApp-first agent automation.

## Highlights
- Pluggable ledger backends: Excel (`openpyxl`) + PostgreSQL (`psycopg`)
- Hybrid intent parser (rule-based + LLM)
- AI providers: `ollama` (primary) + `gemini` (fallback)
- Smart confirmation flow for ambiguous requests
- Transaction safety commands: `/undo`, `/recent`, `/history`
- FastAPI webhook server for WhatsApp Cloud API
- Voice note ingestion pipeline (WhatsApp media -> Whisper STT -> ledger action)
- Image/parcha scanner pipeline (Gemini Vision -> structured entries)
- Daily reminder scheduler (`vasooli` suggestion engine)
- Auto backup rotation for database file
- Backup restore utility (`scripts/restore_backup.py`)
- Webhook abuse protection (rate-limit + payload guard)
- Security env validator (`scripts/validate_env.py`)
- Dashboard analytics API (pending, aging, risk, collection trend)
- Owner response mode preference (`/mode compact|rich`)
- Versioned partner API (`/api/v1/*`) with API key auth
- Compliance endpoints (consent log, export, delete)
- Ops endpoints (`/ops/metrics`, `/ops/slo`) for SLA/SLO tracking
- Rotating logs for production-style traceability

## Table of Contents
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Run](#run)
- [Command Reference](#command-reference)
- [Configuration](#configuration)
- [Data & Backup](#data--backup)
- [Migration](#migration)
- [Testing](#testing)
- [Roadmap](#roadmap)

## Architecture
KwikKhata uses a simple modular flow:
1. `main.py` receives user input and routes command/intents.
2. `ai_parser.py` resolves intents using rules first, then AI provider fallback.
3. `database.py` persists balances and transaction history in Excel.
4. `app.py` exposes WhatsApp webhook endpoints and scheduler.
5. `services/*` handles routing, STT, vision parsing, and reminders.
6. Response layer returns concise Hinglish output with balance transitions.

## Project Structure
```text
KwikKhata/
├── main.py
├── ai_parser.py
├── database.py
├── requirements.txt
├── .env.example
├── app.py
├── config.py
├── api/
│   └── whatsapp_webhook.py
├── services/
│   ├── ledger_agent.py
│   ├── message_router.py
│   ├── reminder_engine.py
│   ├── stt_service.py
│   ├── vision_service.py
│   └── whatsapp_client.py
├── jobs/
│   └── daily_reminder_job.py
├── scripts/
│   ├── env_wizard.py
│   └── migrate_excel.py
├── tests/
│   ├── test_database.py
│   ├── test_main_commands.py
│   ├── test_parser_rules.py
│   └── test_migration.py
├── backups/
└── logs/
```

## Requirements
- Python 3.10+
- `pip`
- Optional for PostgreSQL backend:
  - PostgreSQL 14+
- Optional for local AI:
  - Ollama running on `127.0.0.1:11434`

## Quick Start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Fast `.env` setup
Use interactive wizard to fill/update API keys quickly:
```bash
python3 scripts/env_wizard.py
```

## Run
Terminal mode:
```bash
python3 main.py
```

API mode (WhatsApp webhook):
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Dashboard summary API:
```bash
curl -s "http://127.0.0.1:8000/dashboard/summary?trend_days=14" \
  -H "x-dashboard-token: $DASHBOARD_TOKEN"
```

Partner API examples:
```bash
curl -s "http://127.0.0.1:8000/api/v1/ledgers" -H "x-api-key: $PARTNER_KEY"
curl -s -X POST "http://127.0.0.1:8000/api/v1/transactions" \
  -H "x-api-key: $PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"customer_name":"Raju","amount":500}'
```

Ops/SLO:
```bash
curl -s "http://127.0.0.1:8000/ops/metrics"
curl -s "http://127.0.0.1:8000/ops/slo?max_error_rate=0.02&max_p95_ms=900"
```

## Command Reference
- `/help` -> show available commands
- `/all` -> show all pending ledgers
- `/bal <name>` -> get balance for one customer
- `/add <name> <amount>` -> add udhaar
- `/pay <name> <amount>` -> add jama (payment received)
- `/undo` -> revert last transaction
- `/recent [n]` -> latest `n` transactions (default `10`)
- `/history <name> [n]` -> latest `n` transactions for one customer (default `10`)
- `/mode compact|rich` -> response style preference for owner chat

## Configuration
All configuration lives in `.env`.

### AI
- `AI_PROVIDER=ollama|gemini`
- `FALLBACK_PROVIDER=gemini|ollama`
- `ENABLE_FALLBACK=true|false`
- `PARSER_MODE=hybrid|llm`
- `OLLAMA_MODEL=llama3.2:latest`
- `OLLAMA_URL=http://127.0.0.1:11434/api/generate`
- `GEMINI_MODEL=gemini-2.0-flash`
- `GEMINI_API_KEY=...`

### Integrations (planned-ready)
- `OPENAI_API_KEY=...`
- `WHISPER_MODEL=gpt-4o-mini-transcribe`
- `WHATSAPP_VERIFY_TOKEN=...`
- `WHATSAPP_ACCESS_TOKEN=...`
- `WHATSAPP_PHONE_NUMBER_ID=...`
- `WHATSAPP_BUSINESS_ACCOUNT_ID=...`
- `WHATSAPP_GRAPH_VERSION=v21.0`
- `WHATSAPP_API_BASE=https://graph.facebook.com`
- `WEBHOOK_RATE_LIMIT_PER_MINUTE=120`
- `WEBHOOK_RATE_LIMIT_WINDOW_SECONDS=60`
- `WEBHOOK_MAX_PAYLOAD_KB=256`
- `DASHBOARD_TOKEN=...` (optional dashboard auth header: `x-dashboard-token`)
- `OWNER_WHATSAPP_NUMBER=+91...`
- `CUSTOMER_PHONEBOOK={"Raju":"+91999...","Aditya":"+91888..."}`
- `CUSTOMER_PHONEBOOK_B64=...` (optional base64 encoded JSON phonebook)
- `PII_HASH_SALT=...` (recommended 24+ chars)
- `DEFAULT_RESPONSE_MODE=rich|compact`
- `PARTNER_API_KEYS=key1,key2`
- `WEBHOOK_SIGNATURE_SECRET=...`
- `DEFAULT_LOCALE=en-IN`
- `DEFAULT_CURRENCY=INR`
- `COMPLIANCE_STORE_FILE=logs/compliance_events.jsonl`
- `COMPLIANCE_RETENTION_DAYS=365`
- `METRICS_WINDOW_SIZE=2000`

### Reminder defaults (planned-ready)
- `REMINDER_RUN_TIME=10:00`
- `REMINDER_MIN_DAYS=15`
- `REMINDER_MIN_AMOUNT=500`
- `DEFAULT_COUNTRY_CODE=+91`

### Backup
- `KWIKKHATA_ENABLE_BACKUP=true|false`
- `KWIKKHATA_BACKUP_DIR=backups`
- `KWIKKHATA_BACKUP_KEEP=20`

### Data backend
- `DATA_BACKEND=excel|postgres`
- `KWIKKHATA_DATABASE_URL=postgresql://user:pass@host:5432/dbname` (required when backend is `postgres`)
- `KWIKKHATA_SHOP_NAME=Default Shop`

## Data & Backup
- Primary DB file: `kwik_khata_db.xlsx`
- Ledger sheet: `Khata`
- Transaction sheet: `Transactions`
- Automatic backups saved under `backups/` (configurable)

## Migration
For upgrading old ledger files:
```bash
python3 scripts/migrate_excel.py --file kwik_khata_db.xlsx
```

## Security & Ops Utilities
Validate environment before prod deploy:
```bash
python3 scripts/validate_env.py
```

Restore DB from latest backup:
```bash
python3 scripts/restore_backup.py --db kwik_khata_db.xlsx --backup-dir backups
```

## Testing
```bash
python3 -m unittest discover -s tests -q
```

## Roadmap
- Payment reminder template personalization per customer
- Persistent queue/retry layer for webhook jobs
- Multi-shop tenancy and role-based controls
- Dashboard for overdue analytics and collection trend
