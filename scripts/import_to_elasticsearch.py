import json
import sys
import os
from elasticsearch import Elasticsearch, helpers
from dotenv import load_dotenv

load_dotenv()

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
INDEX_NAME = os.getenv("INDEX_NAME", "products")
INPUT_JSON = os.getenv("EMBEDDED_JSON_FILE", "data/mock_products_with_embedding.json")
try:
    VECTOR_DIM = int(os.getenv("VECTOR_DIM", 384))
except ValueError:
    print("❌ Lỗi: VECTOR_DIM trong .env phải là số nguyên.")
    sys.exit(1)

def get_es_mapping():
    return {
        "properties": {
            "id": {"type": "keyword"}, # ID gốc từ CSV
            "name": {"type": "text", "analyzer": "standard"},
            "description": {"type": "text", "analyzer": "standard"},
            "category": {"type": "keyword"},
            "price": {"type": "float"},
            "image_url": {"type": "keyword", "index": False},
            "data_hash": {"type": "keyword", "index": False},
            "product_embedding": {
                "type": "dense_vector", "dims": VECTOR_DIM,
                "index": "true", "similarity": "cosine"
            }
        }
    }

def connect_es():
    try:
        es = Elasticsearch(hosts=[ES_HOST], verify_certs=False, ssl_show_warn=False)
        if not es.ping(): raise ConnectionError("Ping tới Elasticsearch thất bại.")
        print(f"✅ Kết nối thành công tới Elasticsearch tại {ES_HOST}")
        return es
    except Exception as e:
        print(f"❌ Lỗi kết nối Elasticsearch: {e}")
        sys.exit(1)

def load_json_data(file_path, encoding='utf-8-sig'):
    if not os.path.exists(file_path):
        print(f"❌ Lỗi: Không tìm thấy file dữ liệu '{file_path}'.")
        print("ℹ️ Chạy script 'embed_to_json.py' trước?")
        sys.exit(1)
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            data = json.load(f)
            if not isinstance(data, list):
                print(f"❌ Lỗi: File JSON '{file_path}' không phải list.")
                sys.exit(1)
            return data
    except json.JSONDecodeError:
        print(f"❌ Lỗi: File {file_path} lỗi JSON.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi đọc file {file_path}: {e}")
        sys.exit(1)

def generate_bulk_actions(products, index_name):
    """ Dùng ID gốc ('id') làm _id của Elasticsearch """
    for product in products:
        doc_id = product.get('id')
        if not doc_id:
             print(f"⚠️ Cảnh báo: Bỏ qua sản phẩm thiếu 'id': {product.get('name')}")
             continue
        yield { "_index": index_name, "_id": doc_id, "_source": product }

def main():
    print(f"\n--- Bắt đầu quy trình nạp dữ liệu vào Elasticsearch ---")
    es = connect_es()
    mapping = get_es_mapping()

    try:
        if es.indices.exists(index=INDEX_NAME):
            print(f"⏳ Index '{INDEX_NAME}' đã tồn tại. Đang xóa...")
            es.indices.delete(index=INDEX_NAME, ignore=[400, 404])
        print(f"⏳ Đang tạo index '{INDEX_NAME}' mới...")
        es.indices.create(index=INDEX_NAME, mappings=mapping)
        print("✅ Tạo index thành công.")
    except Exception as e:
        print(f"❌ Lỗi khi thiết lập index '{INDEX_NAME}': {e}")
        sys.exit(1)

    products = load_json_data(INPUT_JSON)
    if not products:
        print("⚠️ Không có sản phẩm nào để nạp.")
        return

    print(f"⏳ Chuẩn bị nạp {len(products)} sản phẩm vào '{INDEX_NAME}'...")
    actions = generate_bulk_actions(products, INDEX_NAME)
    success_count = 0
    fail_count = 0

    try:
        success_count, failed_items = helpers.bulk(es, actions, raise_on_error=False, raise_on_exception=False, request_timeout=60) # Tăng timeout
        fail_count = len(failed_items)

        print(f"\n--- ✅ HOÀN TẤT ---")
        print(f"📥 Nạp thành công: {success_count} sản phẩm.")
        if fail_count > 0:
            print(f"❌ Thất bại: {fail_count} sản phẩm.")
            for i, fail_info in enumerate(failed_items[:5]):
                 error_details = fail_info.get('index', {}).get('error', {})
                 doc_id = fail_info.get('index', {}).get('_id', 'N/A')
                 print(f"  - ID: {doc_id}, Lỗi: {error_details.get('reason', error_details)}")
        if success_count < len(products):
             print(f"⚠️ Lưu ý: Số lượng nạp thành công ít hơn số sản phẩm trong file.")

    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng khi thực hiện bulk import: {e}")

if __name__ == "__main__":
    main()