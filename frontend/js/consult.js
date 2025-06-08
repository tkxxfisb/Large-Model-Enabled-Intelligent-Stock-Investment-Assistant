// 页面加载时检查登录状态
checkAuth();

// 发送消息处理
async function sendMessage() {
    const input = document.getElementById('consultInput');
    const question = input.value.trim();
    const chatContainer = document.getElementById('chatContainer');
    
    if (!question) return;
    
    input.value = '';
    
    // 添加用户消息
    const userMsg = document.createElement('div');
    userMsg.className = 'message user-message';
    userMsg.innerHTML = `
        <img src="assets/avatars/user_avatar.png" class="avatar" alt="用户头像">
        <div class="message-content">${question}</div>
    `;
    chatContainer.appendChild(userMsg);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // 添加加载中的临时消息
    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'message assistant-message loading-message';
    loadingMsg.innerHTML = `
        <img src="assets/avatars/assistant_avatar.png" class="avatar" alt="助手头像">
        <div class="message-content">正在为您解答，请稍候...</div>
    `;
    chatContainer.appendChild(loadingMsg);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const result = await apiRequest('/knowledge', 'POST', { question });
        console.log('API Response:', result);

        // 移除加载消息
        chatContainer.removeChild(loadingMsg);

        if(!result.success){
            const errorMsg = document.createElement('div');
            errorMsg.className = 'message assistant-message';
            errorMsg.innerHTML = `
                <img src="assets/avatars/assistant_avatar.png" class="avatar" alt="助手头像">
                <div class="message-content" style="background: #ffebee; color: #b71c1c;">
                    咨询失败：${result.message || '未知错误'}
                </div>
            `;
            chatContainer.appendChild(errorMsg);
        } else {
            const assistantMsg = document.createElement('div');
            assistantMsg.className = 'message assistant-message';
            assistantMsg.innerHTML = `
                <img src="assets/avatars/assistant_avatar.png" class="avatar" alt="助手头像">
                <div class="message-content">${result.message}</div>
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
                咨询失败：${error.message}
            </div>
        `;
        chatContainer.appendChild(errorMsg);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// 绑定发送事件（点击按钮或回车）
document.getElementById('sendBtn').addEventListener('click', sendMessage);
document.getElementById('consultInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});