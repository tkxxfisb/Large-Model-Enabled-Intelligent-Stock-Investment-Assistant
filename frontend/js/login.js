// 登录表单提交处理
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const result = await apiRequest('/login', 'POST', { username, password });
    if (result) {
        localStorage.setItem('token', result.token);
        alert('登录成功！');
        window.location.href = 'trade.html'; // 跳转到交易页面
    }
});