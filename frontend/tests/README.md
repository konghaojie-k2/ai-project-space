# AI项目管理系统 - 前端自动化测试

## 概述

本项目使用 Playwright 进行端到端(E2E)自动化测试，确保前端功能的正确性和稳定性。

## 测试覆盖范围

### 🔐 认证功能测试 (`login.spec.ts`)

#### 登录功能测试
- ✅ 完整登录流程测试
  - 页面加载验证
  - 表单输入测试（邮箱、密码）
  - 记住我选项测试
  - 登录按钮状态变化验证
  - 成功跳转到Dashboard验证
  - Dashboard页面内容验证

- ✅ 表单验证测试
  - 空表单提交验证
  - 输入格式验证

- ✅ 页面导航测试
  - 忘记密码链接跳转
  - 注册链接跳转
  - Google登录按钮存在性验证

#### 注册功能测试
- ✅ 注册页面加载测试
- ✅ 表单元素存在性验证
- ✅ 用户协议复选框测试

#### 忘记密码功能测试
- ✅ 忘记密码页面功能测试
- ✅ 邮箱输入测试
- ✅ 返回登录链接测试

## 测试环境要求

- Node.js 18+
- Next.js 14
- Playwright
- 本地开发服务器运行在 `http://localhost:3000`

## 运行测试

### 前置条件
确保前端应用正在运行：
```bash
npm run dev
```

### 测试命令

```bash
# 运行所有测试
npm run test

# 运行测试并显示UI界面
npm run test:ui

# 运行测试（显示浏览器窗口）
npm run test:headed

# 调试模式运行测试
npm run test:debug

# 运行特定测试文件
npx playwright test login.spec.ts

# 运行特定测试用例
npx playwright test -g "完整登录流程测试"
```

### 浏览器支持

测试在以下浏览器中运行：
- ✅ Chromium (Chrome/Edge)
- ✅ Firefox
- ✅ WebKit (Safari)
- ✅ Mobile Chrome (Pixel 5)
- ✅ Mobile Safari (iPhone 12)

## 测试报告

测试完成后，可以查看HTML报告：
```bash
npx playwright show-report
```

## 测试数据

### 测试用户凭据
- **邮箱**: `test@example.com`
- **密码**: `password123`

> 注意：这些是测试用的模拟数据，实际登录会调用前端状态管理的模拟登录逻辑。

## 测试最佳实践

1. **页面对象模式**: 考虑使用页面对象模式来提高测试的可维护性
2. **数据驱动测试**: 使用不同的测试数据来验证各种场景
3. **并行执行**: 利用Playwright的并行测试能力提高测试效率
4. **视觉回归测试**: 可以添加截图对比来检测UI变化
5. **API模拟**: 使用Playwright的网络拦截功能模拟API响应

## 故障排除

### 常见问题

1. **测试超时**
   - 确保应用正在运行
   - 检查网络连接
   - 增加timeout配置

2. **元素找不到**
   - 检查选择器是否正确
   - 确认页面是否完全加载
   - 使用 `page.waitForSelector()` 等待元素

3. **浏览器启动失败**
   - 运行 `npx playwright install` 安装浏览器
   - 检查系统权限

## 未来改进计划

- [ ] 添加API层测试
- [ ] 实现视觉回归测试
- [ ] 添加性能测试
- [ ] 集成CI/CD流水线
- [ ] 添加测试覆盖率报告
- [ ] 实现页面对象模式重构

## 联系信息

如有测试相关问题，请联系开发团队。 