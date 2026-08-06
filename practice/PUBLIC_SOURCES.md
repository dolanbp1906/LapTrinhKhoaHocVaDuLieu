# NGUỒN CÔNG KHAI CÓ THỂ DÙNG THAY THẾ

Ngày kiểm tra: 2026-07-23

## 1. DummyJSON Products API

- Tài liệu: https://dummyjson.com/docs/products
- Endpoint: https://dummyjson.com/products
- Mục đích: API dữ liệu giả dành cho phát triển, kiểm thử và học tập.
- Trường có thể lấy: id, title, category, price, brand, stock.
- Lưu ý: dữ liệu và giá chỉ phục vụ thực hành; cần ánh xạ tên trường về cấu trúc của chuyên đề.

## 2. Books to Scrape

- Trang chính: https://books.toscrape.com/
- Mục đích: website sandbox được thiết kế riêng cho luyện web scraping.
- Trường có thể lấy: tên sách, giá, tình trạng tồn kho, danh mục, đường dẫn sản phẩm.
- Lưu ý: website thông báo rõ giá và xếp hạng là dữ liệu ngẫu nhiên, không có ý nghĩa thương mại thực tế.

## Nguyên tắc sử dụng

- Chỉ gửi yêu cầu ở tốc độ thấp, ví dụ nghỉ 1–2 giây giữa các trang.
- Không đăng nhập, không vượt CAPTCHA và không tìm cách né cơ chế giới hạn.
- Ghi rõ URL, ngày truy cập, trường đã thu thập và bước làm sạch.
- Nếu nguồn thay đổi cấu trúc, chuyển sang HTML mẫu trong bộ tài liệu này.
