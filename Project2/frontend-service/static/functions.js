// SỬA LẠI THÀNH THẾ NÀY:
if (!localStorage.getItem('access_token') && 
    window.location.pathname !== '/login' && 
    window.location.pathname !== '/register') {
    window.location.href = '/login';
}

function logout() {
    localStorage.removeItem('access_token'); // Đổi 'token' thành 'access_token'
    sessionStorage.clear(); // 🚀 XÓA SẠCH BỘ NHỚ TẠM CỦA AI TRƯỚC KHI THOÁT
    window.location.href = '/login';
}

window.colorPalette = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
    '#FFBE0B', '#FF006E', '#8338EC', '#3A86FF', 
    '#FB5607', '#38B000', '#9B5DE5', '#F15BB5'
];


window.exchangeRatesToVND = {
    vnd: 1,         
    usd: 25400,     
    eur: 27500,     
    gbp: 32000,     
    jpy: 165,      
    cny: 3500,      
    krw: 18.5,      
    inr: 305,       
    rub: 275,       
    brl: 4900,      
    zar: 1350,      
    aed: 6915,      
    aud: 16800,     
    cad: 18600,     
    chf: 28000,     
    hkd: 3250,      
    bdt: 230,       
    sgd: 18800,     
    thb: 690,      
    try: 780,       
    mxn: 1500,      
    php: 440,     
    pln: 6350,      
    sek: 2350,      
    nzd: 15300,     
    dkk: 3680,      
    idr: 1.58,      
    ils: 6750,      
    myr: 5350,      
    mad: 2520       
};

window.currencyBehaviors = {
    usd: {symbol: "$", useComma: false, useDecimals: true, useSpace: false, right: false},
    eur: {symbol: "€", useComma: true, useDecimals: true, useSpace: false, right: false},
    gbp: {symbol: "£", useComma: false, useDecimals: true, useSpace: false, right: false},
    jpy: {symbol: "¥", useComma: false, useDecimals: false, useSpace: false, right: false},
    cny: {symbol: "¥", useComma: false, useDecimals: true, useSpace: false, right: false},
    krw: {symbol: "₩", useComma: false, useDecimals: false, useSpace: false, right: false},
    inr: {symbol: "₹", useComma: false, useDecimals: true, useSpace: false, right: false},
    rub: {symbol: "₽", useComma: true, useDecimals: true, useSpace: false, right: false},
    brl: {symbol: "R$", useComma: true, useDecimals: true, useSpace: false, right: false},
    zar: {symbol: "R", useComma: false, useDecimals: true, useSpace: true, right: true},
    aed: {symbol: "AED", useComma: false, useDecimals: true, useSpace: true, right: true},
    aud: {symbol: "A$", useComma: false, useDecimals: true, useSpace: false, right: false},
    cad: {symbol: "C$", useComma: false, useDecimals: true, useSpace: false, right: false},
    chf: {symbol: "Fr", useComma: false, useDecimals: true, useSpace: true, right: true},
    hkd: {symbol: "HK$", useComma: false, useDecimals: true, useSpace: false, right: false},
    bdt: {symbol: "৳", useComma: false, useDecimals: true, useSpace: false, right: false},
    sgd: {symbol: "S$", useComma: false, useDecimals: true, useSpace: false, right: false},
    thb: {symbol: "฿", useComma: false, useDecimals: true, useSpace: false, right: false},
    try: {symbol: "₺", useComma: true, useDecimals: true, useSpace: false, right: false},
    mxn: {symbol: "Mex$", useComma: false, useDecimals: true, useSpace: false, right: false},
    php: {symbol: "₱", useComma: false, useDecimals: true, useSpace: false, right: false},
    pln: {symbol: "zł", useComma: true, useDecimals: true, useSpace: true, right: true},
    sek: {symbol: "kr", useComma: false, useDecimals: true, useSpace: true, right: true},
    nzd: {symbol: "NZ$", useComma: false, useDecimals: true, useSpace: false, right: false},
    dkk: {symbol: "kr.", useComma: true, useDecimals: true, useSpace: true, right: true},
    idr: {symbol: "Rp", useComma: false, useDecimals: true, useSpace: true, right: true},
    ils: {symbol: "₪", useComma: false, useDecimals: true, useSpace: false, right: false},
    vnd: {symbol: "₫", useComma: true, useDecimals: true, useSpace: true, right: true},
    myr: {symbol: "RM", useComma: false, useDecimals: true, useSpace: false, right: false},
    mad: {symbol: "DH", useComma: false, useDecimals: true, useSpace: true, right: true},
};

