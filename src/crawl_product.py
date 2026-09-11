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

RAW_DATA_DIR = ROOT_DIR / "data" / "raw" / "product"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


def crawl_products(limit: int = 10, save_file: bool = True) -> list:
    """
    Lấy danh sách sản phẩm từ API Nhanh.vn (v3.0).
    Lưu dữ liệu raw vào data/raw/product/ và in ra các trường cơ bản.
    """
    client = NhanhClient()
    if not client.is_configured():
        client.validate_or_warn()
        return []

    print(f"\n📦 [Product Crawler] Bắt đầu gọi API product/list (kích thước: {limit})...")
    res = client.fetch_list(endpoint="product/list", size=limit)

    if not res["success"]:
        print("❌ Lấy dữ liệu sản phẩm thất bại.")
        return []

    items = res["items"]
    raw = res["raw"]

    print(f"✅ Thành công! Mã code: {res['code']} | Số sản phẩm lấy được: {len(items)}")

    # Lưu dữ liệu raw nguyên bản về thư mục data/raw/product/
    if save_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = RAW_DATA_DIR / f"products_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu dữ liệu thô tại: {output_file.relative_to(ROOT_DIR)}")

    # Hiển thị tóm tắt các trường cơ bản
    print("\n" + "-" * 80)
    print(f"{'STT':<4} | {'ID':<10} | {'Mã SKU':<15} | {'Giá bán (VNĐ)':<15} | {'Tên sản phẩm'}")
    print("-" * 80)

    for idx, item in enumerate(items, 1):
        item_id = str(item.get("id", ""))
        code = str(item.get("code", ""))[:14]
        prices = item.get("prices", {})
        price_val = prices.get("retail") if isinstance(prices, dict) else item.get("price", 0)
        price = f"{price_val:,}" if isinstance(price_val, (int, float)) else str(price_val)
        name = str(item.get("name", ""))[:35]
        print(f"{idx:<4} | {item_id:<10} | {code:<15} | {price:<15} | {name}")

    print("-" * 80)
    return items


if __name__ == "__main__":
    print("==========================================================")
    print("🚀 CHẠY MODULE CRAWL SẢN PHẨM (PRODUCT)")
    print("==========================================================")
    crawl_products(limit=10)
