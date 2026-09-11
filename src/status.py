import sys
import json
from pathlib import Path

# Đảm bảo UTF-8 trên Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
STATUS_FILE = ROOT_DIR / "data" / "crawl_status.json"


def show_status():
    if not STATUS_FILE.exists():
        print("ℹ️ Chưa có tiến trình crawl nào đang chạy hoặc chưa tạo file trạng thái.")
        return

    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Không thể đọc file trạng thái: {e}")
        return

    status = data.get("status", "UNKNOWN")
    pct = data.get("progress_percent", 0.0)
    current_chunk = data.get("current_chunk", 0)
    total_chunks = data.get("total_chunks", 0)
    chunk_range = data.get("current_chunk_range", "")
    page = data.get("page_in_current_chunk", 0)
    chunk_orders = data.get("orders_in_current_chunk", 0)
    total_orders = data.get("total_orders_so_far", 0)
    elapsed = data.get("elapsed_time", "0s")
    updated_at = data.get("last_updated", "")

    bar_len = 25
    filled = int(bar_len * (pct / 100))
    bar = "█" * filled + "░" * (bar_len - filled)

    status_icon = "🟢" if status == "RUNNING" else ("🎉" if status == "COMPLETED" else "⏸️")

    print("\n" + "=" * 65)
    print(f"{status_icon} TRẠNG THÁI TIẾN ĐỘ CRAWL DỮ LIỆU NHANH.VN")
    print("=" * 65)
    print(f"Trạng thái          : {status}")
    print(f"Tiến trình tổng     : [{bar}] {pct}%")
    print(f"Khoảng thời gian    : Khoảng {current_chunk}/{total_chunks} ({chunk_range})")
    print(f"Trang hiện tại      : Trang {page} ({chunk_orders:,} đơn trong khoảng này)")
    print(f"Tổng số đơn đã gom  : {total_orders:,} đơn")
    print(f"Thời gian đã chạy   : {elapsed}")
    print(f"Cập nhật lúc        : {updated_at}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    show_status()
