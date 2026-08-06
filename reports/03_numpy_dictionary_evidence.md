# Minh chứng NumPy và dictionary lồng nhau

## Dictionary lồng nhau

- Số đơn trong mẫu: **41**
- Doanh thu mẫu: **1,123,899,409 VND**
- Đã tính chi tiêu khách hàng và tần suất cặp sản phẩm bằng vòng lặp trên cấu trúc
  `order → customer/order/items`.

## NumPy

- Ma trận doanh thu tháng × danh mục: **(12, 7)**
- `sum(axis=1)`: tổng doanh thu từng tháng.
- `sum(axis=0)`: tổng doanh thu từng danh mục.
- Chuẩn hóa z-score theo cột; trung bình sau chuẩn hóa xấp xỉ 0.
- Giá trị tồn kho đầu kỳ: **15,230,705,000 VND**.

Đầu ra chi tiết: `reports/03_numpy_dictionary_evidence.json`.
