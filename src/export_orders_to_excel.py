import sys
import json
import glob
import pandas as pd
from datetime import datetime
from pathlib import Path

# Đảm bảo in tiếng Việt có dấu trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
RAW_ORDER_DIR = ROOT_DIR / "data" / "raw" / "order"
EXPORT_DIR = ROOT_DIR / "data" / "export"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def parse_order_to_rows(order: dict) -> list:
    """
    Biến đổi (flatten) một đối tượng Order lồng nhau từ Nhanh.vn API v3.0
    thành các dòng tương ứng với từng sản phẩm (Order Line Items),
    khớp với cấu trúc bảng của file Excel Nhanh.vn Order.
    """
    info = order.get("info", {})
    channel = order.get("channel", {})
    shipping = order.get("shippingAddress", {})
    carrier = order.get("carrier", {})
    payment = order.get("payment", {})
    products = order.get("products", [])

    created_at = ""
    created_ts = info.get("createdAt")
    if created_ts:
        created_at = datetime.fromtimestamp(created_ts).strftime("%d/%m/%Y %H:%M:%S")

    order_id = info.get("id")
    app_order_id = channel.get("appOrderId")
    order_type = info.get("type")
    depot_id = info.get("depotId")
    status = info.get("status")

    customer_name = shipping.get("name")
    customer_mobile = shipping.get("mobile")
    customer_address = shipping.get("address")

    carrier_name = carrier.get("name")
    ship_fee = carrier.get("shipFee", 0)
    cod_amount = payment.get("codAmount", 0)

    rows = []

    # Nếu đơn không có sản phẩm (trường hợp hiếm), tạo 1 dòng rỗng
    items_to_process = products if products else [{}]

    for p in items_to_process:
        qty = p.get("quantity", 1) if p else 1
        price = p.get("price", 0) if p else 0
        avg_cost = p.get("avgCost", 0) if p else 0
        discount = p.get("discount", 0) if p else 0
        total_amount = p.get("totalAmount", price * qty) if p else 0
        profit = (price - avg_cost) * qty

        rows.append({
            "ID": order_id,
            "ID Đơn hàng API": app_order_id,
            "Loại đơn": order_type,
            "Thời gian": created_at,
            "Nguồn đơn hàng": channel.get("saleChannel"),
            "Kho tạo đơn": depot_id,
            "Tên khách hàng": customer_name,
            "Số điện thoại": customer_mobile,
            "Địa chỉ": customer_address,
            "Sản phẩm": p.get("name"),
            "Mã sản phẩm": p.get("code"),
            "Mã vạch": p.get("barcode"),
            "Khối lượng": p.get("weight"),
            "Giá bán": price,
            "Số lượng": qty,
            "Chiết khấu sản phẩm": discount,
            "Giá trị đơn hàng": cod_amount,
            "Phí vận chuyển": ship_fee,
            "Hãng vận chuyển": carrier_name,
            "Tổng thu": cod_amount,
            "Giá vốn": avg_cost,
            "Thành tiền sản phẩm": total_amount,
            "Lợi nhuận": profit,
            "Trạng thái": status,
            "Tracking URL": info.get("trackingUrl")
        })

    return rows


def export_all_orders_to_excel(output_filename: str = None) -> Path:
    """
    Đọc tất cả các file JSON raw đơn hàng trong data/raw/order/
    và xuất ra 1 file Excel bảng phẳng hoàn chỉnh.
    """
    json_files = sorted(list(RAW_ORDER_DIR.glob("orders_*.json")))
    if not json_files:
        print("❌ Không tìm thấy file JSON nào trong data/raw/order/ để xuất.")
        return None

    print(f"📊 Tìm thấy {len(json_files)} file JSON dữ liệu đơn hàng. Đang xử lý...")

    all_rows = []
    seen_order_ids = set()

    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                orders = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                
                for order in orders:
                    oid = order.get("info", {}).get("id")
                    # Khử trùng lặp đơn nếu trùng giữa các file
                    if oid and oid in seen_order_ids:
                        continue
                    if oid:
                        seen_order_ids.add(oid)

                    rows = parse_order_to_rows(order)
                    all_rows.extend(rows)
        except Exception as e:
            print(f"⚠️ Lỗi đọc file {fpath.name}: {e}")

    if not all_rows:
        print("❌ Không trích xuất được dòng dữ liệu nào.")
        return None

    df = pd.DataFrame(all_rows)
    print(f"✅ Đã làm phẳng thành công {len(all_rows)} dòng sản phẩm từ {len(seen_order_ids)} đơn hàng!")

    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"Nhanh_Orders_Flattened_{timestamp}.xlsx"

    out_path = EXPORT_DIR / output_filename
    df.to_excel(out_path, index=False, engine="openpyxl")
    print(f"💾 File Excel đã được lưu tại: {out_path.relative_to(ROOT_DIR)}")
    return out_path


if __name__ == "__main__":
    export_all_orders_to_excel()
