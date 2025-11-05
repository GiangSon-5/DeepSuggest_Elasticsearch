// app.js (Đã thêm logic chuyển Tab và nút Tải thêm)
const API_URL = 'http://localhost:8000';
const RESULTS_PER_PAGE = 20; // Số sản phẩm tải mỗi lần

// === BIẾN TOÀN CỤC ĐỂ THEO DÕI SỐ TRANG ===
let currentProductPage = 1;
let currentKeywordPage = 1; // (Tạm thời chưa dùng)
let isLoading = false; // Cờ để tránh click "Tải thêm" nhiều lần

// === DOM ELEMENTS ===
// Tab Content
const appContent = document.getElementById('app-content');
const docContent = document.getElementById('doc-content');
// Tab Buttons
const navTabApp = document.getElementById('nav-tab-app');
const navTabDoc = document.getElementById('nav-tab-doc');

// App Content
const productGrid = document.getElementById('product-grid');
const allProductsSection = document.getElementById('all-products-section');
const keywordResultsSection = document.getElementById('keyword-results-section');
const keywordResultsTitle = document.getElementById('keyword-results-title');
const keywordResultsGrid = document.getElementById('keyword-results-grid');
const keywordMessage = document.getElementById('keyword-message');
const semanticSuggestionsSection = document.getElementById('semantic-suggestions-section');
const semanticTitle = document.getElementById('semantic-title');
const semanticSuggestionsGrid = document.getElementById('semantic-suggestions-grid');
const semanticMessage = document.getElementById('semantic-message');
const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const categorySelect = document.getElementById('category-select');

// Nút Tải thêm
const loadMoreProductsBtn = document.getElementById('load-more-products');
// const loadMoreKeywordBtn = document.getElementById('load-more-keyword'); // Tạm thời chưa dùng

// Modal
const modalElement = document.getElementById('product-modal');
const modalTitle = document.getElementById('modal-title');
const modalContent = document.getElementById('modal-content-main').querySelector('.modal-product-details');
const modalRecoList = document.getElementById('modal-recommendation-list');

// Khác
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
 */
function createProductCardHTML(productData) {
    const isSemanticResult = productData && productData.hasOwnProperty('product') && productData.hasOwnProperty('score');
    const isKeywordOrInitial = productData && productData.hasOwnProperty('id') && !productData.hasOwnProperty('product');
    let product = null, docId = productData ? productData._id : null, score = null;
    if (isSemanticResult) { product = productData.product; score = productData.score; }
    else if (isKeywordOrInitial) { product = productData; }
    if (!product || !docId) { console.error("Dữ liệu không hợp lệ:", productData); return `<div class="product-card error-card"><p>Lỗi</p></div>`; }
    let seed = Math.random(); if (product.id) { const m = ('' + product.id).match(/\d+$/); if (m) seed = parseInt(m[0], 10); } const rating = ((seed * 13) % 21) / 10 + 2.5;
    return `
        <div class="product-card" data-doc-id="${docId}" tabindex="0" title="${product.name || 'Sản phẩm'}">
            <div class="card-image-container"><img src="${product.image_url || 'placeholder.png'}" alt="${product.name || 'N/A'}" loading="lazy" onerror="this.onerror=null; this.src='placeholder.png';"></div>
            <div class="card-content">
                <h4>${product.name || 'N/A'}</h4><span class="category">${product.category || 'N/A'}</span>${createStarRating(rating)}
                <div class="card-footer"><span class="price">${product.price ? formatter.format(product.price) : 'Liên hệ'}</span><button class="btn-detail" aria-label="Chi tiết ${product.name || ''}">Chi tiết</button></div>
            </div>
            ${score ? `<div class="reco-score" title="Độ tương đồng: ${(score * 100).toFixed(1)}%">${(score * 100).toFixed(0)}%</div>` : ''}
        </div>`;
}

/**
 * Hiển thị sản phẩm lên lưới (Sửa lại để hỗ trợ "Tải thêm")
 */
function displayProducts(products, gridElement, messageElement, append = false) {
    // Nếu không phải là "append" (tải thêm) thì xóa nội dung cũ
    if (!append) {
        gridElement.innerHTML = '';
    }
    
    // Xóa thông báo (nếu có)
    if (messageElement) messageElement.textContent = '';

    // Xóa loading "Tải thêm" nếu là lần tải đầu
    if (!append && gridElement === productGrid) {
        const loadingMsg = gridElement.querySelector('p.message');
        if (loadingMsg) loadingMsg.remove();
    }
    
    if (!products || products.length === 0) {
        // Chỉ hiển thị "Không có" nếu đây là lần tải đầu tiên (không append)
        if (!append) {
            const noProductMsg = 'Không có kết quả tìm kiếm.';
            if (messageElement) messageElement.textContent = noProductMsg;
            gridElement.innerHTML = `<p class="message">${noProductMsg}</p>`;
        }
        return;
    }

    const cardsHTML = products.map(productData => {
         if(productData && productData._id) { return createProductCardHTML(productData); }
         else { console.warn("Dữ liệu không hợp lệ:", productData); return ''; }
    }).join('');
    
    // Chèn vào cuối
    gridElement.insertAdjacentHTML('beforeend', cardsHTML);
    
    // Gắn listener (phải chạy lại để gắn cho các thẻ mới)
    addCardClickListeners(gridElement);
}

