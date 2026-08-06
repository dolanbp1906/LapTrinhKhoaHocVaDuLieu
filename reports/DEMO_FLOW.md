# Flow demo — Chuyên đề 6

**Thời lượng gợi ý:** 10–12 phút demo + 3–5 phút Q&A  
**Ứng dụng:** [http://localhost:8501](http://localhost:8501)  
```bash
python -m streamlit run src/app_dashboard.py
```

---

## Sơ đồ nhanh (theo đề bài)

```text
Tổng quan → Kho OOP → Bán hàng → Phân tích EDA → RFM → Học máy → Nhật ký
   │            │           │            │           │         │
 Câu hỏi     Chặn âm kho  Rollback    Doanh thu   Nhóm KH   Dự đoán
 nghiên cứu  + log        nếu thiếu   / cặp SP    + chiến lược / cảnh báo
```

---

## Phút 0–1 — Mở đầu (Tổng quan)

**Menu:** `01 Tổng quan`

Nói:
1. Đề tài: phân tích bán hàng + quản lý tồn kho + phân nhóm khách hàng.
2. Cửa hàng: nhà sách & văn phòng phẩm.
3. 6 câu hỏi nghiên cứu trên màn hình.
4. Quy mô: 90 SP, 220 KH, 1.200 đơn, 3.274 dòng chi tiết.

Chỉ nhanh: nguồn = 60 GV + 30 crawl; giao dịch = synthetic seed=42.

---

## Phút 1–3 — Nghiệp vụ kho OOP (bắt buộc đề bài)

**Menu:** `02 Nghiệp vụ kho`

### Demo A — Nhập / xuất hợp lệ
1. Chọn **Nhập kho** → 1 sản phẩm còn nhiều tồn → số lượng nhỏ (vd. 5) → Xác nhận.
2. Nói: hệ thống ghi `quantity_before` / `quantity_after` vào nhật ký.

### Demo B — Chặn tồn kho âm (điểm then chốt)
1. Chọn **Xuất kho** → cùng SP → số lượng **lớn hơn tồn hiện tại**.
2. Hệ thống **từ chối** → không làm âm kho.
3. Nhắc: đây là yêu cầu PDF mục 6.1.

### Demo C — Điều chỉnh
1. Chọn **Điều chỉnh** → delta âm nhỏ → giải thích kiểm kê/hao hụt.

Sau đó sang mục `07 Nhật ký` (có thể quay lại cuối) để chỉ `inventory_log` + `error_log`.

---

## Phút 3–5 — Bán hàng + rollback

**Menu:** `03 Bán hàng`

### Demo D — Đơn hợp lệ
1. Chọn khách hàng, kênh `offline`, thanh toán `cash`/`transfer`.
2. Dòng 1: SP tồn đủ, số lượng nhỏ.
3. (Tuỳ chọn) Dòng 2: SP khác, số lượng nhỏ.
4. Tạo đơn → tồn giảm → đơn hiện trong phiên.

### Demo E — Rollback khi thiếu hàng
1. Tạo đơn 2 dòng: dòng 1 đủ hàng, dòng 2 **số lượng vượt tồn**.
2. Hệ thống fail → hoàn tác dòng đã trừ trước đó.
3. Nói: `SalesManager` + `InventoryManager` phối hợp, không để kho sai trạng thái.

---

## Phút 5–7 — Phân tích bán hàng (EDA)

**Menu:** `04 Phân tích` → tab **Doanh thu** rồi **Sản phẩm & cặp mua**

Trả lời lần lượt câu hỏi nghiên cứu:

| Câu hỏi PDF | Thao tác trên UI | Câu nói ngắn |
|---|---|---|
| Danh mục / kênh nào lớn nhất? | Biểu đồ danh mục + kênh | Thiết bị văn phòng; offline ~42% |
| Thời điểm doanh thu cao? | Doanh thu theo tháng | Đỉnh 2025-04 |
| SP bán chạy / chậm / mua cùng? | Top SP + heatmap cặp | Chỉ top SP và cặp P0064–P0067 |
| Thành phố? | Doanh thu theo TP | TP.HCM dẫn đầu (dữ liệu mô phỏng) |

Nhắc giới hạn: giao dịch synthetic + FX cố định → thiết bị giá cao chi phối doanh thu.

---

## Phút 7–8 — RFM + chiến lược

**Menu:** `05 RFM`

1. Chỉ `reference_date = 2026-01-01` (cố định, tái lập được).
2. Chỉ 4 nhóm: Champions / Loyal / Potential / At Risk.
3. Đọc 1–2 chiến lược (VIP giữ chân, win-back At Risk).
4. Nói: K-Means trên R, F, log1p(M); chọn k theo silhouette.

---

## Phút 8–10 — Học máy

**Menu:** `06 Học máy`

### Demo F — Dự đoán giá trị đơn
1. Chế độ **Giá trị đơn hàng**.
2. Nhập hồ sơ đơn (số dòng, số lượng, giá TB, kênh, thành phố…).
3. Bấm dự đoán → đọc số tiền ước lượng.
4. Nói metric: Dummy vs Linear vs Tree; Tree R² ≈ 0.79; có ≥10 case sai trong báo cáo.

### Demo G — Cảnh báo tồn kho
1. Chế độ **Cảnh báo tồn kho**.
2. Chọn 1 SP → xem dự báo dưới `reorder_level`.
3. Nói: F1 ≈ 0.98 nhưng lớp mất cân bằng (~77/90) → không chỉ nhìn Accuracy.

---

## Phút 10–11 — Nhật ký & tái lập

**Menu:** `07 Nhật ký`

1. Mở `inventory_log.csv` (UI runtime) → chỉ các giao dịch vừa demo.
2. Mở `error_log.txt` → chỉ lần xuất vượt tồn / rollback.
3. Kết luận: pipeline chạy lại bằng  
   `python src/run_all.py`  
   Báo cáo/slide: `reports/BAO_CAO_CHUYEN_DE_6.docx`, `reports/SLIDE_CHUYEN_DE_6.pptx`.

---

## Checklist 1 phút trước demo

- [ ] Dashboard đang mở `http://localhost:8501`
- [ ] Có sẵn 1 SP tồn thấp để demo từ chối âm kho
- [ ] Nhớ 3 số: R² ≈ 0.79, F1 ≈ 0.98, 77/90 dưới reorder
- [ ] Nhớ nói rõ: thu thập vs mô phỏng; không triển khai tự động trên dữ liệu thật

---

## Câu trả lời sẵn nếu bị hỏi

| Hỏi | Đáp ngắn |
|---|---|
| Vì sao không âm kho? | `InventoryManager` kiểm tra trước khi trừ; giao dịch rejected + ghi log. |
| Rollback hoạt động thế nào? | Đơn nhiều dòng: trừ tuần tự; 1 dòng fail → hoàn tác các dòng đã trừ. |
| Vì sao RMSE lớn? | Có outlier thiết bị giá cao; RMSE phạt sai số lớn. |
| Vì sao cố định ngày RFM? | Để kết quả tái lập, không đổi theo ngày chạy. |
| Dữ liệu crawl có tính SP mới không? | Có: DummyJSON + Books = 30 SP. HTML mẫu chỉ luyện, không tính. |
