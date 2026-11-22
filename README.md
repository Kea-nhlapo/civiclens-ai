# CivicLens AI

Take a photo of a problem on your street and CivicLens finds it, rates how bad it looks, and writes up a report for the municipal department that should fix it. It picks up **potholes**, **road cracks**, **streetlights** and **illegal dumping**.

The detection is real. Four open-source object detection models run on every photo and return boxes with confidence scores, and the severity and report are worked out from those boxes.

CivicLens doesn't send anything anywhere. You check the report and send it through your municipality's own channel.

**Live site:** it runs in demo mode, with six sample photos and the real models' results for each one, saved ahead of time. See [Hosting](#hosting) for why. To try your own photos, [run it locally](#run-it-locally).

## What it detects

| Problem | What CivicLens does | Department |
| --- | --- | --- |
| Potholes | Finds each pothole and rates severity from how many there are and how much of the photo they cover | Roads and Stormwater |
| Road cracks | Finds lengthwise, crosswise and alligator (fatigue) cracking. Alligator cracking ranks higher because it means the road base is failing | Roads and Stormwater |
| Streetlights not working | Finds the streetlight in the photo. A photo can't show whether a light works, so you tick "This streetlight is not working" and the model confirms there's a light in the picture | Electricity (public lighting) |
| Illegal dumping | Finds dumped rubbish, bags, rubble and old furniture with an open-vocabulary model that matches the photo against text descriptions. It's less certain than the others, see [Limitations](#limitations) | Waste Management (Solid Waste) |

One photo can show more than one problem. Each becomes its own issue, the most severe one leads the report, and the rest are listed under it.

## How it works

1. You upload a photo, with an optional location and note, and the streetlight tick box if it applies.
2. The backend runs the four models with ONNX Runtime on the CPU. Anything under a model's threshold is ignored, and if a model boxes the same thing twice the weaker box is dropped.
3. Each kind of problem has its own severity rule:

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

   **Illegal dumping:** Medium for any dumping, because it attracts more dumping and can block pavements and drains. High when it covers 40% or more of the photo or there are 3 or more separate piles.

4. The report is written from those results and addressed to the department for the most severe issue.
5. The frontend draws the boxes over your photo: red for potholes, amber for cracks, blue for streetlights and violet for dumping.

