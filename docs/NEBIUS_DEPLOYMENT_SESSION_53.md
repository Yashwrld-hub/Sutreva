# Sutreva Session 53 — Nebius Deployment Architecture

## Purpose

Session 53 makes the existing Sutreva application deployable as a container on a
Nebius AI Cloud compute target while keeping inference on Nebius Token Factory.
The application remains a normal Streamlit app; no inference credential is baked
into the image.

## Runtime architecture

```text
Browser
  |
  v
Sutreva Streamlit container
  |
  +--> PDF/evidence/audit engine
  +--> human review + feedback + evaluation
  |
  +--> ModelProvider
          |
          v
      Nebius Token Factory
          |
          v
      NVIDIA Nemotron
```

Nebius Token Factory exposes an OpenAI-compatible inference API. Sutreva uses the
standard `openai` client with a configurable base URL and model name. This keeps the
provider seam from Session 44 while allowing deployment-specific configuration.

## Configuration

Required:

- `NEBIUS_API_KEY`

Optional:

- `NEBIUS_API_BASE_URL` — defaults to `https://api.tokenfactory.nebius.com/v1/`
- `NEBIUS_MODEL_NAME` — defaults to `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`
- `NEBIUS_REQUEST_TIMEOUT_S` — defaults to `90`
- `SUTREVA_MODEL_PROVIDER` — defaults to `nebius_nemotron`
- `SUTREVA_ENV` — defaults to `development`; use `production` in deployment

Never commit `.env` or a real API key.

## Local container rehearsal

From the repository root:

```bash
cp .env.example .env
# add NEBIUS_API_KEY

docker compose -f deploy/nebius/docker-compose.yml up --build
```

Then open `http://localhost:8501`.

## Preflight

Offline:

```bash
python scripts/nebius_preflight.py
```

Live model-catalog verification:

```bash
python scripts/nebius_preflight.py --live
```

The live preflight verifies that the configured API key can see the configured
model. It does not run a paid inference request.

## Nebius deployment pattern

The container is suitable for a Nebius AI Cloud VM or containerized compute
workflow. The repository does not assume a specific orchestration product, so the
same image can be moved from a local Docker rehearsal to a Nebius-managed runtime.

## Hackathon demo discipline

The built-in `Use sample` button uses synthetic sample documents only. A hackathon
demo should clearly label a run as either:

- **Live** — real document + live Nebius Token Factory/Nemotron request
- **Replay** — deterministic local/sample data; no model call

Do not present a replay as a live model invocation.

## Three-minute demo path

1. Landing page → **Open audit workspace**.
2. Select the centrifugal-pump template.
3. Use a synthetic sample or prepared OEM document.
4. Run the deterministic audit with Nemotron reasoning enabled.
5. Show one field with source evidence.
6. Show an engineering exception and recommended action.
7. Open Review Queue and record the reviewer disposition.
8. Show the evaluation/feedback path.
9. Close by showing the runtime as **Nebius Token Factory + NVIDIA Nemotron**.
