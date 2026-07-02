# CivicLens AI

CivicLens AI turns a photo of a public infrastructure problem into a polished municipal report draft in under 30 seconds. Citizens add an optional location and note; Gemini classifies the issue, estimates severity, matches a department, and drafts a report for review and manual submission.

> CivicLens AI never claims to submit a report. All output is a draft and should be checked before using an official municipal channel.

## Why it matters

Reporting a pothole, failed streetlight, blocked drain, leaking pipe, unsafe pavement, or illegal dumping often means finding the right department and translating a photo into bureaucratic language. CivicLens reduces that friction to a photo-first workflow while keeping the citizen in control.

## Architecture

```text
React + Vite + TypeScript              FastAPI + Pydantic
┌──────────────────────┐  multipart   ┌─────────────────────────┐
│ Upload / camera      │─────────────▶│ Validate image + context│
│ Demo mode            │              │ Gemini multimodal call  │
│ Animated report card │◀─────────────│ Strict JSON / fallback  │
└──────────────────────┘     JSON     └─────────────────────────┘
   Static hosting                         Google Cloud Run
```

The backend uses the current `google-genai` SDK and asks Gemini for structured JSON matching the response model. Missing credentials, network failures, and invalid model output degrade to polished demo data.

## Local backend setup

Prerequisites: Python 3.11+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export GEMINI_API_KEY="your-key"   # optional; fallback mode works without it
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

API docs are available at `http://localhost:8080/docs`.

## Local frontend setup

Prerequisites: Node.js 20+.

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`. Use **Load demo report** for an offline pitch.

## Environment variables

| Scope | Variable | Default | Purpose |
|---|---|---|---|
| Backend | `GEMINI_API_KEY` | unset | Enables live Gemini analysis |
| Backend | `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model identifier |
| Backend | `PORT` | `8080` | HTTP port used locally and by Cloud Run |
| Frontend | `VITE_API_BASE_URL` | `http://localhost:8080` | Deployed backend base URL |

Never commit real API keys. The app does not log secrets.

## Example request

```bash
curl -X POST http://localhost:8080/api/analyze-report \
  -F "image=@pothole.jpg" \
  -F "location=Corner of Main Road and 4th Avenue" \
  -F "notes=Deep pothole in the left lane"
```

## Tests and build

```bash
cd backend && pytest -q
cd ../frontend && npm run build
```

## Deploy the backend to Google Cloud Run

```bash
gcloud run deploy civiclens-ai-api \
  --source backend \
  --region africa-south1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_MODEL=gemini-3.5-flash \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest
```

Create the `GEMINI_API_KEY` Secret Manager secret first. Cloud Run injects `PORT`; the container binds to `0.0.0.0`.

## Deploy the frontend

Run `npm run build` in `frontend`; the static output is `frontend/dist`. Set `VITE_API_BASE_URL` to the Cloud Run URL **before** building.

- Vercel: import the repository, set root directory to `frontend`, build command `npm run build`, output `dist`.
- Firebase Hosting: select `frontend/dist` as the public directory and configure SPA rewrites to `/index.html`.
- Other static hosts: publish `frontend/dist` and route unknown paths to `index.html`.


### 1. Problem 

“Every day, citizens walk past potholes, broken streetlights, blocked drains, and illegal dumping. Reporting them should be simple, but people must find the right department, describe the issue formally, and navigate a municipal portal. That friction means problems go unreported.”

### 2. Solution 

“CivicLens AI turns one photo into a municipality-ready report draft in under 30 seconds. It identifies the issue, estimates urgency, recommends the responsible department, and writes a professional report. The citizen reviews it and submits it through the official channel—CivicLens never pretends submission happened.”

