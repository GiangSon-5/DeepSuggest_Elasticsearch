import pandas as pd
import json
import os
import sys
from dotenv import load_dotenv
import numpy as np # Import numpy

load_dotenv()

INPUT_CSV = os.getenv('RAW_CSV_FILE', 'data/raw_products.csv')
OUTPUT_CSV_UTF8 = os.getenv('PREPROCESSED_CSV_FILE', 'data/raw_products_utf8.csv')
OUTPUT_JSON = os.getenv('PREPROCESSED_JSON_FILE', 'data/mock_products.json')

def main():
    print(f"\n--- Bắt đầu quy trình tiền xử lý CSV ---")
    print(f"⏳ Đang đọc file: {INPUT_CSV}...")

    if not os.path.exists(INPUT_CSV):
        print(f"❌ Lỗi: Không tìm thấy file {INPUT_CSV}.")
        sys.exit(1)

    encodings_to_try = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    df = None
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(INPUT_CSV, encoding=enc)
            print(f"✅ Đọc file CSV thành công với encoding='{enc}'")
            break
        except UnicodeDecodeError:
            print(f"   (Thử encoding '{enc}' thất bại)")
        except Exception as e:
            print(f"❌ Lỗi không xác định khi đọc file CSV với encoding '{enc}': {e}")
            sys.exit(1)

    if df is None:
        print(f"❌ Lỗi: Không thể đọc file CSV '{INPUT_CSV}'.")
        sys.exit(1)

    try:
        os.makedirs(os.path.dirname(OUTPUT_CSV_UTF8), exist_ok=True)
        df.to_csv(OUTPUT_CSV_UTF8, index=False, encoding='utf-8-sig')
        print(f"💾 Đã tạo bản sao CSV chuẩn UTF-8-SIG tại: {OUTPUT_CSV_UTF8}")
    except Exception as e:
        print(f"⚠️ Cảnh báo: Không thể ghi file UTF-8 '{OUTPUT_CSV_UTF8}': {e}")

    required_cols = ['id', 'name', 'description', 'price', 'image_url', 'category']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Lỗi: File CSV thiếu các cột bắt buộc: {', '.join(missing_cols)}")
        sys.exit(1)

    # Đảm bảo ID là duy nhất và là chuỗi
    df['id'] = df['id'].astype(str).str.strip()
    df.dropna(subset=['id'], inplace=True) # Xóa dòng thiếu ID
    duplicated_ids = df[df.duplicated('id', keep=False)]['id'].unique()
    if len(duplicated_ids) > 0:
        print(f"⚠️ Cảnh báo: Tìm thấy ID sản phẩm trùng lặp:")
        for dup_id in duplicated_ids: print(f"  - ID: {dup_id}")
        print("ℹ️ Xóa các dòng trùng lặp ID, chỉ giữ lại dòng đầu tiên.")
        df.drop_duplicates(subset=['id'], keep='first', inplace=True)

    df['name'] = df['name'].fillna('Không có tên').astype(str).str.strip()
    df['description'] = df['description'].fillna('').astype(str).str.strip()
    df['category'] = df['category'].fillna('Chưa phân loại').astype(str).str.strip()
    df['image_url'] = df['image_url'].fillna('').astype(str).str.strip()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')

    # Chuyển NaN thành None (null trong JSON) dùng numpy
    df = df.replace({np.nan: None})

    products = df.to_dict('records')

    try:
        os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=4)

        print(f"✅ Tiền xử lý thành công! Đã lưu {len(products)} sản phẩm vào {OUTPUT_JSON}")
        print("--- Kết thúc quy trình tiền xử lý CSV ---")

    except Exception as e:
        print(f"❌ Lỗi khi ghi file JSON '{OUTPUT_JSON}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()