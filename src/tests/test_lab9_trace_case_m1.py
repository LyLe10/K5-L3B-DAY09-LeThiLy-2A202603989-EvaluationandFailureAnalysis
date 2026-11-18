from lab9.trace_case import investigate


def test_ticket_override_regression_against_fixed():
    broken = investigate("seeded_regression", "C-002", 11)
    fixed = investigate("fixed", "C-002", 11)
    bad, good = broken["trial"], fixed["trial"]
    assert broken["label"] == fixed["label"]
    assert bad["events"][1]["payload"]["lookup_order"]["order"]["delay_days"] == 2
    assert bad["events"][2]["kind"] == "model_override"
    assert bad["events"][2]["payload"]["delay_days"] == 5
    assert bad["snapshot"]["refund_vnd"] == 20000
    assert not bad["lab8_pass"]
    assert all(event["kind"] != "model_override" for event in good["events"])
    assert good["snapshot"]["refund_vnd"] == fixed["label"]["refund_vnd"] == 0
    assert good["result"]["status"] == fixed["label"]["status"] == "denied"
    assert good["lab8_pass"]