function formatCurrency(amount) {
    if (amount === undefined || amount === null) return '0';

    const cur = window.currentCurrency || (typeof currentCurrency !== 'undefined' ? currentCurrency : 'usd');

    const behavior = window.currencyBehaviors[cur] || {
        symbol: "$", useComma: false, useDecimals: true, useSpace: false, right: false
    };

    const rate = window.exchangeRatesToVND[cur] || 1;
    const convertedAmount = amount / rate;

    const isNegative = convertedAmount < 0;
    const absAmount = Math.abs(convertedAmount);

    let minDecimals = behavior.useDecimals ? 2 : 0;
    let maxDecimals = behavior.useDecimals ? 2 : 0;

    if (behavior.useDecimals && absAmount > 0 && absAmount < 0.01) {
        maxDecimals = 4;
    }

    const options = {
        minimumFractionDigits: minDecimals,
        maximumFractionDigits: maxDecimals,
    };
    
    let formattedAmount = new Intl.NumberFormat(behavior.useComma ? "de-DE" : "en-US", options).format(absAmount);

    let result = behavior.right
        ? `${formattedAmount}${behavior.useSpace ? " " : ""}${behavior.symbol}`
        : `${behavior.symbol}${behavior.useSpace ? " " : ""}${formattedAmount}`;
        
    return isNegative ? `-${result}` : result;
}

function getUserTimeZone() {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

function formatMonth(date) {
    return date.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: 'long',
        timeZone: getUserTimeZone()
    });
}

function formatDateFromUTC(utcDateString) {
    if (!utcDateString) return '-';
    const safeDate = utcDateString.endsWith('Z') ? utcDateString : utcDateString + 'Z';
    const date = new Date(safeDate);
    
    const day = String(date.getUTCDate()).padStart(2, '0');
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const year = date.getUTCFullYear();
    return `${day}/${month}/${year}`;
}

function updateMonthDisplay() {
    const currentMonthEl = document.getElementById('currentMonth');
    if (currentMonthEl && typeof currentDate !== 'undefined') {
        currentMonthEl.textContent = formatMonth(currentDate);
    }
}

function getMonthBounds(date) {
    const d = new Date(date);
    const year = d.getUTCFullYear();
    const month = d.getUTCMonth();
    const startDay = typeof startDate !== 'undefined' ? startDate : 1;

    if (startDay === 1) {
        const start = new Date(Date.UTC(year, month, 1, 0, 0, 0));
        const end = new Date(Date.UTC(year, month + 1, 0, 23, 59, 59, 999));
        return { start, end };
    }
    
    let start, end;
    if (d.getUTCDate() < startDay) {
        start = new Date(Date.UTC(year, month - 1, startDay, 0, 0, 0));
        end = new Date(Date.UTC(year, month, startDay - 1, 23, 59, 59, 999));
    } else {
        start = new Date(Date.UTC(year, month, startDay, 0, 0, 0));
        end = new Date(Date.UTC(year, month + 1, startDay - 1, 23, 59, 59, 999));
    }
    return { start, end };
}

function getMonthExpenses(expenses) {
    if (typeof currentDate === 'undefined') return expenses;
    const { start, end } = getMonthBounds(currentDate);
    return expenses.filter(exp => {
        const safeDateString = exp.date.endsWith('Z') ? exp.date : exp.date + 'Z';
        const expDate = new Date(safeDateString);
        return expDate >= start && expDate <= end;
    }).sort((a, b) => new Date(b.date) - new Date(a.date));
}

