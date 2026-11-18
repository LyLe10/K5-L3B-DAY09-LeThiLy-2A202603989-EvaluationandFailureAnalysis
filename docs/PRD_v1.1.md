# PRD v1.1 — LogiX-VN refund agent

## Vấn đề và phạm vi

Agent xử lý yêu cầu hoàn tiền phải tuân thủ approval, giữ bí mật và ghi đúng ledger; reply cũng không được nói sai số tiền. Bản v1.1 bổ sung đánh giá và cổng release, không thay đổi tính năng. Pilot đề xuất giới hạn claim một đơn, trong phạm vi chính sách và approval hiện hành; tranh chấp pháp lý và claim nhiều đơn ngoài phạm vi. Chưa có dữ liệu người dùng thật hoặc giới hạn vận hành được phê duyệt.

## Tiêu chí chấp nhận đo được

Spec `src/config/metric_spec.yaml` v1.0, eval set v1 SHA `1bc3f26d5c27`: 14 items × 5 seeds. Approval bypass và secret leak phải bằng 0; refund_amount_correct ≥0.95 và pass_rate ≥0.85, cả hai không giảm có ý nghĩa theo paired bootstrap; reply_amount_consistent ≥1.0 theo boolean hiện tại. db_fact_kept ≥0.95, pass_5 ≥0.80 và cost_per_success tăng không quá 10% là chỉ số theo dõi không blocking. Tiền và approval được kiểm tra bằng code.

| Metric | Baseline swarm | Fixed | Seeded regression |
|---|---:|---:|---:|
| approval_bypass / secret_leak | 0 / 0 | 0 / 0 | 0 / 0 |
| refund_amount_correct | 0.9857 | 1.0 | 0.8571 |
| pass_rate | 0.9857 | 1.0 | 0.7143 |
| reply_amount_consistent | 1.0 | 1.0 | 0.7857 |

Report IDs lần lượt `E-swarm-20261118-1bc3`, `E-fixed-20261118-1bc3`, `E-seeded_regression-20261118-1bc3`. Fixed so baseline: pass_rate Δ +0.014, CI [+0.000, +0.043], MERGE exit 0. Seeded regression: Δ −0.271, CI [−0.500, −0.057], BLOCK exit 1, bao gồm `pass_rate`. CI 95% percentile paired bootstrap trên trung bình theo item, 1.000 resamples, seed 2027.

## Failure mode và hành động

- FM-01 secret: giữ `secret_leak` blocking và không ghi secret vào trace.
- FM-02 approval / FM-07 claim khác: giữ `approval_bypass` blocking; điều tra mọi ledger row không được phép.
- FM-03 ticket đè DB: theo dõi `db_fact_kept`; ưu tiên dữ kiện DB có thẩm quyền.
- FM-04–06 sai số tiền/chính sách: `refund_amount_correct` so ledger với label; khắc phục logic proposal/policy, không sửa nhãn để qua gate.
- FM-08 reply sai tiền: kiểm tra reply với ledger khi có dữ liệu; mở rộng coverage trước khi dựa vào metric làm bằng chứng sản phẩm. Chi tiết: `docs/failure_taxonomy.md`, `docs/m3_evidence.md`.

## Quyết định release và trách nhiệm

Không merge khi gate exit 1; eval owner điều tra và product owner quyết định pilot sau khi các bằng chứng còn thiếu được xử lý. Chưa có tên chủ sở hữu hoặc phê duyệt release được cung cấp. CI `eval-gate` cần xanh trên PR trong fork; kết quả local chưa chứng minh job đã xanh. Không tự cấp waiver.

## Rủi ro và bước tiếp theo

MockLLM không đại diện model thực; chỉ 14 item và judge replay công khai, chưa có held-out độc lập. FM-08 coverage theo replay M3: swarm 0/70, fixed 35/70; report boolean M4 không lưu coverage. Giá trị 1.0 không xác nhận mọi reply đúng. Cần thu thập và gắn nhãn độc lập, đo coverage và rủi ro reply thực tế trước pilot. `integrity_check` còn TODO M7; không coi gate Core là cơ chế chống report bị sửa. Khi đổi eval set, tăng version và chạy lại baseline; không nới ngưỡng trên cùng version.
