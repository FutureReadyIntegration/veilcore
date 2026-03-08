# VeilCore Runtime Paths

## Canonical Runtime

### API
Primary API entrypoint

uvicorn veilcore.veil.api:app --host 127.0.0.1 --port 9444

### Event Stream
GET /events

### Engine Control
POST /engines/{engine_id}/start
POST /engines/{engine_id}/stop
POST /engines/{engine_id}/restart
POST /engines/{engine_id}/fail

## Canonical Files

API implementation:
veilcore/veil/api.py

Desktop implementation:
scripts/veilcore_desktop.py

Event UI:
scripts/prism_events.py

## Current Branch

beta-foundation
