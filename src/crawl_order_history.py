import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Đảm bảo in tiếng Việt có dấu trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đảm bảo import được src khi chạy độc lập
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.nhanh_client import NhanhClient

ORDER_RAW_DIR = ROOT_DIR / "data" / "raw" / "order"
ORDER_RAW_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_FILE = ORDER_RAW_DIR / ".checkpoint_history.json"


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_checkpoint(completed_chunks: list):
    try:
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump({"completed_chunks": completed_chunks, "last_updated": datetime.now().isoformat()}, f, indent=2)
    except Exception as e:
        print(f"⚠️ Không thể lưu checkpoint: {e}")


def generate_date_chunks(start_date: datetime, end_date: datetime, max_days_per_chunk: int = 30) -> list:
    """
    Chia khoảng thời gian dài thành các khoảng nhỏ <= 30 ngày để thỏa mãn giới hạn của Nhanh.vn API v3.0.
    """
    chunks = []
    curr_start = start_date

    while curr_start < end_date:
        # Nhanh chỉ cho tối đa 31 ngày, ta chọn 30 ngày để đảm bảo an toàn tuyệt đối
        curr_end = min(curr_start + timedelta(days=max_days_per_chunk) - timedelta(seconds=1), end_date)
        chunks.append((curr_start, curr_end))
        curr_start = curr_end + timedelta(seconds=1)

    return chunks


