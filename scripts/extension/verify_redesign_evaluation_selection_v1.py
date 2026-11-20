#!/usr/bin/env python3
"""Verify selection provenance/counting; source eligibility remains a documented review."""
import datetime, hashlib, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def main():
    x = json.loads((ROOT / "manifests/redesign-evaluation-selection-v1.json").read_text())
    meta = json.loads((ROOT / "results/editability-repairability-repository-metadata-v1/collection.json").read_text())["projects"][8:]
    assert len(x["rows"]) == len(meta) == 32
    for row, original in zip(x["rows"], meta):
        assert all(row[k] == original[k] for k in ("sequence", "repository", "revision"))
    selected = [r for r in x["rows"] if r["status"] == "source_qualified_selected_runtime_unqualified"]
    assert len(selected) == x["selected_slots"] == 1
    assert x["max_slots"] == 6 and x["scientific_cases"] == 0
    assert x["adapter_recipe_published"] is False and x["adapter_clock_started"] is False
    row = selected[0]
    assert row["sequence"] == 9 and row["evaluation_slot"] == 1
    assert row["eligible_text_pointers"] == ["/description", "/name"]
    assert row["runtime_qualified"] is False and row["scientific_cases"] == 0
    for name, digest in row["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    waves = [json.loads((ROOT / ("results/redesign-evaluation-source-wave%d-v1/collection.json" % i)).read_text()) for i in range(1, 7)]
    assert all(w["status"] == "source_wave_closed" for w in waves)
    records = [r for w in waves for r in w["rows"]]
    assert all(r["status"] == "collected_verified" for r in records)
    assert len(records) == len({r["path"] for r in records}) == row["scheduled_paths"] == 45
    assert sum(r["bytes"] for r in records) == row["decoded_bytes"] == 1223859
    for w in waves:
        assert w["source_phase_anchor_utc"] == row["source_phase_anchor_utc"]
    start = datetime.datetime.fromisoformat(row["source_phase_anchor_utc"])
    end = datetime.datetime.fromisoformat(row["source_phase_terminal_utc"])
    assert 0 < (end-start).total_seconds() == row["source_phase_seconds"] == x["source_phase_seconds_used"] < 7200
    assert end < datetime.datetime.fromisoformat(waves[-1]["source_phase_deadline_utc"])
    assert all(r["status"] == "source_unattempted" for r in x["rows"][1:])
    print(json.dumps({"status": "verified", "selected_source_slots": 1, "unattempted_candidates": 31, "source_files": len(records), "runtime_qualified_workflows": 0, "scientific_cases": 0}))
if __name__ == "__main__":
    main()
