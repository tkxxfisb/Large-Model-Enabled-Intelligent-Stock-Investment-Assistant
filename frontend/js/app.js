// 后端接口基础URL（根据实际调整）
const API_BASE = 'http://localhost:8000';

// 通用API请求函数
async function apiRequest(endpoint, method = 'GET', data = {}) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: method !== 'GET' ? JSON.stringify(data) : undefined
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const result = await response.json();
        
        if (!response.ok) throw new Error(result.message || '请求失败');
        return result;
    } catch (error) {
        return { success: false, message: error.message || '网络请求失败' };
    }
}

// 检查用户登录状态（需要认证的页面使用）
function checkAuth() {
    if (!localStorage.getItem('token')) {
        alert('请先登录！');
        window.location.href = 'login.html';
    }
}