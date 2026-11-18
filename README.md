# CivicLens AI

Take a photo of a problem on your street and CivicLens finds it, rates how serious it looks, and drafts a report for the right municipal department. It detects **potholes**, **road cracks** and **streetlights**.

The detection is real: three open-source object detection models run on every upload and return what they find, with boxes and confidence scores. Severity and the report are built from those detections. Gemini can optionally polish the wording, but it never decides what's in the photo.

> CivicLens never submits anything. Every report is a draft for you to check and send through your municipality's official channel.

**Live demo:** _to be added once the backend is hosted (see [Hosting](#hosting))._

## What it can and can't detect

| Problem | What CivicLens does | Department |
| --- | --- | --- |
| Potholes | Finds each pothole and rates severity from how many there are and how much of the photo they cover | Roads and Stormwater |
| Road cracks | Finds lengthwise, crosswise and alligator (fatigue) cracking. Alligator cracking ranks higher because it means the road base is failing | Roads and Stormwater |
| Streetlights not working | Finds streetlights in the photo. A photo can't show whether a light works, so **you tick "This streetlight is not working"** and the detector confirms there is a light in the picture | Electricity (public lighting) |
| Illegal dumping | Not yet. There's no openly licensed model for it, see [Limitations](#limitations) | |

A photo can show more than one problem. Each one becomes its own issue, the most severe leads the report, and the rest are listed with it.

## How it works

1. You upload a photo, with an optional location, a note, and the streetlight tick box.
2. The backend runs three models with ONNX Runtime on the CPU. Each returns boxes with a confidence score, and anything under that model's threshold is ignored. If a model boxes the same thing twice, the weaker box is dropped.
3. Each kind of problem gets its own severity rule:

   **Potholes**

   | Rule | Severity |
   | --- | --- |
   | One pothole covering under 5% of the photo | Low |
   | 2 potholes, or 5% coverage or more | Medium |
   | 3 or more potholes, or 15% coverage or more | High |
   | 40% coverage or more | Critical |

   **Cracks**

   | Rule | Severity |
   | --- | --- |
   | One lengthwise or crosswise crack | Low |
   | Any alligator cracking, 3 or more crack areas, or 15% coverage or more | Medium |
   | Alligator cracking covering 15% or more, or 3 or more alligator areas | High |

   **Streetlights:** Medium when you report the light as not working.

4. The report is written from those numbers and addressed to the department for the most severe issue. If `GEMINI_API_KEY` is set, Gemini rewrites the text more naturally. It can't change what was found, the severities, the confidences or the boxes, and if the call fails the detectors' own wording is used.
5. The frontend draws the boxes over your photo, coloured by type: red for potholes, amber for cracks, blue for streetlights.

Part of a real response (a small pothole inside a wide patch of alligator cracking):

```json
{
  "issue_type": "Road cracks",
  "severity": "High",
  "responsible_department": "Roads and Stormwater",
  "issues": [
    { "category": "crack", "issue_type": "Road cracks", "severity": "High", "confidence": 0.53, "count": 2 },
    { "category": "pothole", "issue_type": "Pothole", "severity": "Low", "confidence": 0.91, "count": 1 }
  ],
  "detections": [
    { "label": "pothole", "category": "pothole", "confidence": 0.909, "x1": 0.3746, "y1": 0.2663, "x2": 0.6283, "y2": 0.4398 },
    { "label": "alligator_crack", "category": "crack", "confidence": 0.5325, "x1": 0.5636, "y1": 0.1481, "x2": 0.9962, "y2": 0.5008 },
    { "label": "alligator_crack", "category": "crack", "confidence": 0.4171, "x1": 0.0104, "y1": 0.1675, "x2": 0.9973, "y2": 0.5755 }
  ],
  "models": ["pothole_rfdetr_nano_v4_r1", "rdd2022_rfdetr_small", "dfine_small_obj365"]
}
```

Box corners are fractions of the image size, so they can be drawn at any display size.

## The models

| | Potholes | Road cracks | Streetlights |
| --- | --- | --- | --- |
| Model | [infra-intelligence/pothole-rfdetr-nano](https://huggingface.co/infra-intelligence/pothole-rfdetr-nano) v4 | [dronefreak/rdd2022-rfdetr-small](https://huggingface.co/dronefreak/rdd2022-rfdetr-small) | [ustc-community/dfine-small-obj365](https://huggingface.co/ustc-community/dfine-small-obj365) |
| Architecture | [RF-DETR](https://github.com/roboflow/rf-detr) Nano | RF-DETR Small | [D-FINE](https://github.com/Peterande/D-FINE) Small |
| Weights licence | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Training data | Pothole photos from [RDD2022](https://doi.org/10.6084/m9.figshare.21431547.v1) (CC BY 4.0) and the [Hazels Space dataset](https://universe.roboflow.com/hazels-space/road-damage-manhole-sewer-covers) (CC BY 4.0) | [RDD2022](https://huggingface.co/datasets/dronefreak/RDD2022), road photos from six countries (CC BY-SA 4.0) | [Objects365](https://www.objects365.org/), a general dataset of 365 everyday object types. Only its "Street Lights" class is used |
| Reported accuracy | AP50 0.70; false alarms on 2% of 300 pothole-free photos | mAP50 58 to 67% per crack type | Not measured for streetlights alone |
| Input size | 384x384 | 512x512 | 640x640 |
| ONNX file | 108 MB | 114 MB | 42 MB |
| Threshold | 0.45 (the publisher's) | 0.35 | 0.50 |

Together the three files are about 265 MB. On a laptop CPU, one photo through all three takes about a second.

The crack model also has a pothole class. CivicLens ignores it, because the dedicated pothole model has far fewer false alarms.

Thanks to Infra Intelligence, dronefreak (DetectionBench) and the D-FINE authors for publishing their weights, to Roboflow for RF-DETR, and to the RDD2022 authors (Arya et al.) and the Objects365 authors (Shao et al.) for the datasets.

### How the model files are built

None of the model files are stored in this repo.

- **Potholes:** the publisher's own ONNX file is downloaded from a pinned revision on Hugging Face and checked against the SHA-256 in its release manifest.
- **Cracks and streetlights:** these are only published as PyTorch checkpoints. `backend/tools/export_models.py` downloads them from pinned revisions, converts them to ONNX, and refuses to save the file unless ONNX Runtime gives the same output as PyTorch on the same input. PyTorch is only needed for that step. The Docker image does it in a separate build stage, so the running app installs nothing heavier than ONNX Runtime.

The D-FINE graph gives wrong results under ONNX Runtime's most aggressive optimisation level, so the app runs that model one level down. The export check uses the same setting.

The test photos in `backend/tests/samples` come from Wikimedia Commons under CC0, public domain, CC BY and CC BY-SA. Authors and licences are in [`ATTRIBUTION.md`](backend/tests/samples/ATTRIBUTION.md).

## Architecture

```text
React + Vite + TypeScript              FastAPI + Pydantic
┌──────────────────────┐  multipart   ┌──────────────────────────────────┐
│ Upload / camera      │─────────────▶│ Validate image, fix rotation     │
│ Streetlight tick box │              │ Potholes:     RF-DETR Nano       │
│ Labelled boxes       │              │ Cracks:       RF-DETR Small      │
│ Report card          │◀─────────────│ Streetlights: D-FINE Small       │
└──────────────────────┘     JSON     │ Issue rules + report + optional  │
                                      │ Gemini wording                   │
                                      └──────────────────────────────────┘
```

| Path | What it does |
| --- | --- |
| `backend/app/detection/detector.py` | Runs the three models, each with its own pre- and post-processing |
| `backend/app/detection/issues.py` | Turns detections into issues with a department, severity and reason |
| `backend/app/detection/model_store.py` | Pinned model sources, download and checksum |
| `backend/tools/export_models.py` | Converts the crack and streetlight models to ONNX and checks them |
| `backend/app/services/report_service.py` | Writes the report from the issues |
| `backend/app/services/gemini_service.py` | Optional rewording with Gemini |
| `frontend/src/components/DetectionView.tsx` | Draws the labelled boxes over the uploaded photo |

## Run it locally

Backend (Python 3.12):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.detection.model_store   # pothole model, about 108 MB

# The crack and streetlight models need PyTorch once to convert them.
# Use a separate environment so the app's stays small.
python -m venv .venv-export
.venv-export/bin/pip install -r requirements-export.txt      # Windows: .venv-export\Scripts\pip
.venv-export/bin/python -m tools.export_models

uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

On Windows, put the export environment on a short path if pip fails with a "Long Path" error.

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
  -F "image=@backend/tests/samples/streetlight-durban.jpg" \
  -F "location=M17, Durban" \
  -F "streetlight_out=true"
```

### Environment variables

| Scope | Variable | Default | Purpose |
| --- | --- | --- | --- |
| Backend | `GEMINI_API_KEY` | unset | Optional. Lets Gemini reword the report |
| Backend | `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model used for wording |
| Backend | `CIVICLENS_MODEL_DIR` | `backend/models` | Where the model files are kept |
| Backend | `CIVICLENS_THRESHOLD_<MODEL_ID>` | see the table above | Override a model's threshold, e.g. `CIVICLENS_THRESHOLD_DFINE_SMALL_OBJ365=0.6` |
| Backend | `PORT` | `8080` | HTTP port |
| Frontend | `VITE_API_BASE_URL` | `http://localhost:8080` | Backend URL, set before building |

Never commit real API keys.

## Tests

```bash
cd backend && pytest -q
cd ../frontend && npm run build
```

There are 44 backend tests:

- **Real photos:** the actual models run on nine of them, covering potholes, cracks, streetlights and a clean road. They check what's found and what isn't, the severities, the departments, and that a streetlight fault is only reported when the citizen says so.
- **Rules:** unit tests cover every severity rule, the duplicate-box rule and the resize that matches PyTorch.
- **Gemini:** a test checks that Gemini can't change the detectors' facts.
- **PyTorch:** a test checks that the app never imports it.

GitHub Actions runs everything on every push. It converts the models once and caches them.

## Hosting

The backend needs a host that runs Docker with about 1 GB of memory. Serverless functions are a poor fit for 265 MB of models, so:

- **Backend:** a free Hugging Face Space using the Docker SDK. `.github/workflows/deploy-backend.yml` uploads `backend/` to the Space whenever the default branch changes, and the Space builds `backend/Dockerfile`, model conversion included.
- **Frontend:** Vercel (or Netlify), built from `frontend/`. `frontend/.env.production` points it at the Space, so no environment variable is needed in Vercel.

To switch the deployment on, add two things under the repo's **Settings → Secrets and variables → Actions**:

| Kind | Name | Value |
| --- | --- | --- |
| Secret | `HF_TOKEN` | A Hugging Face access token with write access |
| Variable | `HF_SPACE` | The Space id, e.g. `Kea-nhlapo/civiclens-api` |

Until both exist, the deploy job notes that they're missing and stops without failing. If the Space id isn't `Kea-nhlapo/civiclens-api`, update `VITE_API_BASE_URL` in `frontend/.env.production` to `https://<owner>-<space-name>.hf.space`.

A free Space goes to sleep when nobody uses it for a while, so the first request after a quiet spell takes longer while it wakes up.

## Limitations

**All categories**
- None of the models has been measured on South African roads. They can miss things, especially small, distant or poorly lit ones.
- Coverage depends on how close the camera was, so severity is a rough guide, not a measurement. An inspector should confirm it.
- Reports are drafts. Nothing is sent to a municipality.

**Potholes**
- The model was trained on a few hundred photos, mostly from Japan, Norway and the Czech Republic, taken from a car-mounted phone.
- In testing it mistook a few fallen leaves on cracked asphalt for small potholes.

**Road cracks**
- Thin cracks are easy to lose when a large photo is shrunk to the model's 512x512 input, so faint cracks are often missed.
- Crack boxes cover the whole damaged area, not the crack line itself, so coverage for alligator cracking is high by nature.
- RDD2022's fifth category (block cracks, patches and other damage) was left out of the model, so those aren't detected.

**Streetlights**
- The model can find a streetlight but can't tell whether it works. The fault always comes from the citizen.
- It sometimes mistakes power and telephone poles for streetlights.
- Objects365's licence terms aren't clear: third-party mirrors list CC BY 4.0 and some listings say non-commercial. The D-FINE weights are Apache-2.0, but check the dataset terms before any commercial use.

**Illegal dumping**
- Not detected yet. I couldn't find an openly licensed model trained on dumping in street photos. The ones that exist are AGPL (Ultralytics YOLO) or offer only a dataset or a hosted API. The next best option is an open-vocabulary model such as OWLv2 (Apache-2.0), which finds objects from a text prompt like "pile of rubbish". It's slower and less accurate than a trained detector.

## Credits and licences

The code is MIT licensed, see [LICENSE](LICENSE). The models are Apache-2.0, see [The models](#the-models). The sample photos keep their own licences, listed in `backend/tests/samples/ATTRIBUTION.md`.
