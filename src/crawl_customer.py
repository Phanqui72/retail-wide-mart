import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Đảm bảo import được src khi chạy độc lập
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.nhanh_client import NhanhClient

RAW_DATA_DIR = ROOT_DIR / "data" / "raw" / "customer"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


def crawl_customers(limit: int = 10, save_file: bool = True) -> list:
    """
    Lấy danh sách khách hàng từ API Nhanh.vn (v3.0).
    Lưu dữ liệu raw vào data/raw/customer/ và in ra các trường cơ bản.
    """
    client = NhanhClient()
    if not client.is_configured():
        client.validate_or_warn()
        return []

    print(f"\n👤 [Customer Crawler] Bắt đầu gọi API customer/list (kích thước: {limit})...")
    res = client.fetch_list(endpoint="customer/list", size=limit)

    if not res["success"]:
        print("❌ Lấy dữ liệu khách hàng thất bại.")
        return []

    items = res["items"]
    raw = res["raw"]

    print(f"✅ Thành công! Mã code: {res['code']} | Số khách hàng lấy được: {len(items)}")

    # Lưu dữ liệu raw nguyên bản về thư mục data/raw/customer/
    if save_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = RAW_DATA_DIR / f"customers_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu dữ liệu thô tại: {output_file.relative_to(ROOT_DIR)}")

    # Hiển thị tóm tắt các trường cơ bản
    print("\n" + "-" * 85)
    print(f"{'STT':<4} | {'ID':<10} | {'Tên khách hàng':<25} | {'Số điện thoại':<15} | {'Chi tiêu tích lũy'}")
    print("-" * 85)

    for idx, item in enumerate(items, 1):
        item_id = str(item.get("id", ""))
        name = str(item.get("name", ""))[:23]
        mobile = str(item.get("mobile", ""))[:13]
        spent_val = item.get("totalAmount") or item.get("totalSpent", 0)
        spent = f"{spent_val:,} VNĐ" if isinstance(spent_val, (int, float)) else str(spent_val)
        print(f"{idx:<4} | {item_id:<10} | {name:<25} | {mobile:<15} | {spent}")

    print("-" * 85)
    return items


if __name__ == "__main__":
    print("==========================================================")
    print("🚀 CHẠY MODULE CRAWL KHÁCH HÀNG (CUSTOMER)")
    print("==========================================================")
    crawl_customers(limit=10)
