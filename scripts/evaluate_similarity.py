import os
import sys
import json
from elasticsearch import Elasticsearch, NotFoundError
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np

try:
    import ml_metrics
except ImportError:
    print("⚠️ Cảnh báo: Thư viện 'ml_metrics' chưa được cài đặt (pip install ml_metrics).")
    ml_metrics = None

load_dotenv()
ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
INDEX_NAME = os.getenv("INDEX_NAME", "products")
TOP_K = 5

def connect_es():
    try:
        es = Elasticsearch(hosts=[ES_HOST], verify_certs=False, ssl_show_warn=False)
        if not es.ping(): raise ConnectionError("Ping tới Elasticsearch thất bại.")
        print(f"✅ Kết nối thành công tới Elasticsearch tại {ES_HOST}")
        return es
    except Exception as e:
        print(f"❌ Lỗi kết nối Elasticsearch: {e}")
        sys.exit(1)

def get_all_products_with_embedding(es, index_name):
    print(f"⏳ Đang tải tất cả sản phẩm và embedding từ index '{index_name}'...")
    all_hits = []
    try:
        resp = es.search(
            index=index_name, query={"match_all": {}}, scroll='2m', size=100,
            _source_includes=["id", "name", "category", "product_embedding"]
        )
        scroll_id = resp['_scroll_id']
        all_hits.extend(resp['hits']['hits'])

        while len(resp['hits']['hits']):
            resp = es.scroll(scroll_id=scroll_id, scroll='2m')
            scroll_id = resp['_scroll_id']
            all_hits.extend(resp['hits']['hits'])

        print(f"✅ Đã tải {len(all_hits)} sản phẩm.")
        try: es.clear_scroll(scroll_id=scroll_id)
        except NotFoundError: pass

        # Trả về list {_id: ..., id: ..., name: ..., ...}
        products = [{"_id": hit['_id'], **hit['_source']} for hit in all_hits]
        return products
    except Exception as e:
        print(f"❌ Lỗi khi tải sản phẩm từ Elasticsearch: {e}")
        return []

def find_similar_for_eval(es, index_name, query_vector, exclude_doc_id, k):
    """ Tìm k sản phẩm tương tự, trả về list {_id, category, score} """
    try:
        knn_query = {"field": "product_embedding", "query_vector": query_vector, "k": k + 1, "num_candidates": 50}
        query_filter = {"bool": {"must_not": [{"term": {"_id": exclude_doc_id}}]}}
        res = es.search(
            index=index_name, knn=knn_query, query=query_filter, size=k,
            _source_includes=["category"] # Chỉ cần category
        )
        # Trả về _id của ES
        return [{"_id": hit['_id'], "category": hit['_source'].get('category'), "score": hit['_score']}
                for hit in res['hits']['hits']]
    except Exception as e:
        return []

def calculate_metrics(query_product, recommendations, k):
    if not recommendations:
        return {"avg_cosine": 0.0, "precision_at_k": 0.0, "relevant_list": []}

    query_category = query_product.get('category')
    num_correct = 0
    total_cosine_sim = 0.0
    relevant_doc_ids_in_order = [] # Lưu _id của ES

    for reco in recommendations:
        es_score = reco['score']
        cosine_sim = max(0.0, (es_score * 2) - 1)
        total_cosine_sim += cosine_sim

        if reco['category'] == query_category:
            num_correct += 1
            relevant_doc_ids_in_order.append(reco['_id']) # Thêm _id đúng

    avg_cosine = total_cosine_sim / len(recommendations)
    precision_at_k = num_correct / k

    return {
        "avg_cosine": avg_cosine,
        "precision_at_k": precision_at_k,
        "relevant_list": relevant_doc_ids_in_order
    }

def main():
    print("\n--- Bắt đầu quy trình đánh giá hệ thống gợi ý ---")
    es = connect_es()
    all_products = get_all_products_with_embedding(es, INDEX_NAME)

    if not all_products:
        print("❌ Không có sản phẩm nào để đánh giá.")
        return

    total_avg_cosine = 0.0
    total_precision_at_k = 0.0
    all_actual_relevant_ids = []
    all_predicted_relevant_ids = []
    evaluated_count = 0

    print(f"\n⚙️ Đánh giá Top-{TOP_K} gợi ý cho {len(all_products)} sản phẩm...")
    for product in tqdm(all_products, desc="📊 Đang đánh giá"):
        product_doc_id = product.get('_id') # ID của ES
        query_vector = product.get('product_embedding')
        query_category = product.get('category')

        if not product_doc_id or not query_vector or not query_category:
            continue
        evaluated_count += 1

        recommendations = find_similar_for_eval(es, INDEX_NAME, query_vector, product_doc_id, TOP_K)
        metrics = calculate_metrics(product, recommendations, TOP_K)

        total_avg_cosine += metrics['avg_cosine']
        total_precision_at_k += metrics['precision_at_k']

        if ml_metrics:
            # Ground truth là list các _id khác cùng category
            actual_relevant = [p['_id'] for p in all_products if p.get('category') == query_category and p.get('_id') != product_doc_id]
            all_actual_relevant_ids.append(actual_relevant)
            all_predicted_relevant_ids.append(metrics['relevant_list'])

    if evaluated_count == 0:
        print("❌ Không có sản phẩm hợp lệ nào được đánh giá.")
        return

    mean_avg_cosine = total_avg_cosine / evaluated_count
    mean_precision_at_k = total_precision_at_k / evaluated_count
    mean_ap = "N/A"

    if ml_metrics and all_actual_relevant_ids and all_predicted_relevant_ids:
        try:
             predicted_top_k = [pred[:TOP_K] for pred in all_predicted_relevant_ids]
             mean_ap = ml_metrics.mapk(all_actual_relevant_ids, predicted_top_k, k=TOP_K)
             mean_ap = f"{mean_ap:.4f}"
        except Exception as e:
            print(f"⚠️ Lỗi khi tính mAP@K: {e}")
            mean_ap = "Lỗi tính toán"
    elif not ml_metrics:
         mean_ap = "N/A (cần ml_metrics)"

    print("\n" + "="*50)
    print(f"--- 📈 KẾT QUẢ ĐÁNH GIÁ (K={TOP_K}) ---")
    print("="*50)
    print(f"  - Số sản phẩm đánh giá hợp lệ: {evaluated_count}")
    print(f"  - Average Cosine Similarity trung bình: {mean_avg_cosine:.4f}")
    print(f"  - Mean Precision@{TOP_K} (P@{TOP_K}):      {mean_precision_at_k:.4f}")
    print(f"  - Mean Average Precision@{TOP_K} (mAP@{TOP_K}): {mean_ap}")
    print("-"*50)
    print("ℹ️ Ground Truth: Cùng Category.")
    print("="*50)

if __name__ == "__main__":
    main()