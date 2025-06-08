// 注册表单提交处理
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('regUsername').value;
    const password = document.getElementById('regPassword').value;
    const confirm = document.getElementById('confirmPassword').value;

    if (password !== confirm) {
        alert('密码与确认密码不一致');
        return;
    }

    const result = await apiRequest('/register', 'POST', { username, password });
    if (result) {
        alert('注册成功！请登录');
        window.location.href = 'login.html';
    }
});