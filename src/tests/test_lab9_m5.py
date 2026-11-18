import copy

from lab9.gate import slice_check


def reports():
    rows = [{"item_id": f"E-{i}", "seed": seed, "slices": ["money_movement"] if i < 2 else [],
             "pass_rate": True} for i in range(4) for seed in (11, 22)]
    return {"rows": copy.deepcopy(rows)}, {"rows": copy.deepcopy(rows)}


def rule(blocking=True, minimum=0.9, ci=True):
    return {"slices": [{"name": "money_movement", "metric": "pass_rate", "min": minimum,
                        "no_significant_drop": ci, "blocking": blocking}]}


def test_slice_floor_and_nonblocking():
    pr, base = reports()
    pr["rows"][0]["pass_rate"] = False
    blocked, _ = slice_check(pr, base, rule())
    assert blocked == ["slice:money_movement/pass_rate"]
    assert slice_check(pr, base, rule(blocking=False))[0] == []


def test_missing_empty_and_unpaired_are_not_success():
    pr, base = reports()
    assert slice_check({"rows": []}, base, rule())[0]
    pr["rows"].pop(0)
    assert slice_check(pr, base, rule())[0]
    pr, base = reports()
    pr["rows"][0]["pass_rate"] = None
    assert slice_check(pr, base, rule())[0]


def test_pairing_by_item_not_row_order():
    pr, base = reports()
    pr["rows"].reverse()
    assert slice_check(pr, base, rule())[0] == []


def test_ci_touching_zero_does_not_block_if_floor_met(monkeypatch):
    pr, base = reports()
    monkeypatch.setattr("lab9.gate.stats.paired_bootstrap", lambda *args, **kwargs: (-0.1, -0.2, 0.0))
    blocked, lines = slice_check(pr, base, rule())
    assert not blocked
    assert "+0.000" in lines[0]


def test_significant_drop_blocks_despite_floor(monkeypatch):
    pr, base = reports()
    monkeypatch.setattr("lab9.gate.stats.paired_bootstrap", lambda *args, **kwargs: (-0.1, -0.2, -0.01))
    assert slice_check(pr, base, rule())[0]
