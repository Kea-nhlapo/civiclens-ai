"""Build the frontend's demo samples by running photos through the real backend.

The live site has no backend (hosting the models costs money), so it shows these
instead. Every result here is exactly what the models returned for that photo; nothing
is written by hand. tests/test_demo_samples.py runs the models again and fails if a
saved result no longer matches.

    python -m tools.make_demo_samples
"""

import json
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.main import analyze  # noqa: E402

OUT = BACKEND.parent / "frontend" / "public" / "samples"

# id, label, photo, whether the citizen reported a dark streetlight, credit line
SAMPLES = [
    ("potholes", "Potholes", "tests/samples/pothole-cluster.jpg", False,
     "Bache grande 1 by Nalilanii, CC BY 4.0, https://commons.wikimedia.org/wiki/File:Bache_grande_1.jpg"),
    ("cracks", "Road cracks", "tests/samples/crack-suburb.jpg", False,
     "Franklin Farm Road by Famartin, CC BY-SA 4.0, https://commons.wikimedia.org/wiki/File:2016-04-25_13_12_24_View_east_along_Franklin_Farm_Road_east_of_Old_Dairy_Road_just_before_shoulder_widening_and_repaving_begins_in_the_Franklin_Farm_section_of_Oak_Hill,_Fairfax_County,_Virginia.jpg"),
    ("streetlight", "Streetlight not working", "tests/samples/streetlight-durban.jpg", True,
     "M17 Springfield ^ Cowey Rds Durban by landagent, CC BY-SA 3.0, https://commons.wikimedia.org/wiki/File:M17_Springfield_%5E_Cowey_Rds_Durban_-_panoramio.jpg"),
    ("dumping", "Illegal dumping", "tests/samples/dumping-site.jpg", False,
     "Illegal Waste Disposal Site in Jabal Mukaber, CC0, https://commons.wikimedia.org/wiki/File:1_Illegal_Waste_Disposal_Site_in_Jerusalem%27s_Jabal_Mukaber_Neighborhood.jpg"),
    ("clean-street", "A clean street", "tools/parity/streetlights.jpg", False,
     "Approaching the OAU main gate roundabout by Eminence190, CC0, https://commons.wikimedia.org/wiki/File:Approaching_the_OAU_main_gate_roundabout_and_security_checkpoint_area.jpg"),
    ("mixed", "Pothole and cracks", "tests/samples/pothole-single.jpg", False,
     "Bache ENP1, CC0, https://commons.wikimedia.org/wiki/File:Bache_ENP1.jpg"),
]


def build() -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for sample_id, label, photo, streetlight_out, credit in SAMPLES:
        source = BACKEND / photo
        report = analyze(source.read_bytes(), "image/jpeg", None, None, streetlight_out)
        shutil.copyfile(source, OUT / f"{sample_id}.jpg")
        (OUT / f"{sample_id}.json").write_text(json.dumps(report.model_dump(), indent=1) + "\n", encoding="utf-8")
        index.append({
            "id": sample_id, "label": label, "image": f"/samples/{sample_id}.jpg", "result": f"/samples/{sample_id}.json",
            "streetlightOut": streetlight_out, "source": photo, "credit": credit,
        })
        print(f"{sample_id}: {report.issue_type} ({report.severity}), {len(report.detections)} boxes")
    (OUT / "index.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    return index


if __name__ == "__main__":
    build()