const originalFetch = window.fetch;
window.fetch = async (...args) => {
    let [resource, config] = args;

    // 1. Nếu đây là một lệnh gọi API, hãy bẻ lái nó sang cổng 8000 của Gateway
    if (typeof resource === 'string' && resource.startsWith('/api/')) {
        resource = 'http://172.207.48.96:8000' + resource;
        args[0] = resource; // Cập nhật lại đường dẫn mới

        // 2. Tự động thêm Token (chỉ bỏ qua các route liên quan đến xác thực auth)
        if (!resource.includes('/auth/')) {
            config = config || {};
            const token = localStorage.getItem('access_token');

            if (token) {
                config.headers = {
                    ...config.headers,
                    'Authorization': `Bearer ${token}`
                };
            }
            args[1] = config;
        }
    }

    try {
        const response = await originalFetch(...args);

        // Nếu token hết hạn hoặc sai, tự động văng ra màn hình đăng nhập
        if (response.status === 401) {
            logout();
        }

        return response;

    } catch (err) {
        console.error("FETCH ERROR:", err);
        throw err;
    }
};

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById('toast-container')) {
        document.body.insertAdjacentHTML('beforeend', '<div id="toast-container"></div>');
    }
});

window.showToast = function(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'error' : ''}`;
    
    const icon = type === 'error' 
        ? '<i class="fa-solid fa-circle-exclamation" style="color: #ff4d4d; font-size: 18px;"></i>' 
        : '<i class="fa-solid fa-circle-check" style="color: #4ade80; font-size: 18px;"></i>';
    
    toast.innerHTML = `${icon} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400); 
    }, 3000);
};

let aiAbortController = null;

function closeAiModal() {
    document.getElementById('aiModal').style.display = 'none';
    if (aiAbortController) {
        aiAbortController.abort();
        aiAbortController = null;
    }
}

window.addEventListener('click', function(event) {
    const modal = document.getElementById('aiModal');
    if (event.target === modal) {
        closeAiModal();
    }
}); 

async function analyzeTrends() {
    const modal = document.getElementById('aiModal');
    const loadingText = document.getElementById('aiLoading');
    const contentBox = document.getElementById('aiContent');
    const btn = document.getElementById('btnAnalyze');

    modal.style.display = 'flex';
    loadingText.style.display = 'block';
    contentBox.innerHTML = '';
    btn.disabled = true;
    if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xử lý...';

    aiAbortController = new AbortController();

    try {
        const token = localStorage.getItem('access_token'); 
        const response = await fetch('/api/ai/analyze-trends', {
            method: 'GET',
            headers: { 'Authorization': 'Bearer ' + token },
            signal: aiAbortController.signal
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Lỗi khi gọi API');
        
        let formattedReply = data.reply
            .replace(/### (.*?)\n/g, '<h3 style="color:#d4a5ff; margin-top: 15px; margin-bottom:5px;">$1</h3>')
            .replace(/\*\*(.*?)\*\*/g, '<strong style="color: #fff;">$1</strong>')
            .replace(/\n/g, '<br>');

        contentBox.innerHTML = formattedReply;

    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Tiến trình AI đã bị ngắt vì người dùng đóng cửa sổ.');
        } else {
            contentBox.innerHTML = `<span style="color:#ff4d4d;">Lỗi: ${error.message || 'Không thể kết nối với Cú Mèo lúc này. Hãy thử lại sau!'}</span>`;
        }
    } finally {
        loadingText.style.display = 'none';
        btn.disabled = false;
        if (btn) btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Phân Tích AI';
    }
}

async function loadUserConfig() {
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (!token) return;

    try {
        // 🚀 Cú Mèo đã chốt cứng link đúng: /api/users/config
        const response = await fetch(`/api/users/config?t=${new Date().getTime()}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const configData = await response.json();

        // XÓA LỆNH CHUYỂN TRANG SETUP.HTML VÌ BẢNG SETUP CỦA EM LÀ OVERLAY TRONG INDEX.HTML

        // Lưu cấu hình mới nhất vào biến toàn cục
        window.userSettings = configData;

        // Phóng thanh thông báo cho toàn bộ các trang biết là "Đã có cấu hình mới"
        window.dispatchEvent(new Event('userConfigLoaded'));

    } catch (error) {
        console.error("Lỗi khi tải cấu hình:", error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    if (!window.location.href.includes('login') && !window.location.href.includes('register')) {
        loadUserConfig();
    }
});