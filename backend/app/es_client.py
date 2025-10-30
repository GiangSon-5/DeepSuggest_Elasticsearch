# es_client.py (Sửa semantic_search_suggestions để nối category)
import os
from elasticsearch import Elasticsearch, helpers
from dotenv import load_dotenv
import asyncio
import json
from sentence_transformers import SentenceTransformer
import random

# --- Phần tải model (Giữ nguyên) ---
try:
    EMBEDDING_MODEL_NAME = os.getenv('MODEL_NAME', 'sentence-transformers/all-MiniLM-L6-v2')
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device='cpu')
    print(f"✅ Tải mô hình embedding '{EMBEDDING_MODEL_NAME}' thành công.")
except Exception as e:
    print(f"❌ LỖI NGHIÊM TRỌNG: Không thể tải mô hình embedding: {e}")
    embedding_model = None

load_dotenv()

class ESClient:
    def __init__(self):
        # (Giữ nguyên)
        host = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
        try:
            self.client = Elasticsearch(
                hosts=[host], verify_certs=False, ssl_show_warn=False, request_timeout=30
            )
            if not self.client.ping(): raise ConnectionError("ES ping failed.")
            print(f"✅ Kết nối ES thành công tại {host}")
        except Exception as e: print(f"❌ Lỗi kết nối ES: {e}"); raise

    # --- HÀM KEYWORD SEARCH (Giữ nguyên) ---
    def keyword_search(self, index_name, query_text, category_filter=None, size=20):
        # (Giữ nguyên code hàm này)
        if not query_text: return []
        keywords = query_text.split()
        if not keywords: return []
        should_clauses = []
        for keyword in keywords:
            should_clauses.append({"match": {"name": {"query": keyword, "boost": 2}}})
            should_clauses.append({"match": {"description": keyword}})
        query_body = {"size": size, "query": {"bool": {"should": should_clauses, "minimum_should_match": 1, "filter": []}}}
        if category_filter: query_body["query"]["bool"]["filter"].append({"term": {"category": category_filter}})
        try:
            print(f"🔍 Tìm kiếm Keyword (Keywords: {keywords}, Category: {category_filter})...")
            res = self.client.search(index=index_name, body=query_body)
            hits = [{"_id": hit['_id'], **hit['_source']} for hit in res['hits']['hits']]
            print(f"✅ Tìm thấy {len(hits)} kết quả Keyword.")
            return hits
        except Exception as e: print(f"❌ Lỗi Keyword Search: {e}"); return []
    # --- KẾT THÚC KEYWORD SEARCH ---


    # --- HÀM SEMANTIC SUGGESTIONS (SỬA ĐỂ NỐI CATEGORY VÀO TEXT) ---
    async def semantic_search_suggestions(self, index_name, query_text, category_filter=None, k=5):
        if embedding_model is None: raise RuntimeError("Mô hình embedding chưa tải.")

        # === THAY ĐỔI Ở ĐÂY ===
        # Nối category vào query_text nếu category được chọn
        text_to_embed = query_text
        if category_filter:
            text_to_embed = f"{category_filter} | {query_text}" # Ví dụ: "Laptop | mỏng nhẹ"
        # =====================

        print(f"🧠 Đang tạo embedding (suggestions) cho: '{text_to_embed}'") # Log text mới
        loop = asyncio.get_event_loop()
        try:
            # Dùng text_to_embed để tạo vector
            query_vector_np = await loop.run_in_executor(None, embedding_model.encode, text_to_embed)
            query_vector = query_vector_np.tolist()
        except Exception as e: raise RuntimeError(f"❌ Lỗi tạo embedding: {e}")

        # --- BỎ FILTER CATEGORY Ở ĐÂY ---
        # Elasticsearch sẽ tìm dựa trên vector đã bao gồm category
        # es_filters = []
        # if category_filter: es_filters.append({"term": {"category": category_filter}})
        # query_body = {"bool": {"filter": es_filters}} if es_filters else None
        # --- KẾT THÚC BỎ FILTER ---

        knn_query = {"field": "product_embedding", "query_vector": query_vector, "k": k, "num_candidates": 50}

        try:
            # Chỉ cần tìm kNN, không cần query filter nữa
            res = self.client.search(index=index_name, knn=knn_query, size=k, _source=True) # Bỏ query=query_body
            hits = [{"_id": hit['_id'], "product": hit['_source'], "score": hit['_score']} for hit in res['hits']['hits']]
            print(f"✅ Tìm thấy {len(hits)} gợi ý Semantic (combined text).")
            return hits
        except Exception as e:
            print(f"❌ Lỗi Semantic Suggestions (combined text): {e}")
            return []
    # --- KẾT THÚC SEMANTIC SUGGESTIONS ---

    # --- Hàm search_products (Giữ nguyên) ---
    def search_products(self, index_name, category_filter=None, page=1, size=20):
        # (Giữ nguyên code hàm này)
        try:
            start_from = (page - 1) * size
            query_body = {"from": start_from, "size": size, "query": {}}
            if category_filter: query_body["query"] = {"term": {"category": category_filter}}
            else: query_body["query"] = {"match_all": {}}
            print(f"🔍 Lấy sản phẩm (Category: {category_filter}, Page: {page}, Size: {size})...")
            res = self.client.search(index=index_name, body=query_body)
            hits = [{"_id": hit['_id'], **hit['_source']} for hit in res['hits']['hits']]
            total_hits = res['hits']['total']['value']
            print(f"✅ Lấy {len(hits)}/{total_hits} sản phẩm.")
            return {"data": hits, "total": total_hits}
        except Exception as e: print(f"❌ Lỗi search_products: {e}"); return {"data": [], "total": 0}
    # --- KẾT THÚC search_products ---

    # --- Các hàm khác (create_index, index_document, get_document, knn_search) - Giữ nguyên ---
    def create_index(self, index_name, mapping): #... (code cũ)
        try:
            if self.client.indices.exists(index=index_name): self.client.indices.delete(index=index_name, ignore=[400, 404])
            self.client.indices.create(index=index_name, mappings=mapping)
            print("✅ Tạo index thành công.")
        except Exception as e: print(f"❌ Lỗi tạo index: {e}")

    def index_document(self, index_name, doc_id, document): #... (code cũ)
        try: self.client.index(index=index_name, id=doc_id, document=document)
        except Exception as e: print(f"❌ Lỗi index doc {doc_id}: {e}")

    def get_document(self, index_name, doc_id): #... (code cũ)
        try:
            res = self.client.get(index=index_name, id=doc_id)
            return {"_id": res['_id'], **res['_source']}
        except Exception as e: return None

    def knn_search(self, index_name, query_vector, k=5, exclude_id=None): #... (code cũ)
        try:
            knn_query = {"field": "product_embedding", "query_vector": query_vector, "k": k + 1, "num_candidates": 50}
            query_filter = {"bool": {"must_not": [{"term": {"_id": exclude_id}}]}} if exclude_id else None
            res = self.client.search(index=index_name, knn=knn_query, query=query_filter, size=k, _source=True)
            hits = [{"_id": hit['_id'], "product": hit['_source'], "score": hit['_score']} for hit in res['hits']['hits']]
            return hits
        except Exception as e: print(f"❌ Lỗi kNN: {e}"); return []


# --- Tạo instance (Giữ nguyên) ---
try:
    es_client = ESClient()
except ConnectionError as e: print(f"❌ Không thể khởi tạo ESClient: {e}"); es_client = None