# main.py (Sửa lại endpoint /products để unpack)
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .es_client import es_client, embedding_model # Import đúng
from typing import List, Optional
import os

app = FastAPI(
    title="Product Recommendation API (Keyword + Semantic)",
    description="API tìm kiếm và gợi ý sản phẩm."
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

INDEX_NAME = os.getenv("INDEX_NAME", "products")

@app.on_event("startup")
async def startup_event():
    if es_client is None: raise RuntimeError("Không thể kết nối tới Elasticsearch.")
    if embedding_model is None: print("⚠️ CẢNH BÁO: Mô hình embedding chưa tải xong...")
    print("✅ FastAPI đã khởi động và kết nối ES thành công.")

@app.get("/")
def read_root(): return {"message": "Welcome to the Recommendation API!"}

# --- ENDPOINT KEYWORD SEARCH (Giữ nguyên) ---
@app.get("/search-keyword")
async def keyword_search_endpoint(
    query: str = Query(..., min_length=1),
    category: Optional[str] = Query(None),
    size: int = Query(20, ge=1, le=100)
):
    if es_client is None: raise HTTPException(status_code=503, detail="ES client lỗi.")
    try:
        results = es_client.keyword_search(
            index_name=INDEX_NAME, query_text=query,
            category_filter=category, size=size
        )
        return results # Trả về list [...]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi keyword search: {e}")

# --- ENDPOINT SEMANTIC SUGGESTIONS (Giữ nguyên) ---
@app.get("/search-semantic-suggestions")
async def semantic_suggestions_endpoint(
    query: str = Query(..., min_length=1),
    category: Optional[str] = Query(None)
):
    if es_client is None: raise HTTPException(status_code=503, detail="ES client lỗi.")
    if embedding_model is None: raise HTTPException(status_code=503, detail="Mô hình embedding lỗi.")
    try:
        results = await es_client.semantic_search_suggestions(
            index_name=INDEX_NAME, query_text=query,
            category_filter=category, k=5
        )
        return results # Trả về list [{_id, product, score}, ...]
    except RuntimeError as e: raise HTTPException(status_code=500, detail=str(e))
    except Exception as e: raise HTTPException(status_code=500, detail=f"Lỗi semantic suggestions: {e}")

# --- ENDPOINT /products (SỬA Ở ĐÂY) ---
@app.get("/products")
async def get_products(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    if es_client is None: raise HTTPException(status_code=503, detail="ES client lỗi.")
    try:
        # 1. Gọi search_products, nó trả về dict {"data": [...], "total": N}
        result_dict = es_client.search_products(
            index_name=INDEX_NAME,
            category_filter=category,
            page=page,
            size=size
        )
        # 2. "Trải" dict đó ra cùng với page và size
        return {"page": page, "size": size, **result_dict} # Dùng ** để unpack
        # Kết quả trả về frontend sẽ là: {"page": 1, "size": 20, "data": [...], "total": N}
        # Frontend (app.js) sẽ đọc result.data -> là MỘT MẢNG (list) -> OK
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải sản phẩm: {e}")
# --- KẾT THÚC SỬA /products ---

# --- Endpoint /recommend và /categories (Giữ nguyên) ---
@app.get("/recommend/{product_doc_id}")
async def get_recommendations(product_doc_id: str):
    if es_client is None: raise HTTPException(status_code=503, detail="ES client lỗi.")
    try:
        original_doc = es_client.get_document(INDEX_NAME, product_doc_id)
        if not original_doc: raise HTTPException(status_code=404, detail=f"Không tìm thấy ID: {product_doc_id}")
        product_source = {k: v for k, v in original_doc.items() if k != '_id'}
        query_vector = product_source.get("product_embedding")
        if not query_vector: raise HTTPException(status_code=500, detail="Thiếu embedding vector")
        recommendations = es_client.knn_search(
            index_name=INDEX_NAME, query_vector=query_vector, k=5, exclude_id=product_doc_id
        )
        return {"original_product": product_source, "recommendations": recommendations}
    except HTTPException as he: raise he
    except Exception as e: raise HTTPException(status_code=500, detail=f"Lỗi gợi ý: {e}")

@app.get("/categories")
async def get_categories():
    if es_client is None: raise HTTPException(status_code=503, detail="ES client lỗi.")
    try:
        query = {"size": 0, "aggs": {"unique_categories": {"terms": {"field": "category", "size": 100}}}}
        res = es_client.client.search(index=INDEX_NAME, body=query, request_timeout=30)
        categories = [bucket["key"] for bucket in res["aggregations"]["unique_categories"]["buckets"]]
        categories.sort()
        return categories
    except Exception as e: print(f"Lỗi lấy categories: {e}"); return []