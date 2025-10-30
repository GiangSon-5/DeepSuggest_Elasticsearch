// app.js (Logic tìm kiếm mới: Keyword + Semantic Suggestions + Category)
const API_URL = 'http://localhost:8000';

// DOM Elements
const productGrid = document.getElementById('product-grid'); // Lưới sản phẩm ban đầu
const allProductsSection = document.getElementById('all-products-section');

// === DOM Elements cho kết quả tìm kiếm (Đổi tên cho rõ ràng) ===
const keywordResultsSection = document.getElementById('keyword-results-section');
const keywordResultsTitle = document.getElementById('keyword-results-title');
const keywordResultsGrid = document.getElementById('keyword-results-grid');
const keywordMessage = document.getElementById('keyword-message');

const semanticSuggestionsSection = document.getElementById('semantic-suggestions-section');
const semanticTitle = document.getElementById('semantic-title');
const semanticSuggestionsGrid = document.getElementById('semantic-suggestions-grid');
const semanticMessage = document.getElementById('semantic-message');
// =====================================

const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const categorySelect = document.getElementById('category-select');

// === DOM Elements cho Modal (Giữ nguyên) ===
const modalElement = document.getElementById('product-modal');
const modalTitle = document.getElementById('modal-title');
const modalContent = document.getElementById('modal-content-main').querySelector('.modal-product-details');
const modalRecoList = document.getElementById('modal-recommendation-list');
// =====================================

let allCategories = [];
const formatter = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' });

/**
 * Hàm tạo đánh giá sao (Giữ nguyên)
 */
function createStarRating(rating) {
    const roundedRating = Math.round(rating * 2) / 2;
    const fullStars = Math.floor(roundedRating);
    const halfStar = roundedRating % 1 !== 0 ? 1 : 0;
    const emptyStars = 5 - fullStars - halfStar;
    let starsHTML = '';
    for (let i = 0; i < fullStars; i++) starsHTML += '<i class="fas fa-star"></i>';
    if (halfStar) starsHTML += '<i class="fas fa-star-half-alt"></i>';
    for (let i = 0; i < emptyStars; i++) starsHTML += '<i class="far fa-star"></i>';
    return `<div class="card-rating">${starsHTML}</div>`;
}

/**
 * Tạo HTML cho một thẻ sản phẩm (Giữ nguyên)
 * (Đã sửa ở lần trước để xử lý cả 2 cấu trúc)
 */
function createProductCardHTML(productData) {
    const isSemanticResult = productData && productData.hasOwnProperty('product') && productData.hasOwnProperty('score');
    const isKeywordOrInitial = productData && productData.hasOwnProperty('id') && !productData.hasOwnProperty('product');

    let product = null;
    let docId = productData ? productData._id : null;
    let score = null;

    if (isSemanticResult) {
        product = productData.product;
        score = productData.score;
    } else if (isKeywordOrInitial) {
        product = productData;
    }

    if (!product || !docId) {
        console.error("Dữ liệu sản phẩm không hợp lệ hoặc thiếu _id:", productData);
        return `<div class="product-card error-card"><p>Lỗi dữ liệu</p></div>`;
    }

    let seed = Math.random();
    if (product.id) { const m = ('' + product.id).match(/\d+$/); if (m) seed = parseInt(m[0], 10); }
    const rating = ((seed * 13) % 21) / 10 + 2.5;

    return `
        <div class="product-card" data-doc-id="${docId}" tabindex="0" title="${product.name || 'Sản phẩm'}">
            <div class="card-image-container">
                <img src="${product.image_url || 'placeholder.png'}" alt="${product.name || 'Hình ảnh sản phẩm'}" loading="lazy" onerror="this.onerror=null; this.src='placeholder.png';">
            </div>
            <div class="card-content">
                <h4>${product.name || 'N/A'}</h4>
                <span class="category">${product.category || 'N/A'}</span>
                ${createStarRating(rating)}
                <div class="card-footer">
                    <span class="price">${product.price ? formatter.format(product.price) : 'Liên hệ'}</span>
                    <button class="btn-detail" aria-label="Xem chi tiết ${product.name || ''}">Chi tiết</button>
                </div>
            </div>
            ${score ? `<div class="reco-score" title="Độ tương đồng: ${(score * 100).toFixed(1)}%">${(score * 100).toFixed(0)}%</div>` : ''}
        </div>
    `;
}

/**
 * Hiển thị sản phẩm lên lưới (Giữ nguyên)
 */
