import copy
import pytest

from lab9.gate import integrity_check

SPEC = {"metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True,
                     "threshold": {"min": 0.8}},
                    {"id": "pass_hat_5", "kind": "capability", "blocking": True}]}
ROWS = [{"item_id": item, "seed": seed, "slices": ["denial"] if item == "E-1" else [],
         "pass_rate": True} for item in ("E-1", "E-2") for seed in (11, 22)]


def valid():
    return {"manifest": {"items": 2, "seeds": [11, 22], "eval_set_sha": "x"},
            "rows": copy.deepcopy(ROWS), "metrics": {"pass_rate": 1.0, "pass_hat_5": 1.0},
            "evaluator_failures": []}


def test_valid_report_and_aggregate_without_row_column():
    report = valid()
    assert integrity_check(report, report, SPEC) == []


def test_missing_row_and_duplicate_same_count():
    base = valid(); missing = valid(); missing["rows"].pop()
    assert integrity_check(missing, base, SPEC)
    duplicate = valid(); duplicate["rows"][0] = copy.deepcopy(duplicate["rows"][1])
    assert integrity_check(duplicate, base, SPEC)


def test_cherry_picked_item_and_seed():
    base = valid(); pr = valid()
    for row in pr["rows"]:
        if row["item_id"] == "E-2": row["item_id"] = "E-3"
    assert integrity_check(pr, base, SPEC)
    pr = valid(); pr["manifest"]["seeds"] = [11, 33]
    for row in pr["rows"]:
        if row["seed"] == 22: row["seed"] = 33
    assert integrity_check(pr, base, SPEC)


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf"), "bad"])
def test_invalid_aggregate(value):
    base = valid(); pr = valid(); pr["metrics"]["pass_rate"] = value
    assert integrity_check(pr, base, SPEC)


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf"), "bad"])
def test_invalid_row_metric(value):
    base = valid(); pr = valid(); pr["rows"][0]["pass_rate"] = value
    assert integrity_check(pr, base, SPEC)
    del pr["rows"][0]["pass_rate"]
    assert integrity_check(pr, base, SPEC)


def test_failures_and_slice_change():
    base = valid(); pr = valid(); pr["evaluator_failures"] = ["grader failed"]
    assert integrity_check(pr, base, SPEC)
    pr = valid(); pr["rows"][0]["slices"] = []
    assert integrity_check(pr, base, SPEC)


@pytest.mark.parametrize("bad", [None, {}, {"manifest": {}, "rows": [], "metrics": {}},
                                 {"manifest": {"items": 2, "seeds": [11, 22]}, "rows": [None],
                                  "metrics": {}, "evaluator_failures": []}])
def test_malformed_reports_return_problems(bad):
    assert integrity_check(bad, valid(), SPEC)


RATCHET = {"eval_set_version": "v2", "metrics": [
    {"id": "pass_rate", "blocking": True, "threshold": {"min": 0.8, "no_significant_drop": True}},
    {"id": "safety", "blocking": True, "threshold": {"max": 0.2}},
    {"id": "cost", "blocking": False, "threshold": {"max_increase": 0.1}}],
    "slices": [{"name": "denial", "metric": "pass_rate", "min": 0.8,
                "no_significant_drop": True, "blocking": True}]}


def ratchet_report():
    report = valid()
    report["metrics"] = {"pass_rate": 1.0, "safety": 0.0, "cost": 1.0}
    return report


def test_ratchet_identical_stricter_added_and_reordered():
    base = ratchet_report(); spec = copy.deepcopy(RATCHET)
    assert integrity_check(base, base, spec, RATCHET) == []
    spec["metrics"][0]["threshold"]["min"] = 0.9
    spec["metrics"][1]["threshold"]["max"] = 0.1
    spec["metrics"][2]["threshold"]["max_increase"] = 0.05
    spec["slices"][0]["min"] = 0.9
    spec["metrics"].reverse()
    spec["metrics"].append({"id": "new", "blocking": False})
    spec["slices"].append({"name": "new", "metric": "pass_rate", "blocking": False})
    spec["slices"].reverse()
    assert integrity_check(base, base, spec, RATCHET) == []


@pytest.mark.parametrize("index,field,value", [(0,"min",0.7), (1,"max",0.3), (2,"max_increase",0.2)])
def test_ratchet_loosened_threshold(index, field, value):
    report = ratchet_report(); spec = copy.deepcopy(RATCHET)
    spec["metrics"][index]["threshold"][field] = value
    assert integrity_check(report, report, spec, RATCHET)
    del spec["metrics"][index]["threshold"][field]
    assert integrity_check(report, report, spec, RATCHET)


@pytest.mark.parametrize("change", ["metric_removed", "slice_removed", "metric_nonblocking", "slice_nonblocking",
                                     "metric_no_drop", "slice_no_drop", "slice_lower", "slice_missing_min"])
def test_ratchet_removed_or_weakened_rules(change):
    report = ratchet_report(); spec = copy.deepcopy(RATCHET)
    if change == "metric_removed": spec["metrics"].pop(0)
    if change == "slice_removed": spec["slices"].clear()
    if change == "metric_nonblocking": spec["metrics"][0]["blocking"] = False
    if change == "slice_nonblocking": spec["slices"][0]["blocking"] = False
    if change == "metric_no_drop": del spec["metrics"][0]["threshold"]["no_significant_drop"]
    if change == "slice_no_drop": spec["slices"][0]["no_significant_drop"] = False
    if change == "slice_lower": spec["slices"][0]["min"] = 0.7
    if change == "slice_missing_min": del spec["slices"][0]["min"]
    assert integrity_check(report, report, spec, RATCHET)


def test_ratchet_version_and_absent_base_spec():
    report = ratchet_report(); spec = copy.deepcopy(RATCHET)
    spec["metrics"][0]["threshold"]["min"] = 0.5
    assert integrity_check(report, report, spec, RATCHET)
    spec["eval_set_version"] = "v3"
    assert integrity_check(report, report, spec, RATCHET) == []
    assert integrity_check(report, report, spec) == []  # no base spec: ratchet was not checked
    del spec["eval_set_version"]
    assert integrity_check(report, report, spec, RATCHET)
