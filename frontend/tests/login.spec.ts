import { test, expect } from '@playwright/test';

test.describe('AI项目管理系统登录功能测试', () => {
  test.beforeEach(async ({ page }) => {
    // 确保每次测试前都导航到登录页面
    await page.goto('http://localhost:3000/login');
  });

  test('完整登录流程测试', async ({ page }) => {
    // 步骤1: 验证登录页面加载正确
    await expect(page).toHaveTitle('AI项目管理系统');
    await expect(page.locator('h2')).toContainText('登录账户');
    await expect(page.locator('text=欢迎回到AI项目管理系统')).toBeVisible();

    // 步骤2: 输入测试邮箱地址
    const emailInput = page.getByRole('textbox', { name: '请输入邮箱地址' });
    await emailInput.fill('test@example.com');
    await expect(emailInput).toHaveValue('test@example.com');

    // 步骤3: 输入测试密码
    const passwordInput = page.getByRole('textbox', { name: '请输入密码' });
    await passwordInput.fill('password123');
    await expect(passwordInput).toHaveValue('password123');

    // 步骤4: 选择记住我选项
    const rememberCheckbox = page.getByRole('checkbox', { name: '记住我' });
    await rememberCheckbox.check();
    await expect(rememberCheckbox).toBeChecked();

    // 步骤5: 点击登录按钮
    const loginButton = page.getByRole('button', { name: '登录', exact: true });
    await loginButton.click();

    // 验证登录按钮状态变化
    await expect(page.getByRole('button', { name: '登录中...' })).toBeVisible();

    // 步骤6: 验证登录成功并跳转到dashboard
    await expect(page).toHaveURL('http://localhost:3000/dashboard');
    await expect(page).toHaveTitle('AI项目管理系统');

    // 步骤7: 验证dashboard页面内容加载正确
    await expect(page.locator('h1')).toContainText('概览');
    await expect(page.locator('text=欢迎回来！这里是您的项目管理概览。')).toBeVisible();

    // 验证统计卡片存在
    await expect(page.locator('text=活跃项目')).toBeVisible();
    await expect(page.locator('text=文件总数')).toBeVisible();
    await expect(page.locator('text=AI对话')).toBeVisible();
    await expect(page.locator('text=团队成员')).toBeVisible();

    // 验证快速操作区域
    await expect(page.locator('h2', { hasText: '快速操作' })).toBeVisible();
    await expect(page.locator('text=创建项目')).toBeVisible();
    await expect(page.locator('text=上传文件')).toBeVisible();
    await expect(page.locator('text=AI问答')).toBeVisible();
    await expect(page.locator('text=团队协作')).toBeVisible();
  });

  test('表单验证测试', async ({ page }) => {
    // 测试空表单提交
    const loginButton = page.getByRole('button', { name: '登录', exact: true });
    await loginButton.click();
    
    // 验证表单验证是否工作（这里应该根据实际的验证逻辑调整）
    // 注意：由于我们没有实现后端验证，这里主要测试前端行为
  });

  test('忘记密码链接测试', async ({ page }) => {
    // 点击忘记密码链接
    const forgotPasswordLink = page.getByRole('link', { name: '忘记密码？' });
    await forgotPasswordLink.click();

    // 验证跳转到忘记密码页面
    await expect(page).toHaveURL(/.*forgot-password/);
    await expect(page.locator('h2')).toContainText('忘记密码');
  });

  test('注册链接测试', async ({ page }) => {
    // 点击立即注册链接
    const registerLink = page.getByRole('link', { name: '立即注册' });
    await registerLink.click();

    // 验证跳转到注册页面
    await expect(page).toHaveURL(/.*register/);
    await expect(page.locator('h2')).toContainText('创建账户');
  });

  test('Google登录按钮存在性测试', async ({ page }) => {
    // 验证Google登录按钮存在
    const googleLoginButton = page.getByRole('button', { name: '使用 Google 登录' });
    await expect(googleLoginButton).toBeVisible();
    
    // 注意：这里不实际点击，因为需要Google OAuth配置
  });
});

test.describe('注册页面测试', () => {
  test('注册页面加载和表单元素测试', async ({ page }) => {
    await page.goto('http://localhost:3000/register');

    // 验证页面标题和标题
    await expect(page).toHaveTitle('AI项目管理系统');
    await expect(page.locator('h2')).toContainText('创建账户');

    // 验证表单字段存在
    await expect(page.getByRole('textbox', { name: '请输入用户名' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: '请输入邮箱地址' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: '请输入密码' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: '请再次输入密码' })).toBeVisible();

    // 验证协议复选框
    await expect(page.getByRole('checkbox')).toBeVisible();

    // 验证创建账户按钮
    await expect(page.getByRole('button', { name: '创建账户' })).toBeVisible();
  });
});

test.describe('忘记密码页面测试', () => {
  test('忘记密码页面功能测试', async ({ page }) => {
    await page.goto('http://localhost:3000/forgot-password');

    // 验证页面内容
    await expect(page).toHaveTitle('AI项目管理系统');
    await expect(page.locator('h2')).toContainText('忘记密码');

    // 测试邮箱输入
    const emailInput = page.getByRole('textbox', { name: '请输入您的邮箱地址' });
    await emailInput.fill('test@example.com');
    await expect(emailInput).toHaveValue('test@example.com');

    // 验证发送按钮存在
    await expect(page.getByRole('button', { name: '发送重置邮件' })).toBeVisible();

    // 验证返回登录链接
    const backToLoginLink = page.getByRole('link', { name: '返回登录' });
    await expect(backToLoginLink).toBeVisible();
    
    await backToLoginLink.click();
    await expect(page).toHaveURL(/.*login/);
  });
}); 