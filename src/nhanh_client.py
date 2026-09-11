import os
import sys
import warnings
from pathlib import Path

# Đảm bảo in tiếng Việt có dấu trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

warnings.filterwarnings("ignore")

import requests
from dotenv import load_dotenv

# Tự động tìm nạp .env từ thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class NhanhClient:
    """
    Client kết nối và tương tác với Nhanh.vn Open API (v3.0).
    Docs: https://apidocs.nhanh.vn/
    """
    BASE_URL = "https://pos.open.nhanh.vn/v3.0"

    def __init__(
        self,
        app_id: str = None,
        business_id: str = None,
        access_token: str = None,
        rate_limit_delay: float = 0.35
    ):
        self.app_id = (app_id or os.getenv("NHANH_APP_ID", "")).strip()
        self.business_id = (business_id or os.getenv("NHANH_BUSINESS_ID", "")).strip()
        self.access_token = (access_token or os.getenv("NHANH_ACCESS_TOKEN", "")).strip()
        # Nghỉ giữa các request (0.35s ~ tối đa 2.8 req/giây, an toàn dưới ngưỡng 150 req/30s của Nhanh)
        self.rate_limit_delay = rate_limit_delay

    def is_configured(self) -> bool:
        """Kiểm tra xem credentials đã được điền hợp lệ hay chưa."""
        placeholders = {"", "your_app_id_here", "your_business_id_here", "your_access_token_here"}
        return (
            self.app_id not in placeholders
            and self.business_id not in placeholders
            and self.access_token not in placeholders
        )

    def validate_or_warn(self) -> bool:
        """Thông báo lỗi nếu chưa cấu hình API."""
        if not self.is_configured():
            print("\n" + "=" * 60)
            print("⚠️  [CẢNH BÁO] CHƯA CẤU HÌNH ĐẦY ĐỦ THÔNG TIN API NHANH.VN")
            print("Vui lòng cập nhật các biến sau trong file .env:")
            print(f"  - NHANH_APP_ID: {'[ĐÃ CÓ]' if self.app_id and self.app_id != 'your_app_id_here' else '[CHƯA CÓ]'}")
            print(f"  - NHANH_BUSINESS_ID: {'[ĐÃ CÓ]' if self.business_id and self.business_id != 'your_business_id_here' else '[CHƯA CÓ]'}")
            print(f"  - NHANH_ACCESS_TOKEN: {'[ĐÃ CÓ]' if self.access_token and self.access_token != 'your_access_token_here' else '[CHƯA CÓ]'}")
            print("=" * 60 + "\n")
            return False
        return True

    def post(self, endpoint: str, payload: dict = None, timeout: int = 30, max_retries: int = 3) -> dict:
        """
        Gọi phương thức POST đến API Nhanh.vn v3.0 kèm kiểm soát Rate Limit và tự động retry.
        """
        import time

        if not self.validate_or_warn():
            return {"success": False, "error": "Missing credentials", "raw": None}

        url = f"{self.BASE_URL}/{endpoint}?appId={self.app_id}&businessId={self.business_id}"
        headers = {
            "Authorization": self.access_token,
            "Content-Type": "application/json"
        }

        body = payload if payload is not None else {}

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(url, headers=headers, json=body, timeout=timeout)
                
                # Kiểm tra HTTP 429 Too Many Requests
                if response.status_code == 429:
                    print(f"⚠️ [Rate Limit HTTP 429] Chạm giới hạn gọi API (Lần {attempt}/{max_retries}). Tạm dừng 35 giây...")
                    time.sleep(35)
                    continue

                response.raise_for_status()
                res_json = response.json()

                # Kiểm tra lỗi Rate Limit từ body phản hồi của Nhanh.vn (ERR_429)
                if res_json.get("errorCode") == "ERR_429":
                    wait_sec = 35
                    print(f"⚠️ [Rate Limit ERR_429] Nhanh.vn yêu cầu chờ (Lần {attempt}/{max_retries}). Tạm nghỉ {wait_sec} giây...")
                    time.sleep(wait_sec)
                    continue

                # Delay an toàn giữa các request
                if self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

                return {
                    "success": True,
                    "code": res_json.get("code"),
                    "messages": res_json.get("messages", []),
                    "raw": res_json
                }

            except requests.exceptions.HTTPError as http_err:
                error_msg = f"HTTP Error: {http_err}"
                detail = ""
                try:
                    detail = response.text
                except Exception:
                    pass
                print(f"❌ [Lỗi HTTP] {error_msg}\nChi tiết phản hồi: {detail}")
                if attempt < max_retries:
                    time.sleep(3)
                    continue
                return {"success": False, "error": error_msg, "detail": detail, "raw": None}

            except requests.exceptions.RequestException as req_err:
                error_msg = f"Connection Error: {req_err}"
                print(f"❌ [Lỗi mạng/kết nối] {error_msg} (Thử lại {attempt}/{max_retries} sau 5s...)")
                if attempt < max_retries:
                    time.sleep(5)
                    continue
                return {"success": False, "error": error_msg, "raw": None}

    def fetch_list(
        self,
        endpoint: str,
        size: int = 50,
        next_cursor: dict = None,
        filters: dict = None,
        sort: dict = None
    ) -> dict:
        """
        Hàm helper chuẩn để lấy dữ liệu danh sách có phân trang v3.0 (cursor-based paginator).
        Lưu ý: Một số API như order/list không hỗ trợ sort, chỉ truyền sort khi cần thiết.
        """
        paginator = {"size": size}
        if sort:
            paginator["sort"] = sort
        if next_cursor:
            paginator["next"] = next_cursor

        payload = {
            "filters": filters or {},
            "paginator": paginator
        }

        result = self.post(endpoint, payload)
        if not result["success"]:
            return result

        raw = result["raw"]
        code = raw.get("code")
        
        # Nhanh.vn v3: code == 1 là thành công, code == 0 là có lỗi/thông báo
        if code != 1:
            msg = raw.get("messages", "Unknown error")
            print(f"⚠️ [API trả về lỗi] {msg}")
            return {
                "success": False,
                "code": code,
                "error": msg,
                "raw": raw,
                "items": []
            }

        data = raw.get("data", [])
        items = []
        paginator_info = raw.get("paginator", {}) or {}

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items", [])
            if not paginator_info:
                paginator_info = data.get("paginator", {}) or {}

        return {
            "success": True,
            "code": code,
            "items": items,
            "next_cursor": paginator_info.get("next"),
            "paginator": paginator_info,
            "raw": raw
        }
