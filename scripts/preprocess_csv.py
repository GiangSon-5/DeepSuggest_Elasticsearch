import pandas as pd
import json
import os
import sys
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Biến env vẫn tên là RAW_CSV_FILE, nhưng script sẽ tự xử lý
INPUT_FILE_PATH = os.getenv('RAW_CSV_FILE', 'data/raw_products.csv')
OUTPUT_CSV_UTF8 = os.getenv('PREPROCESSED_CSV_FILE', 'data/raw_products_utf8.csv')
OUTPUT_JSON = os.getenv('PREPROCESSED_JSON_FILE', 'data/mock_products.json')

def main():
    print(f"\n--- Bắt đầu quy trình tiền xử lý ---")
    print(f"⏳ Đang đọc file: {INPUT_FILE_PATH}...")

    if not os.path.exists(INPUT_FILE_PATH):
        print(f"❌ Lỗi: Không tìm thấy file {INPUT_FILE_PATH}.")
        print(f"ℹ️  Hãy chắc chắn biến RAW_CSV_FILE trong file .env trỏ đúng file (có thể là .csv hoặc .xlsx)")
        sys.exit(1)

    df = None
    file_extension = os.path.splitext(INPUT_FILE_PATH)[1].lower()

    # === PHẦN ĐỌC FILE ĐÃ SỬA ===
    if file_extension == '.csv':
        print("ℹ️  Phát hiện file .csv. Đang thử đọc (chỉ dùng UTF-8)...")
        encodings_to_try = ['utf-8-sig', 'utf-8'] # Chỉ dùng encoding Tiếng Việt
        for enc in encodings_to_try:
            try:
                df = pd.read_csv(INPUT_FILE_PATH, encoding=enc)
                print(f"✅ Đọc file CSV thành công với encoding='{enc}'")
                break
            except UnicodeDecodeError:
                print(f"   (Thử encoding '{enc}' thất bại)")
            except Exception as e:
                print(f"❌ Lỗi không xác định khi đọc CSV: {e}")
                sys.exit(1)

    elif file_extension in ['.xlsx', '.xls']:
        print(f"ℹ️  Phát hiện file {file_extension}. Đang thử đọc...")
        try:
            # engine='openpyxl' là cần thiết cho .xlsx
            df = pd.read_excel(INPUT_FILE_PATH, engine='openpyxl')
            print(f"✅ Đọc file Excel thành công.")
        except ImportError:
            print(f"❌ Lỗi: Cần cài đặt thư viện 'openpyxl'.")
            print(f"ℹ️  Chạy lệnh: pip install openpyxl")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Lỗi không xác định khi đọc Excel: {e}")
            sys.exit(1)
    
    else:
        print(f"❌ Lỗi: Định dạng file '{file_extension}' không được hỗ trợ.")
        print(f"ℹ️  Vui lòng cung cấp file .csv hoặc .xlsx.")
        sys.exit(1)

    # === KẾT THÚC PHẦN ĐỌC FILE ===

    if df is None:
        print(f"❌ Lỗi: Không thể đọc dữ liệu từ file '{INPUT_FILE_PATH}'.")
        print(f"ℹ️  Nếu là file CSV, hãy đảm bảo nó được lưu ở dạng UTF-8 hoặc UTF-8-SIG.")
        sys.exit(1)

    # Phần lưu file CSV dự phòng (vẫn giữ)
    try:
        os.makedirs(os.path.dirname(OUTPUT_CSV_UTF8), exist_ok=True)
        df.to_csv(OUTPUT_CSV_UTF8, index=False, encoding='utf-8-sig')
        print(f"💾 Đã tạo bản sao CSV chuẩn UTF-8-SIG tại: {OUTPUT_CSV_UTF8}")
    except Exception as e:
        print(f"⚠️ Cảnh báo: Không thể ghi file UTF-8 '{OUTPUT_CSV_UTF8}': {e}")

    
    # === PHẦN KIỂM TRA VÀ XỬ LÝ (GIỮ NGUYÊN) ===
    required_cols = ['id', 'name', 'description', 'price', 'image_url', 'category']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Lỗi: File đầu vào thiếu các cột bắt buộc: {', '.join(missing_cols)}")
        sys.exit(1)

    # Đảm bảo ID là duy nhất và là chuỗi
    # Chuyển đổi ID sang chuỗi, loại bỏ .0 nếu có (thường gặp khi đọc từ Excel)
    df['id'] = df['id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df.dropna(subset=['id'], inplace=True)
    duplicated_ids = df[df.duplicated('id', keep=False)]['id'].unique()
    if len(duplicated_ids) > 0:
        print(f"⚠️ Cảnh báo: Tìm thấy ID sản phẩm trùng lặp:")
        for dup_id in duplicated_ids: print(f"  - ID: {dup_id}")
        print("ℹ️  Xóa các dòng trùng lặp ID, chỉ giữ lại dòng đầu tiên.")
        df.drop_duplicates(subset=['id'], keep='first', inplace=True)

    df['name'] = df['name'].fillna('Không có tên').astype(str).str.strip()
    df['description'] = df['description'].fillna('').astype(str).str.strip()
    df['category'] = df['category'].fillna('Chưa phân loại').astype(str).str.strip()
    df['image_url'] = df['image_url'].fillna('').astype(str).str.strip()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')

    # Chuyển NaN (xuất hiện sau pd.to_numeric) thành None (null trong JSON)
    df = df.replace({np.nan: None})

    products = df.to_dict('records')

    try:
        os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=4)

        print(f"✅ Tiền xử lý thành công! Đã lưu {len(products)} sản phẩm vào {OUTPUT_JSON}")
        print("--- Kết thúc quy trình tiền xử lý ---")

    except Exception as e:
        print(f"❌ Lỗi khi ghi file JSON '{OUTPUT_JSON}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()