def crawl_orders_history(
    start_date_str: str,
    end_date_str: str = None,
    page_size: int = 100,
    resume: bool = True
) -> dict:
    """
    Crawl toàn bộ đơn hàng từ quá khứ (start_date) đến hiện tại (end_date).
    - Tự động chia khoảng <= 30 ngày
    - Phân trang đầy đủ (cursor-based paginator) để không sót đơn nào
    - Kiểm soát Rate Limit và tự phục hồi (resume checkpoint)
    """
    client = NhanhClient(rate_limit_delay=0.35)
    if not client.validate_or_warn():
        return {"total_orders": 0, "all_orders": []}

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    except ValueError:
        print("❌ Định dạng start_date không hợp lệ. Vui lòng dùng YYYY-MM-DD (Ví dụ: 2024-01-01)")
        return {"total_orders": 0, "all_orders": []}

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            print("❌ Định dạng end_date không hợp lệ. Vui lòng dùng YYYY-MM-DD")
            return {"total_orders": 0, "all_orders": []}
    else:
        end_date = datetime.now()

    if start_date > end_date:
        print("❌ start_date phải nhỏ hơn hoặc bằng end_date.")
        return {"total_orders": 0, "all_orders": []}

    chunks = generate_date_chunks(start_date, end_date, max_days_per_chunk=30)
    checkpoint_data = load_checkpoint() if resume else {}
    completed_chunks = set(checkpoint_data.get("completed_chunks", []))

    print("=" * 80)
    print("🚀 BẮT ĐẦU CRAWL LỊCH SỬ ĐƠN HÀNG (ORDER HISTORY)")
    print(f"Khoảng thời gian: Từ {start_date.strftime('%d/%m/%Y')} Đến {end_date.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Tổng số khoảng (30 ngày/khoảng): {len(chunks)}")
    print(f"Số khoảng đã crawl trước đó (Checkpoint): {len(completed_chunks)}")
    print("=" * 80)

    total_orders_crawled = 0
    all_crawled_orders = []
    start_run_time = time.time()
    STATUS_FILE = ROOT_DIR / "data" / "crawl_status.json"

    def write_status(current_idx, chunk_info, page_num, chunk_count, total_count, is_done=False):
        try:
            pct = round(((current_idx - (0 if is_done else 1)) / len(chunks)) * 100, 1)
            elapsed_sec = int(time.time() - start_run_time)
            mins, secs = divmod(elapsed_sec, 60)
            status_obj = {
                "status": "COMPLETED" if is_done else "RUNNING",
                "progress_percent": 100.0 if is_done else pct,
                "current_chunk": current_idx,
                "total_chunks": len(chunks),
                "current_chunk_range": chunk_info,
                "page_in_current_chunk": page_num,
                "orders_in_current_chunk": chunk_count,
                "total_orders_so_far": total_count,
                "elapsed_time": f"{mins}m {secs}s",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(STATUS_FILE, "w", encoding="utf-8") as sf:
                json.dump(status_obj, sf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    for idx, (chunk_start, chunk_end) in enumerate(chunks, 1):
        chunk_key = f"{chunk_start.strftime('%Y%m%d_%H%M%S')}_{chunk_end.strftime('%Y%m%d_%H%M%S')}"
        chunk_title = f"{chunk_start.strftime('%d/%m/%Y')} -> {chunk_end.strftime('%d/%m/%Y')}"
        pct_start = round(((idx - 1) / len(chunks)) * 100, 1)

        if resume and chunk_key in completed_chunks:
            pct_done = round((idx / len(chunks)) * 100, 1)
            print(f"⏩ [{pct_done}%] Khoảng {idx}/{len(chunks)} ({chunk_title}): Đã crawl trước đó (Bỏ qua).", flush=True)
            write_status(idx, chunk_title, 0, 0, total_orders_crawled, is_done=False)
            continue

        print(f"\n📦 [{pct_start}%] Đang crawl Khoảng {idx}/{len(chunks)}: {chunk_title} ...", flush=True)

        chunk_orders = []
        next_cursor = None
        page_num = 1

        from_ts = int(chunk_start.timestamp())
        to_ts = int(chunk_end.timestamp())

        while True:
            payload = {
                "filters": {
                    "createdAtFrom": from_ts,
                    "createdAtTo": to_ts
                },
                "paginator": {
                    "size": page_size
                }
            }
            if next_cursor:
                payload["paginator"]["next"] = next_cursor

            res = client.post("order/list", payload)

            if not res["success"]:
                print(f"❌ Lỗi khi tải trang {page_num} của khoảng {chunk_title}: {res.get('error')}", flush=True)
                break

            raw = res["raw"]
            if raw.get("code") != 1:
                print(f"⚠️ Nhanh.vn trả về cảnh báo/lỗi: {raw.get('messages')}", flush=True)
                break

            items = raw.get("data", [])
            chunk_orders.extend(items)
            current_total = total_orders_crawled + len(chunk_orders)
            
            # In tiến trình mỗi trang kèm % tổng thể
            bar_len = 20
            filled = int(bar_len * (idx - 1 + (page_num / max(page_num + 1, 10))) / len(chunks))
            progress_bar = "█" * filled + "░" * (bar_len - filled)

            if page_num % 5 == 0 or not items or len(items) < page_size:
                print(f"   [{pct_start}% | {progress_bar}] Trang {page_num}: Lấy được {len(items)} đơn (Khoảng này: {len(chunk_orders):,} | Tổng: {current_total:,} đơn)", flush=True)
            else:
                print(f"   [{pct_start}%] Trang {page_num}: +{len(items)} đơn...", flush=True)

            # Cập nhật file trạng thái
            write_status(idx, chunk_title, page_num, len(chunk_orders), current_total, is_done=False)

            # Lấy con trỏ trang tiếp theo
            paginator_info = raw.get("paginator", {})
            next_cursor = paginator_info.get("next")

            if not next_cursor or not items:
                # Đã hết dữ liệu trong khoảng 30 ngày này
                break

            page_num += 1

        # Lưu dữ liệu raw của chunk này vào file
        chunk_filename = f"orders_{chunk_key}.json"
        chunk_file_path = ORDER_RAW_DIR / chunk_filename
        with open(chunk_file_path, "w", encoding="utf-8") as f:
            json.dump({"chunk": chunk_title, "total": len(chunk_orders), "data": chunk_orders}, f, ensure_ascii=False, indent=2)

        print(f"💾 Đã lưu {len(chunk_orders)} đơn của khoảng {chunk_title} vào: {chunk_file_path.name}")

        # Cập nhật checkpoint
        completed_chunks.add(chunk_key)
        save_checkpoint(list(completed_chunks))

        total_orders_crawled += len(chunk_orders)
        all_crawled_orders.extend(chunk_orders)

    write_status(len(chunks), "Hoàn thành", 0, 0, total_orders_crawled, is_done=True)

    print("\n" + "=" * 80, flush=True)
    print("🎉 HOÀN THÀNH CRAWL LỊCH SỬ ĐƠN HÀNG! [100%]", flush=True)
    print(f"Tổng số đơn hàng tải mới trong lần chạy này: {total_orders_crawled:,}", flush=True)
    print(f"Dữ liệu được lưu trữ tại: {ORDER_RAW_DIR}", flush=True)
    print("=" * 80, flush=True)

    return {"total_orders": total_orders_crawled, "all_orders": all_crawled_orders}


if __name__ == "__main__":
    from src.export_orders_to_excel import export_all_orders_to_excel

    parser = argparse.ArgumentParser(description="Crawl toàn bộ lịch sử đơn hàng Nhanh.vn (quản lý 30 ngày/request & Rate Limit)")
    parser.add_argument("--start", type=str, required=True, help="Ngày bắt đầu (YYYY-MM-DD), ví dụ: 2026-06-10")
    parser.add_argument("--end", type=str, default=None, help="Ngày kết thúc (YYYY-MM-DD), mặc định là hôm nay")
    parser.add_argument("--no-resume", action="store_true", help="Crawl lại từ đầu, không đọc checkpoint")
    parser.add_argument("--export-excel", action="store_true", help="Tự động xuất toàn bộ ra file Excel sau khi crawl xong")

    args = parser.parse_args()
    crawl_orders_history(start_date_str=args.start, end_date_str=args.end, resume=not args.no_resume)

    if args.export_excel:
        print("\n📊 Đang tự động xuất dữ liệu ra file Excel...")
        export_all_orders_to_excel()