function displayProducts(products, gridElement, messageElement) {
    gridElement.innerHTML = '';
    if (messageElement) messageElement.textContent = '';

    if (!products || products.length === 0) {
        const noProductMsg = 'Không có kết quả tìm kiếm.';
        if (messageElement) messageElement.textContent = noProductMsg;
        gridElement.innerHTML = `<p class="message">${noProductMsg}</p>`;
        return;
    }

    const cardsHTML = products.map(productData => {
         if(productData && productData._id) { return createProductCardHTML(productData); }
         else { console.warn("Dữ liệu không hợp lệ:", productData); return ''; }
    }).join('');
    gridElement.innerHTML = cardsHTML;
    addCardClickListeners(gridElement);
}

/**
 * Gọi API lấy danh sách sản phẩm ban đầu hoặc theo category
 * Sửa lại để nhận category
 */
async function fetchProducts(category = null, grid = productGrid, section = allProductsSection, msg = null) {
    grid.innerHTML = '<p class="message"><i class="fas fa-spinner fa-spin"></i> Đang tải...</p>';
    if (section) section.style.display = 'block';

    // Ẩn các section kết quả tìm kiếm khác
    if(grid !== keywordResultsGrid) keywordResultsSection.style.display = 'none';
    if(grid !== semanticSuggestionsGrid) semanticSuggestionsSection.style.display = 'none';
    if(grid !== productGrid) allProductsSection.style.display = 'none';

    try {
        const params = new URLSearchParams({ page: '1', size: '20' });
        if (category) {
            params.append('category', category);
        }
        // Gọi endpoint /products đã sửa
        const url = `${API_URL}/products?${params.toString()}`;

        const response = await fetch(url);
        if (!response.ok) throw await createApiError(response, 'Không tải được sản phẩm');
        const result = await response.json(); // API trả về { data: [...], total: N }

        displayProducts(result.data, grid, msg); // Hiển thị result.data

        // Cập nhật tiêu đề nếu là tìm theo category
        if (category && grid === keywordResultsGrid) {
            keywordResultsTitle.textContent = `Sản phẩm thuộc loại "${category}" (Tìm thấy ${result.total} sản phẩm)`;
        }

    } catch (error) {
        console.error('Lỗi khi tải sản phẩm:', error);
        const errorMsg = `❌ ${error.message}.`;
        if (msg) msg.textContent = errorMsg;
        grid.innerHTML = `<p class="message error">${errorMsg}</p>`;
    }
}

// --- Hàm fetchCategories, populateCategoryDropdown (Giữ nguyên) ---
async function fetchCategories() {
    try {
        const response = await fetch(`${API_URL}/categories`);
        if (!response.ok) { console.warn(`Lỗi ${response.status} khi tải categories.`); allCategories = []; }
        else { allCategories = await response.json(); }
        populateCategoryDropdown();
    } catch (error) { console.error('Lỗi mạng khi tải categories:', error); }
}
function populateCategoryDropdown() {
    const selectedValue = categorySelect.value;
    categorySelect.innerHTML = '<option value="">-- Tất cả loại --</option>';
    allCategories.forEach(category => {
        const option = document.createElement('option');
        option.value = category; option.textContent = category;
        categorySelect.appendChild(option);
    });
    if (allCategories.includes(selectedValue)) { categorySelect.value = selectedValue; }
}

/**
 * HÀM MỚI: Gọi API tìm kiếm keyword
 */
async function fetchKeywordSearch(queryText, category) {
    keywordResultsGrid.innerHTML = '<p class="message"><i class="fas fa-spinner fa-spin"></i> Đang tìm theo từ khóa...</p>';
    keywordMessage.textContent = '';
    keywordResultsTitle.textContent = `Kết quả khớp từ khóa cho "${queryText}"`+ (category ? ` trong "${category}"` : '');
    keywordResultsSection.style.display = 'block';

    try {
        const params = new URLSearchParams({ query: queryText, size: '20' });
        if (category) params.append('category', category);
        const url = `${API_URL}/search-keyword?${params.toString()}`;

        const response = await fetch(url);
        if (!response.ok) throw await createApiError(response, 'Tìm kiếm từ khóa thất bại');

        const results = await response.json(); // API trả về list [{_id:..., id:..., name:...}]
        displayProducts(results, keywordResultsGrid, keywordMessage); // Dữ liệu này không có 'product' lồng

    } catch (error) {
        console.error('Lỗi khi tìm kiếm keyword:', error);
        keywordResultsGrid.innerHTML = '';
        keywordMessage.textContent = `❌ ${error.message}.`;
    }
}

/**
 * HÀM MỚI: Gọi API lấy gợi ý semantic
 */