/**
 * Gọi API lấy sản phẩm (Sửa lại để hỗ trợ "Tải thêm")
 */
async function fetchProducts(category = null, page = 1, grid = productGrid, section = allProductsSection, msg = null, btn = loadMoreProductsBtn) {
    if (isLoading) return; // Không tải nếu đang tải dở
    isLoading = true;
    
    // Hiển thị loading
    if (page === 1) {
        grid.innerHTML = '<p class="message"><i class="fas fa-spinner fa-spin"></i> Đang tải...</p>';
    } else {
        btn.textContent = 'Đang tải...';
        btn.disabled = true;
    }
    
    if (section) section.style.display = 'block';
    if(grid !== keywordResultsGrid) keywordResultsSection.style.display = 'none';
    if(grid !== semanticSuggestionsGrid) semanticSuggestionsSection.style.display = 'none';
    if(grid !== productGrid) allProductsSection.style.display = 'none';

    try {
        const params = new URLSearchParams({ page: page, size: RESULTS_PER_PAGE });
        if (category) {
            params.append('category', category);
        }
        const url = `${API_URL}/products?${params.toString()}`;

        const response = await fetch(url);
        if (!response.ok) throw await createApiError(response, 'Không tải được sản phẩm');
        const result = await response.json(); // API trả về { data: [...], total: N }

        // Hiển thị sản phẩm (page > 1 nghĩa là append=true)
        displayProducts(result.data, grid, msg, page > 1);

        // Xử lý nút Tải thêm
        const totalLoaded = (page * RESULTS_PER_PAGE);
        if (totalLoaded < result.total) {
            btn.style.display = 'block'; // Hiển thị nút
        } else {
            btn.style.display = 'none'; // Ẩn nút (đã hết hàng)
        }

        if (category && grid === keywordResultsGrid) {
            keywordResultsTitle.textContent = `Sản phẩm thuộc loại "${category}" (Tìm thấy ${result.total} sản phẩm)`;
        }

    } catch (error) {
        console.error('Lỗi khi tải sản phẩm:', error);
        const errorMsg = `❌ ${error.message}.`;
        if (msg) msg.textContent = errorMsg;
        else if (page === 1) grid.innerHTML = `<p class="message error">${errorMsg}</p>`;
        btn.style.display = 'none'; // Ẩn nút nếu lỗi
    } finally {
        isLoading = false;
        btn.textContent = 'Tải thêm';
        btn.disabled = false;
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
 * Gọi API tìm kiếm keyword (Sửa lại để reset "Tải thêm")
 */
async function fetchKeywordSearch(queryText, category) {
    // Tạm thời chưa hỗ trợ "Tải thêm" cho keyword, nên ẩn nút
    // loadMoreKeywordBtn.style.display = 'none'; 
    
    keywordResultsGrid.innerHTML = '<p class="message"><i class="fas fa-spinner fa-spin"></i> Đang tìm theo từ khóa...</p>';
    keywordMessage.textContent = '';
    keywordResultsTitle.textContent = `Kết quả khớp từ khóa cho "${queryText}"`+ (category ? ` trong "${category}"` : '');
    keywordResultsSection.style.display = 'block';

    try {
        // Chỉ tải 1 trang (20 sản phẩm)
        const params = new URLSearchParams({ query: queryText, size: RESULTS_PER_PAGE, page: 1 });
        if (category) params.append('category', category);
        const url = `${API_URL}/search-keyword?${params.toString()}`;

        const response = await fetch(url);
        if (!response.ok) throw await createApiError(response, 'Tìm kiếm từ khóa thất bại');

        const results = await response.json();
        displayProducts(results, keywordResultsGrid, keywordMessage, false); // Không append

    } catch (error) {
        console.error('Lỗi khi tìm kiếm keyword:', error);
        keywordResultsGrid.innerHTML = '';
        keywordMessage.textContent = `❌ ${error.message}.`;
    }
}

/**
 * Gọi API lấy gợi ý semantic (Giữ nguyên, vì luôn chỉ lấy 5)
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

        const suggestions = await response.json();
        displayProducts(suggestions, semanticSuggestionsGrid, semanticMessage, false); // Không append

    } catch (error) {
        console.error('Lỗi khi lấy gợi ý semantic:', error);
        semanticSuggestionsGrid.innerHTML = '';
        semanticMessage.textContent = `❌ ${error.message}.`;
    }
}


/**
 * Gọi API lấy chi tiết sản phẩm và gợi ý (cho Modal) (Giữ nguyên)
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
 * Xử lý lỗi từ API response (Giữ nguyên)
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
 * Thêm event listener cho các thẻ sản phẩm (Giữ nguyên)
 */
function addCardClickListeners(gridElement) {
    if (!gridElement) return;
    
    // === SỬA LỖI: Gắn listener vào grid thay vì dùng cờ ===
    // (Xóa các dòng dataset.cardListenerBound)

    // Dùng event delegation (chỉ gắn 1 lần)
    // Cần đảm bảo hàm này chỉ được gọi MỘT LẦN cho mỗi grid
    if (gridElement.dataset.listenerAttached) return;
    gridElement.dataset.listenerAttached = 'true';

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
 * Thêm event listener cho các thẻ gợi ý trong modal (Giữ nguyên)
 */
function addModalRecoClickListeners(listElement) {
     if (!listElement || listElement.dataset.recoListenerBound === 'true') return;
     listElement.dataset.recoListenerBound = 'true';
    listElement.addEventListener('click', (event) => { /* ... code cũ ... */ });
    listElement.addEventListener('keydown', (event) => { /* ... code cũ ... */ });
}


// --- INITIALIZATION (Thêm logic chuyển tab) ---
document.addEventListener('DOMContentLoaded', () => {
    // Khởi tạo Micromodal
    try { MicroModal.init({ /* ... cấu hình cũ ... */ }); }
    catch (e) { console.error("Micromodal init error:", e); }

    // === LOGIC CHUYỂN TAB ===
    navTabApp.addEventListener('click', () => {
        navTabApp.classList.add('active');
        navTabDoc.classList.remove('active');
        appContent.classList.add('active');
        docContent.classList.remove('active');
    });

    navTabDoc.addEventListener('click', () => {
        navTabDoc.classList.add('active');
        navTabApp.classList.remove('active');
        docContent.classList.add('active');
        appContent.classList.remove('active');
    });
    
    // Liên kết logo về trang chủ (reset)
    document.getElementById('home-link-app').addEventListener('click', (e) => {
        e.preventDefault();
        // Reset về trang 1
        currentProductPage = 1;
        fetchProducts(null, 1);
        // Xóa ô tìm kiếm và dropdown
        searchInput.value = '';
        categorySelect.value = '';
    });
    // === KẾT THÚC LOGIC CHUYỂN TAB ===


    // Tải categories và sản phẩm ban đầu
    fetchCategories();
    // Bắt đầu tải trang 1
    currentProductPage = 1;
    fetchProducts(null, currentProductPage);

    // --- SỰ KIỆN SUBMIT FORM (Sửa lại để reset trang) ---
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        const category = categorySelect.value;
        allProductsSection.style.display = 'none';
        loadMoreProductsBtn.style.display = 'none'; // Ẩn nút tải thêm
        currentProductPage = 1; // Reset trang
        currentKeywordPage = 1; // Reset trang

        if (query) {
            fetchKeywordSearch(query, category); // (Chỉ tải trang 1)
            fetchSemanticSuggestions(query, category);
        }
        else if (!query && category) {
            keywordResultsTitle.textContent = `Sản phẩm thuộc loại "${category}"`;
            keywordResultsSection.style.display = 'block';
            semanticSuggestionsSection.style.display = 'none';
            // Gọi fetchProducts cho keywordGrid, nhưng KHÔNG có nút tải thêm
            fetchProducts(category, keywordResultsGrid, keywordMessage, null, document.createElement('button')); // Truyền 1 nút giả để nó không lỗi
        }
        else {
            fetchProducts(null, currentProductPage); // Tải lại trang 1
        }
    });

     // --- SỰ KIỆN NÚT TẢI THÊM ---
     loadMoreProductsBtn.addEventListener('click', () => {
        if (!isLoading) {
            currentProductPage++; // Tăng số trang
            fetchProducts(null, currentProductPage, productGrid, null, loadMoreProductsBtn); // Tải trang tiếp theo
        }
     });

     // Reset khi chọn lại "-- Tất cả loại --" VÀ ô tìm kiếm RỖNG
     categorySelect.addEventListener('change', () => {
         if (categorySelect.value === '' && searchInput.value.trim() === '') {
             currentProductPage = 1;
             fetchProducts(null, currentProductPage);
         }
     });

    // Reset KHI XÓA HẾT chữ trong ô tìm kiếm
    searchInput.addEventListener('input', () => {
        if (searchInput.value.trim() === '') {
             keywordResultsSection.style.display = 'none';
             semanticSuggestionsSection.style.display = 'none';
             allProductsSection.style.display = 'block';
             // Không cần fetch, chỉ hiện lại
        }
    });
    
    // Gắn listener 1 lần duy nhất cho các grid
    addCardClickListeners(productGrid);
    addCardClickListeners(keywordResultsGrid);
    addCardClickListeners(semanticSuggestionsGrid);
});