Part of a real response, for a small pothole inside a wide patch of alligator cracking:

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
  "models": ["pothole_rfdetr_nano_v4_r1", "rdd2022_rfdetr_small", "dfine_small_obj365", "owlv2_base_dumping_672"]
}
```

Box corners are fractions of the image size, so they can be drawn at any display size.

## The models

| | Potholes | Road cracks | Streetlights | Illegal dumping |
| --- | --- | --- | --- | --- |
| Model | [infra-intelligence/pothole-rfdetr-nano](https://huggingface.co/infra-intelligence/pothole-rfdetr-nano) v4 | [dronefreak/rdd2022-rfdetr-small](https://huggingface.co/dronefreak/rdd2022-rfdetr-small) | [ustc-community/dfine-small-obj365](https://huggingface.co/ustc-community/dfine-small-obj365) | [google/owlv2-base-patch16-ensemble](https://huggingface.co/google/owlv2-base-patch16-ensemble) |
| Architecture | [RF-DETR](https://github.com/roboflow/rf-detr) Nano | RF-DETR Small | [D-FINE](https://github.com/Peterande/D-FINE) Small | [OWLv2](https://arxiv.org/abs/2306.09683) Base, open-vocabulary (zero-shot) |
| Weights licence | Apache-2.0 | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Training data | Pothole photos from [RDD2022](https://doi.org/10.6084/m9.figshare.21431547.v1) (CC BY 4.0) and the [Hazels Space dataset](https://universe.roboflow.com/hazels-space/road-damage-manhole-sewer-covers) (CC BY 4.0) | [RDD2022](https://huggingface.co/datasets/dronefreak/RDD2022), road photos from six countries (CC BY-SA 4.0) | [Objects365](https://www.objects365.org/), a general dataset of 365 everyday object types. Only its "Street Lights" class is used | Google's web-scale image and text data. It was never trained on dumping: it finds whatever best matches five text prompts, such as "a pile of rubbish" and "an old mattress dumped on the street" |
| Reported accuracy | AP50 0.70; false alarms on 2% of 300 pothole-free photos | mAP50 58 to 67% per crack type | Not measured for streetlights alone | Found 9 of 13 dumping photos, with no false alarms on 13 clean ones (my own test) |
| Input size | 384x384 | 512x512 | 640x640 | 672x672 (trained at 960, see below) |
| ONNX file | 108 MB | 114 MB | 42 MB | 360 MB |
| Threshold | 0.45 (the publisher's) | 0.35 | 0.50 | 0.33 |

The four files come to about 625 MB. On a 4-core laptop CPU one photo takes about 3.5 s: about 1 s for the first three models and 2.5 s for OWLv2.

The crack model also has a pothole class. CivicLens ignores it, because the dedicated pothole model has far fewer false alarms.

Thanks to Infra Intelligence, dronefreak (DetectionBench), the D-FINE authors and Google for publishing their weights, to Roboflow for RF-DETR, and to the RDD2022 authors (Arya et al.) and the Objects365 authors (Shao et al.) for the datasets.

### How the model files are built

None of the model files are stored in this repo.

- **Potholes:** the publisher's own ONNX file is downloaded from a pinned revision on Hugging Face and checked against the SHA-256 in its release manifest.
- **Cracks, streetlights and dumping:** these are only published as PyTorch checkpoints. `backend/tools/export_models.py` downloads them from pinned revisions and converts them to ONNX. It fails unless ONNX Runtime finds the same things as PyTorch, in the same places with nearly the same scores, on a real road photo (`backend/tools/parity/`, all CC0). PyTorch is only needed for that step. The Docker image does it in a separate build stage, so the running app installs nothing heavier than ONNX Runtime.

ONNX Runtime's heavier optimisations change the D-FINE results on real photos (one streetlight scored 0.82 instead of 0.39), so the app runs that model with basic optimisations only, and the export check uses the same setting.

For OWLv2, the five text prompts are turned into embeddings once during export and stored in the ONNX file, so the text half of the model never runs on a request. OWLv2 is trained at 960x960, but that took about 5 s a photo on a laptop. At 672x672 it takes about 2.5 s and found the same dumping photos in testing. 576 was faster again but flagged a clean roundabout as dumping. Squeezing the model to 8-bit made it no faster and moved the boxes, so it stays at full precision.

The test photos in `backend/tests/samples` come from Wikimedia Commons under CC0, public domain, CC BY and CC BY-SA. Authors and licences are in [`ATTRIBUTION.md`](backend/tests/samples/ATTRIBUTION.md).

## Architecture

```text
React + Vite + TypeScript              FastAPI + Pydantic
┌──────────────────────┐  multipart   ┌──────────────────────────────────┐
│ Upload / camera      │─────────────▶│ Check the image, fix rotation    │
│ Streetlight tick box │              │ Potholes:     RF-DETR Nano       │
│ Sample photos        │              │ Cracks:       RF-DETR Small      │
│ Labelled boxes       │              │ Streetlights: D-FINE Small       │
│ Report card          │◀─────────────│ Dumping:      OWLv2 Base         │
└──────────────────────┘     JSON     │ Severity rules + report          │
                                      └──────────────────────────────────┘
```

| Path | What it does |
| --- | --- |
| `backend/app/detection/detector.py` | Runs the four models, each with its own pre- and post-processing |
| `backend/app/detection/issues.py` | Turns detections into issues with a department, severity and reason |
| `backend/app/detection/model_store.py` | Pinned model sources, download and checksum |
| `backend/app/services/report_service.py` | Writes the report from the issues |
| `backend/tools/export_models.py` | Converts the crack, streetlight and dumping models to ONNX and checks them |
| `backend/tools/make_demo_samples.py` | Runs the real backend on the sample photos and saves the results for demo mode |
| `frontend/src/components/DetectionView.tsx` | Draws the labelled boxes over the photo |
| `frontend/src/components/SamplePicker.tsx` | The "Try a sample photo" picker used in demo mode |

## Run it locally

Backend (Python 3.12):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.detection.model_store   # pothole model, about 108 MB

# The other three models need PyTorch once to convert them.
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

Open http://localhost:5173 and upload a photo. If the backend isn't running, the sample photo picker shows up instead.

Or try the API directly:

```bash
curl -X POST http://localhost:8080/api/analyze-report \
  -F "image=@backend/tests/samples/streetlight-durban.jpg" \
  -F "location=M17, Durban" \
  -F "streetlight_out=true"
