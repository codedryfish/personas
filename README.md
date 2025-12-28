# personas

Persona simulation backend MVP built with FastAPI, LangGraph, and LangChain. The project favors a modular, typed, and testable architecture with SQLite-backed persistence for quick local development.

## Requirements

- Python 3.11+
- Make

## Setup

1. Create and activate the virtual environment with dependencies:

   ```bash
   make install
   ```

2. Copy the environment template and update values as needed:

   ```bash
   cp .env.example .env
   ```

3. Run the API locally:

   ```bash
   make run
   ```

## Testing and quality

```bash
make test   # run unit tests (pytest)
make lint   # run static analysis (ruff)
make fmt    # format code (ruff)
```

## Project layout

- `src/persona_sim/app/`: FastAPI application entrypoint.
- `src/persona_sim/core/`: configuration and logging setup.
- `src/persona_sim/db/`: database engine, sessions, and models.
- `src/persona_sim/api/`: API routers and dependencies.
- `src/persona_sim/schemas/`: Pydantic models.
- `src/persona_sim/sim/`: LangGraph / LangChain orchestration stubs.
- `tests/`: pytest suites.

## How to run

After installing dependencies and configuring `.env`, start the server with:

```bash
make run
```

## Example curl calls

Create a simulation run:

```bash
curl -X POST http://localhost:8000/v1/simulations \\
  -H "Content-Type: application/json" \\
  -d '{
    "scenario": {
      "id": "b5e18cb6-2f20-4f6d-a061-c3f46a45c265",
      "title": "UK compliance control rollout",
      "context": "Launching an AI assistant to streamline SMCR evidence collection for UK banking teams.",
      "deadline": "2024-11-30T17:00:00Z",
      "stressors": ["tight audit window", "multiple regulators"],
      "success_criteria": ["reduce manual reviews by 40%", "no critical audit findings"]
    },
    "personas": [
      {
        "id": "2fdab821-76d6-4c04-9a4b-6bc0099ae0b0",
        "name": "Priya Desai",
        "role": "Head of Compliance Technology",
        "sector": "Banking",
        "locale": "UK",
        "incentives": ["prove audit readiness", "shorten change cycles"],
        "fears": ["vendor lock-in", "regulatory gaps"],
        "constraints": {
          "time_per_week_minutes": 180,
          "budget_gbp": 75000,
          "ai_trust_level": 3,
          "authority_level": "high"
        },
        "communication_style": "crisp, metric-led"
      },
      {
        "id": "8db75344-5df5-4f93-9a45-7f0c6801f4c0",
        "name": "Jamie Clark",
        "role": "Compliance Analyst",
        "sector": "Banking",
        "locale": "UK",
        "incentives": ["fewer manual tasks", "clear exception handling"],
        "fears": ["false positives", "opaque guidance"],
        "constraints": {
          "time_per_week_minutes": 240,
          "budget_gbp": 5000,
          "ai_trust_level": 4,
          "authority_level": "medium"
        },
        "communication_style": "succinct tickets"
      },
      {
        "id": "4e0ad9e9-4a0a-4b59-bb61-640703ba6f6a",
        "name": "Alex Morgan",
        "role": "Shadow IT Vendor",
        "sector": "Fintech",
        "locale": "UK",
        "incentives": ["bypass change control", "sell point tools"],
        "fears": ["central oversight", "standardized controls"],
        "constraints": {
          "time_per_week_minutes": 120,
          "budget_gbp": 0,
          "ai_trust_level": 2,
          "authority_level": "low"
        },
        "communication_style": "pushy proposals"
      }
    ],
    "stimuli": [
      {
        "type": "feature",
        "content": "Adaptive SMCR evidence pack generator with audit trails.",
        "question": "What gaps remain for FCA alignment?"
      },
      {
        "type": "pricing",
        "content": "Pilot bundle at £18k for 3 squads with monthly billing."
      }
    ],
    "run_mode": "single-turn",
    "steps": 2
  }'
```

Fetch a simulation run:

```bash
curl http://localhost:8000/v1/simulations/<run_id>
```
