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

RAW_DATA_DIR = ROOT_DIR / "data" / "raw" / "order"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


def crawl_orders(limit: int = 10, save_file: bool = True) -> list:
    """
    Lấy danh sách đơn hàng từ API Nhanh.vn (v3.0).
    Lưu dữ liệu raw vào data/raw/order/ và in ra các trường cơ bản.
    """
    client = NhanhClient()
    if not client.is_configured():
        client.validate_or_warn()
        return []

    print(f"\n🛒 [Order Crawler] Bắt đầu gọi API order/list (kích thước: {limit})...")
    res = client.fetch_list(endpoint="order/list", size=limit)

    if not res["success"]:
        print("❌ Lấy dữ liệu đơn hàng thất bại.")
        return []

    items = res["items"]
    raw = res["raw"]

    print(f"✅ Thành công! Mã code: {res['code']} | Số đơn hàng lấy được: {len(items)}")

    # Lưu dữ liệu raw nguyên bản về thư mục data/raw/order/
    if save_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = RAW_DATA_DIR / f"orders_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu dữ liệu thô tại: {output_file.relative_to(ROOT_DIR)}")

    # Hiển thị tóm tắt các trường cơ bản
    print("\n" + "-" * 95)
    print(f"{'STT':<4} | {'ID Đơn':<12} | {'Mã đơn sàn/kênh':<18} | {'Khách hàng':<18} | {'Tổng tiền (VNĐ)':<16} | {'Ngày tạo'}")
    print("-" * 95)

    for idx, item in enumerate(items, 1):
        info = item.get("info", {})
        channel = item.get("channel", {})
        shipping = item.get("shippingAddress", {})
        payment = item.get("payment", {})
        products = item.get("products", [])

        order_id = str(info.get("id", ""))[:11]
        app_order_id = str(channel.get("appOrderId") or info.get("orderIndex") or "")[:17]
        customer = str(shipping.get("name") or "Khách lẻ")[:17]
        
        # Tính tổng tiền: ưu tiên codAmount hoặc tổng tiền các sản phẩm
        money_val = payment.get("codAmount", 0)
        if not money_val and products:
            money_val = sum(p.get("totalAmount", 0) for p in products)
        money = f"{money_val:,}" if isinstance(money_val, (int, float)) else str(money_val)

        created_ts = info.get("createdAt")
        created_at = datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d %H:%M") if created_ts else ""

        print(f"{idx:<4} | {order_id:<12} | {app_order_id:<18} | {customer:<18} | {money:<16} | {created_at}")

    print("-" * 95)
    return items


if __name__ == "__main__":
    print("==========================================================")
    print("🚀 CHẠY MODULE CRAWL ĐƠN HÀNG (ORDER)")
    print("==========================================================")
    crawl_orders(limit=10)
