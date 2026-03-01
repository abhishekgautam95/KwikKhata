# KwikKhata (Phase 1 + 2 Core Backend)

Terminal-first Hinglish ledger assistant for local shopkeepers.

## Features
- Excel-backed ledger (`openpyxl`)
- Hybrid parser: rule-based + AI providers
- AI providers: `ollama` (primary) and `gemini` (fallback)
- Friendly Hinglish responses
- Manual quick commands for fast usage
- Transaction history sheet in Excel
- Auto backup rotation for DB file
- Rotating app logs (`logs/kwikkhata.log`)

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` as needed.

## Run
```bash
python3 main.py
```

## Quick commands
- `/help`
- `/all`
- `/bal <name>`
- `/add <name> <amount>`
- `/pay <name> <amount>`

## AI Config
- `AI_PROVIDER=ollama|gemini`
- `PARSER_MODE=hybrid|llm`
- `ENABLE_FALLBACK=true|false`
- `FALLBACK_PROVIDER=gemini|ollama`
- `OLLAMA_MODEL=llama3.2:latest`
- `OLLAMA_URL=http://127.0.0.1:11434/api/generate`
- `GEMINI_API_KEY=...`

## Backup Config
- `KWIKKHATA_ENABLE_BACKUP=true|false`
- `KWIKKHATA_BACKUP_DIR=backups`
- `KWIKKHATA_BACKUP_KEEP=20`

## Excel Migration
Run once for older ledgers:
```bash
python3 scripts/migrate_excel.py --file kwik_khata_db.xlsx
```

## Tests
```bash
python3 -m unittest discover -s tests -q
```
