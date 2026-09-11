import sys
import argparse
from pathlib import Path

# Đảm bảo import được src
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.nhanh_client import NhanhClient
from src.crawl_product import crawl_products
from src.crawl_customer import crawl_customers
from src.crawl_order import crawl_orders


def main():
    parser = argparse.ArgumentParser(description="Nhanh.vn ETL Data Crawler")
    parser.add_argument(
        "--target",
        choices=["all", "product", "customer", "order"],
        default="all",
        help="Chọn đối tượng cần crawl (mặc định: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Số lượng bản ghi lấy mỗi đối tượng để test (mặc định: 5)",
    )

    args = parser.parse_args()

    client = NhanhClient()
    if not client.validate_or_warn():
        sys.exit(1)

    print("=" * 70)
    print("🚀 NHANH.VN ETL DATA PIPELINE - CHẾ ĐỘ TEST")
    print(f"App ID: {client.app_id} | Business ID: {client.business_id}")
    print(f"Mục tiêu: {args.target.upper()} | Số lượng mẫu: {args.limit}")
    print("=" * 70)

    if args.target in ("all", "product"):
        crawl_products(limit=args.limit)

    if args.target in ("all", "customer"):
        crawl_customers(limit=args.limit)

    if args.target in ("all", "order"):
        crawl_orders(limit=args.limit)

    print("\n" + "=" * 70)
    print("🎉 Hoàn tất quá trình crawl thử nghiệm!")
    print("Dữ liệu thô JSON đã được lưu trữ an toàn trong thư mục: data/raw/")
    print("=" * 70)


if __name__ == "__main__":
    main()
