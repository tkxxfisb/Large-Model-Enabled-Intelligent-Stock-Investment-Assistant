// 登录状态检查
async function checkAuth() {
    try {
        const token = localStorage.getItem('token');
        
        if (!token) {
            window.location.href = 'login.html';
            return;
        }

        const data = await apiRequest('/check-auth');
        
        if (!data.success) {
            localStorage.removeItem('token');
            window.location.href = 'login.html';
            throw new Error('登录状态已过期');
        }

        const user_id = data.user_id;

    } catch (error) {
        console.error('登录状态检查失败:', error.message);
        alert('登录状态异常，请重新登录');
        window.location.href = 'login.html';
    }
}

// 策略生成函数（适配带头像的聊天消息）
async function generateStrategy() {
    const instruction = document.getElementById('instruction').value.trim();
    const errorAlert = document.getElementById('errorAlert');
    const chatContainer = document.getElementById('chatContainer');
    errorAlert.style.display = 'none';
    document.getElementById('instruction').value = ''; // 清空输入框

    if (!instruction) {
        errorAlert.textContent = '请输入投资需求';
        errorAlert.style.display = 'block';
        return;
    }

    // 添加用户消息
    const userMsg = document.createElement('div');
    userMsg.className = 'message user-message';
    userMsg.innerHTML = `
        <img src="assets/avatars/user_avatar.png" class="avatar" alt="用户头像">
        <div class="message-content">${instruction}</div>
    `;
    chatContainer.appendChild(userMsg);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // 添加加载中的等待消息（带旋转动画）
    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'message assistant-message loading-message';
    loadingMsg.innerHTML = `
        <img src="assets/avatars/assistant_avatar.png" class="avatar" alt="助手头像">
        <div class="message-content">策略生成中，请稍候...预计1-5分钟</div>
    `;
    chatContainer.appendChild(loadingMsg);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const result = await apiRequest('/strategy', 'POST', {instruction});
        console.log('API Response:', result);

        // 移除加载消息
        chatContainer.removeChild(loadingMsg);

        if (!result.success) {
            const errorMsg = document.createElement('div');
            errorMsg.className = 'message assistant-message';
            errorMsg.innerHTML = `
                <img src="assets/avatars/assistant_avatar.png" class="avatar" alt="助手头像">
                <div class="message-content" style="background: #ffebee; color: #b71c1c;">
                    ${result.message}<br>
                    建议：${result.suggestions?.join(' ') || '无具体建议'}
                </div>
            `;
            chatContainer.appendChild(errorMsg);
        } else {
            const strategyData = result.data[0];
            const assistantMsg = document.createElement('div');
            assistantMsg.className = 'message assistant-message';
            assistantMsg.innerHTML = `
                <img src="assets/avatars/assistant_avatar.png" class="avatar" alt="助手头像">
                <div class="message-content">
                    <strong>${strategyData.title || '智能投资策略'}</strong><br>
                    ${strategyData.description || '未获取到策略描述'}<br>
                    风险等级：${strategyData.riskLevel || '未知'} | 历史年化收益：${strategyData.annualReturn || 'N/A'}<br>
                    推荐股票：${strategyData.recommendedStocks?.map(stock => `${stock.name}(${stock.code})`).join('、') || '无推荐股票'}
                </div>
            `;
            chatContainer.appendChild(assistantMsg);
        }
        chatContainer.scrollTop = chatContainer.scrollHeight;
    } catch (error) {
        // 移除加载消息
        chatContainer.removeChild(loadingMsg);

        const errorMsg = document.createElement('div');
        errorMsg.className = 'message assistant-message';
        errorMsg.innerHTML = `
            <img src="assets/avatars/assistant_avatar.png" class="avatar" alt="助手头像">
            <div class="message-content" style="background: #ffebee; color: #b71c1c;">
                策略生成失败：${error.message}
            </div>
        `;
        chatContainer.appendChild(errorMsg);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// 页面加载时检查登录状态
checkAuth();