
# 🧠 Hệ thống Gợi ý Sản phẩm (Elasticsearch & Embedding)

Dự án demo hệ thống **gợi ý sản phẩm tương tự (content-based)** sử dụng **vector embedding** được tính toán offline và tìm kiếm **kNN trên Elasticsearch**.  
Phần **Backend** được viết bằng **FastAPI (siêu nhẹ)** và **Frontend** bằng **HTML/CSS/JS**.

---

## 🏗️ Cấu trúc thư mục


```css
TTTN/
├── backend/              # Code backend API (FastAPI)
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── data/                 # Dữ liệu (CSV, JSON)
├── frontend/             # Giao diện người dùng (HTML, CSS, JS)
├── scripts/              # Các script xử lý dữ liệu offline (Python)
│   ├── requirements.txt  # Thư viện cho scripts
│   └── ... (preprocess, embed, import, evaluate)
├── .env                  # File cấu hình biến môi trường
├── docker-compose.yml    # Cấu hình Docker
├── run_all.py            # Script điều phối chính
└── README.md             # File hướng dẫn này

```

---

## ⚙️ Yêu cầu hệ thống

- **Python:** Phiên bản 3.10 (nên trùng với bản trong Dockerfile)
- **Docker & Docker Compose:** Cài Docker Desktop và đảm bảo đang chạy
- **Git:** *(Tùy chọn)* để quản lý mã nguồn

---

## 🚀 Cài đặt ban đầu

Các bước này **chỉ cần làm một lần** khi thiết lập dự án.

### 1️⃣ Mở Terminal và di chuyển đến thư mục dự án


>cd TTTN


### 2️⃣ Tạo môi trường ảo (`venv`) cho scripts

> Đảm bảo đang dùng Python 3.10 hoặc 3.11


>python -m venv venv


### 3️⃣ Kích hoạt `venv`

* **Windows:**


> .\venv\Scripts\activate

* **macOS / Linux:**

>source venv/bin/activate

> Nếu thấy `(venv)` ở đầu dòng lệnh là đã kích hoạt thành công.

---

### 4️⃣ Cài đặt thư viện cần thiết

Lần lượt chạy các lệnh sau:


# Cài các thư viện cho scripts
>pip install -r scripts/requirements.txt

# Đảm bảo setuptools đúng phiên bản
>pip install "setuptools<58"




---

### 5️⃣ Chuẩn bị dữ liệu

Đặt file dữ liệu gốc `raw_products.csv` vào thư mục `data/`:

>data/raw_products.csv


---

### 6️⃣ Cấu hình `.env`

Tạo file `.env` tại thư mục gốc (hoặc sao chép từ `.env.example` nếu có)
và cập nhật các biến môi trường:


>ES_HOST=http://localhost:9200
>INDEX_NAME=products
>EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2


---

### 7️⃣ Build Docker Images (lần đầu)

Lệnh này sẽ đọc `Dockerfile` và `docker-compose.yml` để build image cho backend.
Lần đầu sẽ hơi lâu do Docker phải tải base image và dependencies.


docker-compose build --no-cache


> Chỉ cần chạy lại khi bạn **thay đổi Dockerfile** hoặc `backend/requirements.txt`.

---

## ▶️ Chạy & Quản lý ứng dụng

Sau khi thiết lập xong, bạn có thể chạy hệ thống theo các cách sau:

---

### 🧩 1. Chạy Toàn Bộ Pipeline (Lần đầu / Khi có dữ liệu mới)

Chạy toàn bộ quy trình:

* Khởi động Docker (Elasticsearch + Backend)
* Xử lý dữ liệu (preprocess → embed → import)


>python run_all.py


**Dùng khi:**

* Lần đầu thiết lập dự án
* Cập nhật dữ liệu `data/raw_products.csv`
* Hoặc sau khi sửa code trong `backend/` mà cần build lại image

---

### ⚡ 2. Chỉ Khởi động Dịch vụ Docker (sử dụng hàng ngày)

Khi bạn chỉ muốn chạy ứng dụng với dữ liệu đã có:


>docker-compose up -d


>> Cờ `-d` giúp chạy nền (background).

**Dùng khi:**

* Chỉ muốn mở ứng dụng web để demo
* Hoặc sau khi khởi động lại máy

---

### 🔁 3. Cập nhật khi Sửa Code Backend

Nếu chỉ thay đổi code trong `backend/app/` mà không đổi dữ liệu:


# Build lại image backend (nhanh vì dùng cache)
>docker-compose build backend

# Chạy lại container backend
>docker-compose up -d


> Không cần chạy lại `run_all.py`.

---

### 🔄 4. Khởi động lại một dịch vụ (ví dụ: Backend)

Khi backend bị lỗi hoặc muốn nạp lại biến môi trường:


>docker-compose restart backend


---

### 🛑 5. Dừng ứng dụng

Dừng các container đang chạy nền:


>docker-compose down


Nếu muốn **xóa luôn volume dữ liệu Elasticsearch** (sẽ mất toàn bộ dữ liệu):


>docker-compose down -v


---

## 🧹 Dọn dẹp Docker

Giúp giải phóng dung lượng ổ đĩa và cache build cũ.

* **Dọn dẹp cơ bản (an toàn, nên dùng thường xuyên):**

  
  docker system prune -f
  

* **Dọn dẹp triệt để (xóa cả cache, image, container cũ):**

  
  docker system prune -a -f
  

> Script `run_all.py` hỗ trợ thêm cờ `--prune-docker` để tự động dọn sau khi chạy xong.

---

## 📊 Đánh giá mô hình (Tùy chọn)

Sau khi có dữ liệu trong Elasticsearch (đã chạy `run_all.py`):


python scripts/evaluate_similarity.py


> Đảm bảo đã cài `numpy` và `ml_metrics` trong `venv`.

---

## 💡 Gợi ý kiểm tra nhanh

* Kiểm tra Elasticsearch có hoạt động không:


> http://localhost:9200/_cat/indices?v

* Kiểm tra backend (FastAPI):


> http://localhost:8000/docs


---

## 🎯 Kết luận

Dự án giúp hiểu rõ quy trình **xây dựng hệ thống gợi ý sản phẩm dựa trên nội dung (Content-Based)**:

1. Tiền xử lý dữ liệu
2. Tính toán vector embedding
3. Lưu và tìm kiếm bằng Elasticsearch
4. Kết hợp backend API + frontend hiển thị kết quả


