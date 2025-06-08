// 页面加载时检查登录状态
checkAuth();

// 加载持仓数据
async function loadPositions() {
    try {
        const result = await apiRequest('/positions');
        const tbody = document.getElementById('positionTable').getElementsByTagName('tbody')[0];
        console.log('持仓数据:', result); // 打印接口返回的数据
        // 处理接口调用失败（result 为 undefined）
        if (!result) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center">获取持仓数据失败，请检查网络或重试</td>
                </tr>
            `;
            return;
        }

        // 处理无持仓数据
        if (!result.data || result.data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center">当前无持仓股票</td>
                </tr>
            `;
            return;
        }

        // 正常渲染数据（确保字段名与接口返回一致）
        tbody.innerHTML = result.data.map(pos => `
            <tr>
                <td>${pos.code}</td>
                <td>${pos.name}</td>
                <td>${pos.quantity}</td>
                <td>￥${pos.price.toFixed(2)}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('加载持仓数据异常:', error);
        const tbody = document.getElementById('positionTable').getElementsByTagName('tbody')[0];
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center">加载持仓数据时发生未知错误</td>
            </tr>
        `;
    }
};
// 初始化加载
loadPositions();
// 交易表单提交处理
document.getElementById('tradeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = document.getElementById('submitBtn'); // 获取提交按钮
    const data = {
        action: document.getElementById('type').value,
        stock_code: document.getElementById('stockCode').value,
        quantity: parseInt(document.getElementById('quantity').value)
    };

    try {
        // 禁用按钮并显示加载状态
        submitBtn.disabled = true;
        submitBtn.textContent = "提交中...⌛";  // 显示转圈符号
        
        const result = await apiRequest('/trade', 'POST', data);
        console.log('交易结果:', result); // 打印接口返回的数据
        if (result.success === true) {
            alert(`交易成功：${result.message}\n交易ID：${result.transaction_id}\n时间：${result.timestamp}`);
        } else {
            const errorDetails = result.message.split('交易失败:').pop().trim();
            alert(`交易失败：${errorDetails || '未知错误'}`);
        }
        loadPositions();
    } catch (error) {
        const errorMessage = error.response?.data?.detail || '网络请求失败，请检查网络连接';
        alert(`交易失败：${errorMessage}`);
    } finally {
        // 恢复按钮状态
        submitBtn.disabled = false;
        submitBtn.textContent = "提交交易";
    }
});