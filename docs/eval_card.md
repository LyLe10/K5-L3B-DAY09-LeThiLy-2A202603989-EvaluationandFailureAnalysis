# Eval card — LogiX-VN refund agent

Đánh giá offline trên code và grader commit `c75d989`, eval set v1 SHA `1bc3f26d5c27`, metric spec 1.0. Dữ liệu gồm 14 item `lab8_public`, nhãn riêng `labels_v1.json`, mỗi item chạy seeds 11, 22, 33, 44, 55 (70 trial/shape). Report do `lab9.eval` sinh, `evaluator_failures` rỗng.

| Metric | Ngưỡng / blocking | Swarm baseline | Fixed | Seeded regression |
|---|---|---:|---:|---:|
| approval_bypass | max 0 / có | 0 | 0 | 0 |
| secret_leak | max 0 / có | 0 | 0 | 0 |
| db_fact_kept | min 0.95 / không | 0.9857 | 1.0 | 0.9286 |
| refund_amount_correct | min 0.95 + không giảm có ý nghĩa / có | 0.9857 | 1.0 | 0.8571 |
| pass_rate | min 0.85 + không giảm có ý nghĩa / có | 0.9857 | 1.0 | 0.7143 |
| pass_5 | min 0.80 / không | 0.9286 | 1.0 | 0.7143 |
| cost_per_success | tăng tối đa 10% / không | 49.567 | 48.7157 | 81.202 |
| reply_amount_consistent | min 1.0 / có | 1.0 | 1.0 | 0.7857 |

Run IDs: baseline `E-swarm-20261118-1bc3`; fixed `E-fixed-20261118-1bc3`; seeded regression `E-seeded_regression-20261118-1bc3`. Các run ID theo shape/ngày/SHA ngắn, không đảm bảo duy nhất cho mọi lần chạy trong cùng ngày.

Paired bootstrap 95%, percentile, 1.000 resamples, seed 2027, đơn vị tái lấy mẫu là item sau khi lấy trung bình 5 seed. Δ pass_rate = PR − baseline: fixed **+0.014**, CI **[+0.000, +0.043]**, gate **MERGE, exit 0**; seeded regression **−0.271**, CI **[−0.500, −0.057]**, gate **BLOCK, exit 1**, có `pass_rate` trong các metric bị chặn. Gate cũng chặn seeded regression theo `refund_amount_correct` và `reply_amount_consistent`.

Judge tone replay: κ=0.757, P=0.857, R=0.800 đạt floors; helpful κ=0.375, P=1.000, R=0.300 không được dùng gate. Xem `docs/judge_audit.md`. Trace case và regression test: `docs/trace_case.md`.

**Giới hạn:** MockLLM và dữ liệu public không đại diện traffic hay model thật; 14 item làm CI rộng; judge replay chưa có held-out độc lập. FM-08: replay M3 cho swarm 0/70 và fixed 35/70 trial có thể xác minh; report M4 chỉ lưu boolean, không lưu coverage nên không thể xác nhận lại các số này từ report. Aggregate 1.0 không chứng minh 100% reply đúng; swarm không ghi reply event. Không coi gate Core là kiểm tra toàn vẹn chống sửa report: integrity_check là TODO M7. Chỉ mở pilot sau khi có kiểm thử dữ liệu thực, owner và tiêu chí được phê duyệt; eval owner điều tra gate đỏ và không merge khi chưa xử lý. Thay đổi tập item/nhãn cần phiên bản eval set mới và baseline tương ứng.


## Advanced M5–M6 — eval set v2

V2 gồm 28 item × 5 seed, SHA `a74cc128b448`: 14 item v1 cộng 14 adversarial claims. Item giữ provenance và FM; reference labels được tách tại `src/data/eval/labels_v2.json`. Coverage toàn v2 cho các FM bị tấn công: FM-02 4, FM-03 3, FM-04 9, FM-05 4, FM-06 3, FM-07 5, FM-08 4, FM-09 3. Validator trả 0 problems. Replay fixed trên các cross-principal claims xác nhận ranh giới từ chối truy cập; không chứng minh đã xảy ra rò rỉ.

Baseline swarm `E-swarm-20261118-a74c`: pass_rate 0.9786, pass_hat_5 0.8929. Threshold `pass_hat_5 ≥ 0.80` là **ngưỡng thử nghiệm**, blocking. `money_movement` và `adversarial` là slices blocking với pass_rate min 0.90 và paired CI; FM-08 `reply_amount_consistent` blocking min 1.0. Không diễn giải boolean 1.0 thành coverage reply đầy đủ: swarm không ghi reply event.

| Shape (run ID `E-<shape>-20261118-a74c`) | pass_rate | pass_hat_5 | Kết quả local |
|---|---:|---:|---|
| swarm so với chính nó | 0.9786 | 0.8929 | MERGE |
| fixed | 1.0000 | 1.0000 | MERGE |
| honest_refactor | 1.0000 | 1.0000 | MERGE |
| slice_regression | 0.9357 | 0.8929 | BLOCK `slice:money_movement/pass_rate` (0.85) |
| flaky_regression | 0.9143 | 0.5714 | BLOCK gồm `pass_hat_5`, `pass_rate` và money slice |
| seeded_regression | 0.6429 | 0.6429 | BLOCK gồm `pass_rate`, `pass_hat_5`, `reply_amount_consistent` và slices |

A/A dùng seeds 66,77,88,99,110 so với 11,22,33,44,55: mọi delta được in là 0; pass_hat_5 = 0.8929 ở cả hai. MockLLM A/A không đại diện nhiễu của LLM thật. Với chỉ 5 seed, bug xuất hiện 1/3 seed không được phát hiện ổn định; không điều chỉnh ngưỡng chỉ để bắt mẫu đó. Hidden tests chưa kiểm chứng. M7 integrity/ratchet chưa triển khai; CI v2 chưa được xác nhận và workflow hiện chọn cả test M7.

Tái lập từ `src/` sau khi có baseline v2:

```bash
python -m lab9.evalset --v2 --check
python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
```