async function fetchSemanticSuggestions(queryText, category) {
    semanticSuggestionsGrid.innerHTML = '<p class="message"><i class="fas fa-spinner fa-spin"></i> Đang tìm gợi ý...</p>';
    semanticMessage.textContent = '';
    semanticTitle.textContent = 'Gợi ý liên quan (Semantic)';
    semanticSuggestionsSection.style.display = 'block';

    try {
        const params = new URLSearchParams({ query: queryText });
        if (category) params.append('category', category);
        const url = `${API_URL}/search-semantic-suggestions?${params.toString()}`;

        const response = await fetch(url);
        if (!response.ok) throw await createApiError(response, 'Lấy gợi ý thất bại');

        const suggestions = await response.json(); // API trả về list [{_id:..., product:..., score:...}]
        displayProducts(suggestions, semanticSuggestionsGrid, semanticMessage); // Dữ liệu này có 'product' lồng

    } catch (error) {
        console.error('Lỗi khi lấy gợi ý semantic:', error);
        semanticSuggestionsGrid.innerHTML = '';
        semanticMessage.textContent = `❌ ${error.message}.`;
    }
}


/**
 * Gọi API lấy chi tiết sản phẩm và gợi ý (cho Modal)
 */
async function fetchProductDetailsAndRecommendations(docId) {
    modalContent.innerHTML = '<p class="message"><i class="fas fa-spinner fa-spin"></i> Đang tải...</p>';
    modalRecoList.innerHTML = '<p class="message"><i class="fas fa-spinner fa-spin"></i> Đang tải...</p>';
    modalTitle.textContent = 'Đang tải...';
    MicroModal.show('product-modal', {
         onShow: (modal) => { const c = modal.querySelector('.modal-container'); if(c) c.scrollTop = 0; },
    });
    try {
        const response = await fetch(`${API_URL}/recommend/${docId}`);
        if (!response.ok) throw await createApiError(response, 'Lỗi tải chi tiết/gợi ý');
        const data = await response.json();
        const product = data.original_product;
        const recommendations = data.recommendations;
        if (!product) throw new Error("Không có dữ liệu sản phẩm gốc.");
        let seed = Math.random(); if (product.id) { const m=product.id.match(/\d+$/); if(m) seed=parseInt(m[0],10); } const rating = ((seed * 13)%21)/10 + 2.5;
        modalTitle.textContent = product.name || 'Chi tiết';
        modalContent.innerHTML = `<img src="${product.image_url || 'placeholder.png'}" alt="${product.name || 'N/A'}" onerror="this.onerror=null; this.src='placeholder.png';"><h3>${product.name || 'N/A'}</h3><div class="category">Loại: ${product.category || 'N/A'}</div>${createStarRating(rating)}<div class="price">${product.price ? formatter.format(product.price) : 'Liên hệ'}</div><h4>Mô tả</h4><p class="description">${product.description || 'Không có.'}</p>`;
        if (recommendations && recommendations.length > 0) {
            modalRecoList.innerHTML = '';
            recommendations.forEach(item => {
                const recoProduct = item.product; const recoDocId = item._id;
                if (!recoProduct) { console.warn("Lỗi gợi ý:", item); return; }
                let rSeed = Math.random(); if (recoProduct.id) { const m=recoProduct.id.match(/\d+$/); if(m) rSeed=parseInt(m[0],10); } const rRating = ((rSeed * 17)%21)/10 + 2.5;
                modalRecoList.insertAdjacentHTML('beforeend', `<div class="reco-card-modal" data-doc-id="${recoDocId}" tabindex="0" title="${recoProduct.name || 'Sản phẩm'} - Độ tương đồng: ${(item.score * 100).toFixed(1)}%"><img src="${recoProduct.image_url || 'placeholder.png'}" alt="${recoProduct.name || 'N/A'}" loading="lazy" onerror="this.onerror=null; this.src='placeholder.png';"><div class="reco-card-modal-info"><p>${recoProduct.name || 'N/A'}</p>${createStarRating(rRating)}</div></div>`);
            });
            addModalRecoClickListeners(modalRecoList);
        } else { modalRecoList.innerHTML = '<p class="message">Không có gợi ý.</p>'; }
    } catch (error) {
        console.error('Lỗi fetch chi tiết/gợi ý:', error);
        modalTitle.textContent = 'Lỗi';
        modalContent.innerHTML = `<p class="message error">❌ ${error.message}.</p>`;
        modalRecoList.innerHTML = '<p class="message error">❌ Lỗi tải gợi ý.</p>';
    }
}

/**
 * Xử lý lỗi từ API response
 */
async function createApiError(response, defaultMessage = 'Có lỗi xảy ra') {
    let detail = defaultMessage;
    try {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            const errData = await response.json(); detail = errData.detail || errData.message || detail;
        } else { detail = await response.text() || detail; }
    } catch (e) { console.warn("Không thể parse lỗi:", e); }
    const statusText = response.statusText ? ` (${response.statusText})` : '';
    return new Error(`Lỗi API ${response.status}${statusText}: ${detail}`);
}

