# Nhanh.vn ETL Pipeline (retail-wide-mart)

Dự án crawl và trích xuất dữ liệu từ **Nhanh.vn Open API v3.0** về kho dữ liệu thô (raw data) phục vụ phân tích kinh doanh.

---

## 📁 Cấu trúc thư mục dự án

```text
retail-wide-mart/
│
├── .env                  # Thông tin bí mật: APP_ID, BUSINESS_ID, ACCESS_TOKEN
├── .env.example          # File mẫu để sao chép thành .env
├── .gitignore            # Loại trừ .env và dữ liệu data/raw/
├── requirements.txt      # Thư viện Python cần thiết
├── README.md             # Hướng dẫn sử dụng
├── main.py               # Runner tổng hợp chạy toàn bộ hoặc từng phần
│
├── src/
│   ├── __init__.py
│   ├── nhanh_client.py   # Client API dùng chung (v3.0, phân trang cursor, timeout, logging)
│   ├── crawl_product.py  # Module trích xuất Sản phẩm
│   ├── crawl_customer.py # Module trích xuất Khách hàng
│   └── crawl_order.py    # Module trích xuất Đơn hàng
│
└── data/
    └── raw/
        ├── product/      # Chứa file JSON thô của Sản phẩm
        ├── customer/     # Chứa file JSON thô của Khách hàng
        └── order/        # Chứa file JSON thô của Đơn hàng
```

---

## ⚙️ Cài đặt & Cấu hình

### 1. Cài đặt thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### 2. Thiết lập biến môi trường
Tạo file `.env` tại thư mục gốc (hoặc copy từ `.env.example`):
```env
NHANH_APP_ID=your_actual_app_id
NHANH_BUSINESS_ID=your_actual_business_id
NHANH_ACCESS_TOKEN=your_actual_access_token
```

---

## 🚀 Hướng dẫn Chạy Thử Nghiệm

### Cách 1: Chạy tổng hợp qua `main.py`

- **Crawl tất cả (mặc định lấy 5 mẫu mỗi loại):**
  ```bash
  python main.py
  ```

- **Tùy chỉnh số lượng mẫu lấy thử:**
  ```bash
  python main.py --limit 10
  ```

- **Chỉ crawl riêng 1 đối tượng:**
  ```bash
  python main.py --target product
  python main.py --target customer
  python main.py --target order
  ```

### Cách 2: Chạy độc lập từng module trong `src/`

- **Sản phẩm (Product):**
  ```bash
  python src/crawl_product.py
  ```
- **Khách hàng (Customer):**
  ```bash
  python src/crawl_customer.py
  ```
- **Đơn hàng gần nhất (Order):**
  ```bash
  python src/crawl_order.py
  ```

---

## 🕒 Crawl Toàn Bộ Lịch Sử Đơn Hàng (Quá khứ -> Hiện tại)

Nhanh.vn quy định mỗi request **tối đa 31 ngày** và **Rate Limit 150 request / 30s**. Script `src/crawl_order_history.py` đã tự động:
1. Chia nhỏ khoảng thời gian thành các khối **30 ngày**.
2. Tự động lặp phân trang (`paginator.size = 100`) để kéo sạch toàn bộ đơn hàng trong từng khối.
3. Điều phối độ trễ an toàn và tự nghỉ 35s nếu gặp `ERR_429`.
4. Lưu Checkpoint (`.checkpoint_history.json`) để nếu bị gián đoạn mạng, chạy lại sẽ tự động tiếp tục phần còn dở.

```bash
# Crawl toàn bộ đơn hàng từ 01/01/2024 đến hôm nay:
python src/crawl_order_history.py --start 2024-01-01

# Hoặc chỉ định rõ khoảng từ ngày A đến ngày B:
python src/crawl_order_history.py --start 2024-01-01 --end 2024-12-31
```

---

## 📑 Xuất Bảng Dữ Liệu Phẳng Ra Excel (Tương tự Sheet Nhanh)

Để "bung" mảng sản phẩm trong mỗi đơn hàng và liên kết đầy đủ thông tin Đơn hàng - Khách hàng - Sản phẩm (Line items):

```bash
python src/export_orders_to_excel.py
```
File Excel đầu ra sẽ được lưu vào: `data/export/Nhanh_Orders_Flattened_YYYYMMDD_HHMMSS.xlsx`.
