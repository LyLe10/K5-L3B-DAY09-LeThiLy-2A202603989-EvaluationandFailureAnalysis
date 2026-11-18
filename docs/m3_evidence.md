# M3 — Trajectory evidence

## Trial pairs

`python -m pytest -q -o addopts= tests/test_lab9_graders.py tests/test_lab9_m3.py`

Each row below is a seed 11 pair: the first trial is generated at runtime by `make_shape` with the named public switch, the control is `fixed` on the same claim and seed. The tests first assert a real trace or ledger discrepancy, then score it and check the control. Detection is 6/6 = 100%; false positives are 0/6 = 0%, **for the relevant grader on these six controls**. This is a small, selected public sample, not an estimate of performance on all possible failures. The test uses existing SecretLeak and DbFactKept alongside the M3 graders; the rate is for that combined set, not exclusively the two new TODOs.

| Switch and claim | Actual observed failure | Grader |
|---|---|---|
| leaky_trace C-001@11 | forbidden secret in artifact | SecretLeak |
| ticket_trust C-002@11 | model_override event after DB lookup | DbFactKept |
| round_down C-001@11 | ledger amount differs from label | RefundAmountCorrect |
| pre_deducted C-014@11 | ledger amount differs from label | RefundAmountCorrect |
| sibling_refund C-001@11 | unexpected foreign ledger row | ApprovalBypass |
| misreport C-008@11 | reply 35.000đ versus ledger 20.000đ | ReplyAmountConsistent |

The `fixed C-008@11` control has a 20.000đ ledger and matching reply. FM-08 is therefore detected as a contradiction; the control is not flagged.

## Reply coverage and metric

Replayed in memory over the v1 14 claims × seeds 11, 22, 33, 44, 55, without writing reports:

| Shape | Match | Mismatch | Unverifiable | Boolean aggregate | Evaluator failures |
|---|---:|---:|---:|---:|---:|
| swarm | 0 | 0 | 70 | 1.0 | 0 |
| fixed | 35 | 0 | 35 | 1.0 | 0 |

`reply_amount_status` distinguishes match, mismatch and unverifiable; missing/multiple replies, no unique currency amount or missing ledger are unverifiable. The existing report retains only a boolean, so the evaluator returns true when no contradiction is observed and labels the reason unverifiable. **Aggregate 1.0 is not proof of a correct reply**: in particular swarm has no reply event at all. The min 1.0 blocking threshold means zero *observed* contradictions in this binary contract; it is not a coverage guarantee. Multiple monetary amounts are unverifiable rather than guessed. The deterministic parser supports integer VND with thousands separators and explicit currency units, not arbitrary natural-language amounts.

The new metric aggregates successfully in both shapes without evaluator failures. Full M4 gate compatibility and bootstrap checks remain unverified until M4; in particular the baseline cannot establish FM-08 coverage for swarm. A future coverage-aware schema would require separate authorization and design, not an unreported change to Day 8 or the gate.