/**
 * Thêm event listener cho các thẻ sản phẩm (Click + Keydown)
 * Sửa lại: Dùng flag, không clone node
 */
function addCardClickListeners(gridElement) {
    if (!gridElement || gridElement.dataset.cardListenerBound === 'true') {
        // console.log("Listener đã được gắn cho:", gridElement.id); // Debug
        return;
    }
    gridElement.dataset.cardListenerBound = 'true';
    // console.log("Gắn listener cho:", gridElement.id); // Debug

    gridElement.addEventListener('click', (event) => {
        const card = event.target.closest('.product-card'); if (!card) return;
        const docId = card.dataset.docId;
        const isDetailButtonClick = event.target.classList.contains('btn-detail') || event.target.closest('.btn-detail');
        if (docId && isDetailButtonClick) { fetchProductDetailsAndRecommendations(docId); }
    });
    gridElement.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            const card = event.target.closest('.product-card'); if (card) {
                event.preventDefault(); const docId = card.dataset.docId;
                if(docId) fetchProductDetailsAndRecommendations(docId);
            }
        }
    });
}

/**
 * Thêm event listener cho các thẻ gợi ý trong modal
 * Sửa lại: Dùng flag, không clone node
 */
function addModalRecoClickListeners(listElement) {
     if (!listElement || listElement.dataset.recoListenerBound === 'true') return;
     listElement.dataset.recoListenerBound = 'true';
     // console.log("Gắn listener cho Modal Reco List"); // Debug

    listElement.addEventListener('click', (event) => {
        const card = event.target.closest('.reco-card-modal'); if (!card) return;
        const docId = card.dataset.docId; if (docId) {
            MicroModal.close('product-modal');
            setTimeout(() => { fetchProductDetailsAndRecommendations(docId); }, 150);
        }
    });
    listElement.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            const card = event.target.closest('.reco-card-modal'); if (card) {
                event.preventDefault(); const docId = card.dataset.docId; if(docId) {
                    MicroModal.close('product-modal');
                    setTimeout(() => fetchProductDetailsAndRecommendations(docId), 150);
                }
            }
        }
    });
}


// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    // Khởi tạo Micromodal
    try {
        MicroModal.init({
             closeTrigger: 'data-micromodal-close',
             disableScroll: true,
             disableFocus: false,
             awaitOpenAnimation: false,
             awaitCloseAnimation: true,
             debugMode: false
        });
    } catch (e) { console.error("Micromodal init error:", e); }

    // Tải categories và sản phẩm ban đầu
    fetchCategories();
    fetchProducts(); // Tải sản phẩm ban đầu

    // --- SỰ KIỆN SUBMIT FORM ---
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        const category = categorySelect.value;

        // Ẩn section sản phẩm ban đầu
        allProductsSection.style.display = 'none';

        // TRƯỜNG HỢP 1: Có Từ Khóa
        if (query) {
            // Chạy cả tìm kiếm keyword và gợi ý semantic
            fetchKeywordSearch(query, category);
            fetchSemanticSuggestions(query, category);
        }
        // TRƯỜNG HỢP 2: Không có Từ Khóa nhưng Có Category
        else if (!query && category) {
            // Chỉ tìm theo category, hiển thị vào grid keyword results
            keywordResultsTitle.textContent = `Sản phẩm thuộc loại "${category}"`; // Đặt tiêu đề trước
            keywordResultsSection.style.display = 'block'; // Hiện section keyword
            semanticSuggestionsSection.style.display = 'none'; // Ẩn section semantic
            fetchProducts(category, keywordResultsGrid, keywordMessage); // Gọi API /products với filter
        }
        // TRƯỜNG HỢP 3: Cả Từ Khóa và Category đều rỗng -> Reset
        else {
            fetchProducts(); // Tải lại sản phẩm ban đầu
        }
    });

     // Reset khi chọn lại "-- Tất cả loại --" VÀ ô tìm kiếm RỖNG
     categorySelect.addEventListener('change', () => {
         if (categorySelect.value === '' && searchInput.value.trim() === '') {
             fetchProducts(); // Reset về trang chủ
         }
     });

    // Reset KHI XÓA HẾT chữ trong ô tìm kiếm
    searchInput.addEventListener('input', () => {
        if (searchInput.value.trim() === '') {
             // Chỉ ẩn các section kết quả, hiện lại section ban đầu
             keywordResultsSection.style.display = 'none';
             semanticSuggestionsSection.style.display = 'none';
             allProductsSection.style.display = 'block';
        }
    });
});