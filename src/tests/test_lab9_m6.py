from math import comb

import pytest

from lab9.stats import pass_at_k, pass_hat_k


@pytest.mark.parametrize("n,c,k", [(1, 0, 1), (1, 1, 1), (5, 0, 5), (5, 5, 5),
                                     (5, 2, 3), (5, 2, 1), (5, 4, 5)])
def test_edge_cases_against_exact(n, c, k):
    total = comb(n, k)
    assert pass_at_k(n, c, k) == pytest.approx((total - (comb(n-c, k) if n-c >= k else 0)) / total)
    assert pass_hat_k(n, c, k) == pytest.approx((comb(c, k) if c >= k else 0) / total)


def test_all_small_vectors_against_exact():
    for n in range(1, 21):
        for c in range(n + 1):
            for k in range(1, n + 1):
                total = comb(n, k)
                a = (total - (comb(n-c, k) if n-c >= k else 0)) / total
                h = (comb(c, k) if c >= k else 0) / total
                assert pass_at_k(n, c, k) == a
                assert pass_hat_k(n, c, k) == h
                assert 0 <= h <= c / n <= a <= 1


@pytest.mark.parametrize("args", [(-1, 0, 1), (0, 0, 1), (5, -1, 1), (5, 6, 1),
                                   (5, 2, 0), (5, 2, -1), (5, 2, 6),
                                   (5.0, 2, 1), (5, 2.0, 1), (5, 2, 1.0),
                                   ("5", 2, 1), (5, None, 1), (True, 1, 1),
                                   (5, False, 1), (5, 2, True)])
@pytest.mark.parametrize("fn", [pass_at_k, pass_hat_k])
def test_invalid_inputs(fn, args):
    with pytest.raises(ValueError):
        fn(*args)


def test_large_counts_and_tiny_probability():
    n = 10**20
    assert pass_at_k(n, 1, 1) == 1 / n
    assert pass_hat_k(n, n - 1, 1) == (n - 1) / n
    assert pass_hat_k(10000, 5000, 2) == comb(5000, 2) / comb(10000, 2)
    assert pass_at_k(10000, 5000, 2) == (comb(10000, 2) - comb(5000, 2)) / comb(10000, 2)


def gate_report(metrics):
    return {"manifest": {"eval_set_sha": "x", "items": 1, "seeds": [11]},
            "rows": [{"item_id": "E-1", "seed": 11, "slices": [], "pass_rate": True}],
            "metrics": dict(metrics), "evaluator_failures": []}


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf"), "bad", True])
@pytest.mark.parametrize("blocking", [True, False])
def test_invalid_global_metric_is_not_pass(value, blocking):
    from lab9.gate import check
    pr, base = gate_report({"metric": value}), gate_report({"metric": 1.0})
    spec = {"metrics": [{"id": "metric", "threshold": {"min": 0.8}, "blocking": blocking}]}
    blocked, lines = check(pr, base, spec)
    assert blocked == ["integrity"]
    assert "invalid aggregate metric metric" in lines[0]


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf"), "bad"])
def test_invalid_slice_metric_blocks(value):
    from lab9.gate import slice_check
    base = {"rows": [{"item_id": "E-1", "seed": 11, "slices": ["s"], "metric": True}]}
    pr = {"rows": [{"item_id": "E-1", "seed": 11, "slices": ["s"], "metric": value}]}
    spec = {"slices": [{"name": "s", "metric": "metric", "min": 0.9, "blocking": True}]}
    blocked, lines = slice_check(pr, base, spec)
    assert blocked == ["slice:s/metric"]
    assert "missing" in lines[0]


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf"), "bad"])
def test_invalid_baseline_metric_blocks(value):
    from lab9.gate import check
    pr, base = gate_report({"metric": 1.0}), gate_report({"metric": value})
    spec = {"metrics": [{"id": "metric", "threshold": {"min": 0.8}, "blocking": True}]}
    blocked, lines = check(pr, base, spec)
    assert blocked == ["integrity"]
    assert "baseline: invalid aggregate metric metric" in lines[0]


def test_pass_hat_5_aggregate_uses_all_five_trials():
    from lab9.eval import aggregate
    rows = [{"item_id": "E-1", "pass_rate": i < 4, "cost": 0} for i in range(5)]
    assert aggregate(rows, ["pass_rate"], [5])["pass_hat_5"] == 0.0
    for row in rows:
        row["pass_rate"] = True
    assert aggregate(rows, ["pass_rate"], [5])["pass_hat_5"] == 1.0
    assert aggregate(rows[:4], ["pass_rate"], [5])["pass_hat_5"] is None


def test_pass_hat_5_gate_block_merge_and_missing():
    from lab9.gate import check
    spec = {"metrics": [{"id": "pass_hat_5", "threshold": {"min": 0.8}, "blocking": True}]}
    base = gate_report({"pass_hat_5": 1.0})
    assert check(gate_report({"pass_hat_5": 0.79}), base, spec)[0] == ["pass_hat_5"]
    assert check(gate_report({"pass_hat_5": 0.8}), base, spec)[0] == []
    assert check(gate_report({"pass_hat_5": 0.81}), base, spec)[0] == []
    assert check(gate_report({}), base, spec)[0] == ["pass_hat_5"]
    assert check(gate_report({"pass_hat_5": float("nan")}), base, spec)[0] == ["integrity"]
    spec["metrics"][0]["blocking"] = False
    assert check(gate_report({"pass_hat_5": 0.79}), base, spec)[0] == []


def test_max_metric_threshold_decisions():
    from lab9.gate import check
    spec = {"metrics": [{"id": "metric", "threshold": {"max": 0.8}, "blocking": True}]}
    base = gate_report({"metric": 0.8})
    assert check(gate_report({"metric": 0.81}), base, spec)[0] == ["metric"]
    assert check(gate_report({"metric": 0.8}), base, spec)[0] == []
    spec["metrics"][0]["blocking"] = False
    assert check(gate_report({"metric": 0.81}), base, spec)[0] == []


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf")])
def test_invalid_row_metric_integrity(value):
    from lab9.gate import check
    pr, base = gate_report({"pass_rate": 1.0}), gate_report({"pass_rate": 1.0})
    pr["rows"][0]["pass_rate"] = value
    spec = {"metrics": [{"id": "pass_rate", "threshold": {"min": 0.8}, "blocking": True}]}
    assert check(pr, base, spec)[0] == ["integrity"]