```

### Settings

| Where | Variable | Default | What it does |
| --- | --- | --- | --- |
| Backend | `CIVICLENS_MODEL_DIR` | `backend/models` | Where the model files are kept |
| Backend | `CIVICLENS_THRESHOLD_<MODEL_ID>` | see the table above | Overrides a model's threshold, e.g. `CIVICLENS_THRESHOLD_DFINE_SMALL_OBJ365=0.6` |
| Backend | `PORT` | `8080` | HTTP port |
| Frontend | `VITE_API_BASE_URL` | `http://localhost:8080` | Backend URL, set before building |
| Frontend | `VITE_DEMO_MODE` | `false` (`true` in `.env.production`) | Shows only the saved sample results and never calls a backend |

## Tests

```bash
cd backend && pytest -q
cd ../frontend && npm run build
```

- **Real photos:** the actual models run on 13 photos covering potholes, cracks, streetlights, dumping and a clean road. The tests check what's found and what isn't (no dumping in any of the 9 non-dumping photos), plus the severities, the departments, and that a streetlight fault is only reported when the person says so.
- **Rules:** unit tests cover every severity rule, the duplicate-box rule and the resize that has to match PyTorch.
- **Demo samples:** a test runs the models again on the six demo photos and fails if a saved result no longer matches.
- **PyTorch:** a test checks that the app never imports it.

GitHub Actions runs all of it on every push. It converts the models once and caches them.

## Hosting

The live site is the frontend only, in demo mode. Hosting 625 MB of models on a CPU server costs money, so for now the site offers six sample photos: potholes, road cracks, a streetlight reported as not working, illegal dumping, a clean street, and a pothole inside cracking. Each result is the real backend's output for that photo, saved by `backend/tools/make_demo_samples.py` and shown through the same boxes and report as a live result. If you upload your own photo on the live site, it tells you that real detection needs the backend.

- `frontend/.env.production` sets `VITE_DEMO_MODE=true`. To point a build at a running backend, set it to `false` and set `VITE_API_BASE_URL` to the backend's URL.
- The backend runs anywhere that takes a Docker image and gives it about 2 to 3 GB of memory. `backend/Dockerfile` builds the models in its first stage and listens on `PORT` (8080 by default).
- `.github/workflows/deploy-backend.yml` can push `backend/` to a Hugging Face Docker Space. It only runs when the repo variable `DEPLOY_BACKEND` is `true`, and Docker Spaces now need a paid plan, so it's switched off.

## Limitations

**All categories**
- None of the models has been measured on South African roads. They can miss things, especially small, distant or poorly lit ones.
- Coverage depends on how close the camera was, so severity is a rough guide and an inspector should confirm it.
- Nothing is sent to a municipality. You send the report yourself.

**Potholes**
- The model was trained on a few hundred photos, mostly from Japan, Norway and the Czech Republic, taken from a car-mounted phone.
- In testing it mistook a few fallen leaves on cracked asphalt for small potholes.

**Road cracks**
- Thin cracks are easy to lose when a large photo is shrunk to 512x512, so faint cracks are often missed.
- Crack boxes cover the whole damaged area rather than the crack line, so coverage for alligator cracking is high by nature.
- RDD2022's fifth category (block cracks, patches and other damage) was left out of the model, so those aren't detected.

**Streetlights**
- The model can find a streetlight but can't tell whether it works. The fault always comes from the person reporting it.
- It sometimes mistakes power and telephone poles for streetlights.
- Objects365's licence terms aren't clear. Third-party mirrors list CC BY 4.0 and some listings say non-commercial. The D-FINE weights are Apache-2.0, but check the dataset terms before any commercial use.

**Illegal dumping**
- OWLv2 was never trained on dumping. It finds whatever looks most like the text prompts, so **expect false positives**. A pothole full of dirt scored 0.30 against "illegal dumping of rubble", just under the 0.33 threshold, and a clean roundabout crossed it when the model ran smaller. Every dumping report says the result is less certain and asks you to check the photo.
- It also misses things. In testing it found 9 of 13 dumping photos at full size and 8 of 13 once they were shrunk to 640 px. One miss was a single dumped washing machine.
- I couldn't find a permissively licensed model trained on dumping in street photos. The ones that exist are AGPL (Ultralytics YOLO) or only offer a dataset or a paid API. Training on a dataset like DroneWaste or Raven Scan would do better, but that's training work, not a download.
- The threshold was tuned on 26 photos. That's enough to set it sensibly, not enough to promise how it does on South African streets.

## Licence and credits

© 2026 Kea Nhlapo. The code is released under the MIT License, see [LICENSE](LICENSE). The models are Apache-2.0, see [The models](#the-models). The sample photos keep their own licences, listed in [`ATTRIBUTION.md`](backend/tests/samples/ATTRIBUTION.md).
