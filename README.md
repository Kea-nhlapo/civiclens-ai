# CivicLens AI

Take a photo of a pothole and CivicLens finds it, rates how serious it looks, and drafts a report you can send to your municipality.

The detection is real: an open-source object detection model runs on every upload and returns the potholes it finds, with boxes and confidence scores. Severity and the report are built from those detections. Gemini can optionally polish the wording, but it never decides what's in the photo.

> CivicLens never submits anything. Every report is a draft for you to check and send through your municipality's official channel.

**Live demo:** _to be added once the backend is hosted (see [Hosting](#hosting))._

## How it works

1. You upload a road photo, with an optional location and note.
2. The backend runs **RF-DETR Nano** on it with ONNX Runtime on the CPU. The model returns every pothole it finds as a box with a confidence score. Anything under 0.45, the model's published operating threshold, is ignored.
3. If the model boxes the same pothole twice, the weaker box is dropped.
4. Severity comes from two things the photo shows: how many potholes there are, and how much of the photo they cover.

   | Rule | Severity |
   | --- | --- |
   | One pothole covering under 5% of the photo | Low |
   | 2 potholes, or 5% coverage or more | Medium |
   | 3 or more potholes, or 15% coverage or more | High |
   | 40% coverage or more | Critical |

5. The report is written from those numbers and sent to the Roads and Stormwater department. If `GEMINI_API_KEY` is set, Gemini rewrites the text more naturally. It can't change the issue type, severity, confidence or boxes, and if the call fails the detector's own wording is used.
6. The frontend draws the boxes over your photo and explains the severity.

The API response includes the raw detections. Box corners are fractions of the image size, so they can be drawn at any display size:

```json
{
  "issue_type": "Potholes",
  "severity": "High",
  "confidence": 0.81,
  "pothole_count": 4,
  "coverage": 0.0259,
  "severity_reason": "4 potholes close together, covering 3% of the photo. ...",
  "detections": [
    { "label": "pothole", "confidence": 0.8067, "x1": 0.4097, "y1": 0.6415, "x2": 0.4915, "y2": 0.7039 }
  ],
  "model": "pothole_rfdetr_nano_v4_r1",
  "analysis_source": "detector"
}
```

## The model

| | |
| --- | --- |
| Model | [infra-intelligence/pothole-rfdetr-nano](https://huggingface.co/infra-intelligence/pothole-rfdetr-nano), version 4 (`pothole_rfdetr_nano_v4_r1`) |
| Architecture | [RF-DETR](https://github.com/roboflow/rf-detr) Nano by Roboflow, fine-tuned for one class: pothole |
| Licence | Apache-2.0 (the weights), Apache-2.0 (RF-DETR) |
| Training data | Pothole images from [RDD2022](https://doi.org/10.6084/m9.figshare.21431547.v1) (Japan, Norway, Czech Republic, India; CC BY 4.0) and the [Hazels Space road damage dataset](https://universe.roboflow.com/hazels-space/road-damage-manhole-sewer-covers) on Roboflow Universe (CC BY 4.0) |
| Reported accuracy | AP50 0.70 on the publisher's test set; false alarms on 2% of 300 pothole-free road photos |
| Runtime | ONNX Runtime on CPU, input 384x384, roughly 0.2 to 0.5 s per photo on a laptop |

Thanks to Infra Intelligence for publishing the weights and a clear input/output contract, to Roboflow for RF-DETR, and to the RDD2022 authors (Arya et al.) for the dataset.

The 108 MB model file isn't stored in this repo. `backend/app/detection/model_store.py` downloads it from a pinned revision on Hugging Face and checks its SHA-256 against the model's release manifest before loading it. The Docker image downloads it at build time, and CI caches it.

The test photos in `backend/tests/samples` come from Wikimedia Commons under CC0, CC BY and CC BY-SA. Authors and licences are in [`ATTRIBUTION.md`](backend/tests/samples/ATTRIBUTION.md).

## Architecture

```text
React + Vite + TypeScript              FastAPI + Pydantic
┌──────────────────────┐  multipart   ┌──────────────────────────────┐
│ Upload / camera      │─────────────▶│ Validate image, fix rotation │
│ Boxes over the photo │              │ RF-DETR Nano (ONNX Runtime)  │
│ Report card          │◀─────────────│ Severity rules + report      │
└──────────────────────┘     JSON     │ Optional Gemini wording      │
                                      └──────────────────────────────┘
```

| Path | What it does |
| --- | --- |
| `backend/app/detection/detector.py` | Loads the model, runs it, drops duplicate boxes |
| `backend/app/detection/severity.py` | Turns detections into issue type, severity and a reason |
| `backend/app/detection/model_store.py` | Downloads and verifies the model |
| `backend/app/services/report_service.py` | Writes the report from the detections |
| `backend/app/services/gemini_service.py` | Optional rewording with Gemini |
| `frontend/src/components/DetectionView.tsx` | Draws the boxes over the uploaded photo |

## Run it locally

Backend (Python 3.12):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.detection.model_store   # downloads the model once, about 108 MB
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

API docs are at http://localhost:8080/docs.

Frontend (Node.js 20+):

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173. **Load demo (sample data)** shows a sample report without calling the backend, and it's labelled as sample data.

Try the API directly:

```bash
curl -X POST http://localhost:8080/api/analyze-report \
  -F "image=@backend/tests/samples/pothole-cluster.jpg" \
  -F "location=Main Road, Kempton Park"
```

### Environment variables

| Scope | Variable | Default | Purpose |
| --- | --- | --- | --- |
| Backend | `GEMINI_API_KEY` | unset | Optional. Lets Gemini reword the report |
| Backend | `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model used for wording |
| Backend | `CIVICLENS_DETECTION_THRESHOLD` | `0.45` | Minimum detection confidence |
| Backend | `CIVICLENS_MODEL_PATH` | `backend/models/pothole_rfdetr_nano_v4_r1.onnx` | Where the model file is kept |
| Backend | `PORT` | `8080` | HTTP port |
| Frontend | `VITE_API_BASE_URL` | `http://localhost:8080` | Backend URL, set before building |

Never commit real API keys.

## Tests

```bash
cd backend && pytest -q
cd ../frontend && npm run build
```

The backend tests run the real model on six photos: four with potholes and two clean roads. They check the number of potholes, the severity, the boxes and the report fields. Other tests cover the severity rules, the duplicate-box rule, and that Gemini can't change the detector's facts. GitHub Actions runs both on every push.

## Hosting

The backend needs a host that runs Docker with about 1 GB of memory. Serverless functions are a poor fit for a 108 MB model. The plan:

- **Backend:** a free Hugging Face Space using the Docker SDK, built from `backend/Dockerfile`.
- **Frontend:** Vercel or Netlify, with `VITE_API_BASE_URL` set to the Space's URL.

A free Space goes to sleep when nobody uses it for a while, so the first request after a quiet spell takes longer.

## Limitations

- It only detects potholes. Cracks, broken streetlights, blocked drains and dumping aren't detected, and a photo of them comes back as "No pothole detected".
- The model was trained on a few hundred images, mostly from Japanese, Norwegian and Czech roads, taken from a car-mounted phone. It hasn't been measured on South African roads, at night, or in rain, and it can miss small or distant potholes.
- Coverage depends on how close the camera was, so severity is a rough guide, not a measurement. An inspector should confirm it.
- Reports are drafts. Nothing is sent to a municipality.

## Credits and licences

The detection model and RF-DETR are Apache-2.0, see [The model](#the-model). The sample photos keep their own licences, listed in `backend/tests/samples/ATTRIBUTION.md`.
