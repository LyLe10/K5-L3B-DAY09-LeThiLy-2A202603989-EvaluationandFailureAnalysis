# Trace case: C-002, ticket ghi ?? DB

Ch?y offline t? `src/`:

```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q tests/test_lab9_trace_case_m1.py
```

| Tr??ng | K?t qu? |
|---|---|
| Trial | `seeded_regression C-002@11`, trial run_id `R-seeded_regression-C-002-s11` (ID c?a trial, kh?ng ph?i report run_id). |
| Tri?u ch?ng | Lab 8 grader FAIL: `status resolved != denied`; ledger 20.000?, label 0; reply n?i ?? ho?n 20.000?. |
| B??c sai ??u ti?n | Event 3 `model_override`, payload `{"delay_days": 5}`. |
| V? sao ??u ti?n | Event 1 handoff; event 2 lookup cho O-202 c? `delay_days=2`. Event 3 thay b?ng 5 t? ticket, tr??c quote v? tr??c ghi ledger. |
| Failure mode | FM-03 ticket_trust. |
| ??i ch?ng | `fixed C-002@11`: event 3 quote 0 `no_entitlement`, ledger 0, status denied, grader PASS; kh?ng c? model_override. |
| Regression test | `test_ticket_override_regression_against_fixed` ch?y c? hai shape, ??i chi?u event, ledger v? label; x?c nh?n trial l?i fail v? fixed pass. |
| Ch?a ch?c ch?n | Trace cho th?y override v? k?t qu?, kh?ng ch?ng minh tr?ng th?i n?i b? kh?ng ???c ghi; kh?ng th? ??i chi?u anchor key c?a gi?ng vi?n. |

Kh?ng c?n report cho case n?y: `investigate` ch?y t?ng trial trong temporary store v? tr? trial run_id; kh?ng g?i ID n?y l? report run_id.
