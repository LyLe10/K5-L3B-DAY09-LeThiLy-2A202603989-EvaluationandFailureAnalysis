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
