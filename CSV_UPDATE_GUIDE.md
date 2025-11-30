# CSV测试结果更新指南

## 📋 使用 Filesystem MCP 工具更新CSV文件

### ⚠️ 重要说明

1. **浏览器要求**: **必须使用外部Chrome浏览器**，不能使用Cursor内置浏览器
2. **CSV文件位置**: **必须在Desktop目录**，因为Filesystem MCP工具只能访问Desktop和Documents目录

### 文件位置
- **文件路径**: `C:\Users\<用户名>\Desktop\test_results.csv`（桌面目录）
  - ⚠️ **重要**: Filesystem MCP工具只能访问以下目录：
    - `C:\Users\<用户名>\Desktop`
    - `C:\Users\<用户名>\Documents`
  - ⚠️ **不能**: 不能保存在项目根目录（不在允许的目录范围内）
- **文件格式**: CSV（UTF-8编码）

### 更新方式：使用 `edit_file` 工具（推荐）

**Filesystem MCP 提供了 `edit_file` 工具，可以直接编辑文件内容，无需使用代码！**

#### 方法1: 使用 edit_file 更新（最简单）

`edit_file` 工具可以基于行进行编辑，直接替换文件中的特定行。

**⚠️ 重要**: 必须使用完整路径，指向Desktop目录

**格式**:
```json
{
  "path": "C:\\Users\\<用户名>\\Desktop\\test_results.csv",
  "edits": [
    {
      "oldText": "Phase X,测试项名称,⬜,,,",
      "newText": "Phase X,测试项名称,状态,耗时,错误信息,备注"
    }
  ]
}
```

**示例** (使用实际用户名路径):

1. **测试通过**:
```json
{
  "path": "C:\\Users\\17625\\Desktop\\test_results.csv",
  "edits": [
    {
      "oldText": "Phase 1,环境准备,⬜,,,",
      "newText": "Phase 1,环境准备,✅,0.5,,"
    }
  ]
}
```

2. **测试失败（带错误信息）**:
```json
{
  "path": "C:\\Users\\17625\\Desktop\\test_results.csv",
  "edits": [
    {
      "oldText": "Phase 1,注册功能,⬜,,,",
      "newText": "Phase 1,注册功能,❌,3.5,400 Bad Request,邮箱已存在"
    }
  ]
}
```

3. **部分通过**:
```json
{
  "path": "C:\\Users\\17625\\Desktop\\test_results.csv",
  "edits": [
    {
      "oldText": "Phase 5,Chat页面加载,⬜,,,",
      "newText": "Phase 5,Chat页面加载,⚠️,2.0,部分API失败,页面正常但API请求失败"
    }
  ]
}
```

4. **性能测试（带备注）**:
```json
{
  "path": "C:\\Users\\17625\\Desktop\\test_results.csv",
  "edits": [
    {
      "oldText": "Phase 7,登录性能验证,⬜,,,",
      "newText": "Phase 7,登录性能验证,✅,2.1,,平均耗时2.1秒，符合预期<3秒"
    }
  ]
}
```

#### 方法2: 使用 write_file 重写整个文件（批量更新）

如果需要一次性更新多个测试项，可以读取整个文件，修改后使用 `write_file` 重写。

**步骤**:
1. 使用 `read_file` 读取整个CSV文件
2. 修改需要更新的行
3. 使用 `write_file` 写入整个文件

**示例**:
```json
{
  "path": "test_results.csv",
  "content": "测试阶段,测试项,状态,耗时(秒),错误信息,备注\nPhase 1,环境准备,✅,0.5,,\nPhase 1,首页测试,✅,1.2,,\n..."
}
```

### 状态符号说明

- ✅ **通过** - 测试完全通过
- ❌ **失败** - 测试失败
- ⚠️ **部分通过** - 部分功能正常，部分功能失败
- ⬜ **未测试** - 尚未测试（初始状态）

### 字段说明

1. **测试阶段**: Phase 1-7
2. **测试项**: 具体测试项目名称（必须与CSV中的完全一致）
3. **状态**: ✅ ❌ ⚠️ ⬜
4. **耗时(秒)**: 数字，保留2位小数，如 `0.50`、`1.23`、`2.10`
5. **错误信息**: 如果有错误，记录简短错误信息，如 `400 Bad Request`、`Failed to fetch`
6. **备注**: 其他备注信息，如 `邮箱已存在`、`平均耗时2.1秒`

### 更新流程

**每个测试项完成后**:

1. 记录测试结果（状态、耗时、错误信息、备注）
2. 使用 `edit_file` 工具更新对应的测试项行
3. CSV文件自动保存

### 完整示例

**示例1: 单个测试项更新**
```json
{
  "path": "test_results.csv",
  "edits": [
    {
      "oldText": "Phase 1,环境准备,⬜,,,",
      "newText": "Phase 1,环境准备,✅,0.5,,"
    }
  ]
}
```

**示例2: 多个测试项批量更新**
```json
{
  "path": "test_results.csv",
  "edits": [
    {
      "oldText": "Phase 1,环境准备,⬜,,,",
      "newText": "Phase 1,环境准备,✅,0.5,,"
    },
    {
      "oldText": "Phase 1,首页测试,⬜,,,",
      "newText": "Phase 1,首页测试,✅,1.2,,"
    },
    {
      "oldText": "Phase 1,注册功能,⬜,,,",
      "newText": "Phase 1,注册功能,❌,3.5,400 Bad Request,邮箱已存在"
    }
  ]
}
```

### 注意事项

1. **精确匹配**: `oldText` 必须与CSV文件中的行完全匹配（包括所有逗号和空格）
2. **整行替换**: 必须替换整行，不能只替换部分字段
3. **实时更新**: 每个测试项完成后立即更新，不要累积到最后统一更新
4. **多行更新**: `edit_file` 支持一次更新多行，使用数组形式

### 查看CSV内容

如果需要查看当前CSV文件内容：

使用 `read_file` 工具：
```json
{
  "path": "test_results.csv"
}
```

### CSV文件结构

**文件位置**: `C:\Users\<用户名>\Desktop\test_results.csv`

```csv
测试阶段,测试项,状态,耗时(秒),错误信息,备注
Phase 1,环境准备,⬜,,,
Phase 1,首页测试,⬜,,,
Phase 1,注册功能,⬜,,,
Phase 1,登录功能,⬜,,,
...
```

### ⚠️ 关键注意事项

1. **浏览器**: 必须使用外部Chrome浏览器，所有 `browser_navigate` 操作都会在外部浏览器中打开
2. **CSV文件路径**: 必须使用完整路径 `C:\Users\<用户名>\Desktop\test_results.csv`
3. **工具限制**: Filesystem MCP只能访问Desktop和Documents目录，不能访问项目根目录
4. **实时更新**: 每个测试项完成后立即使用 `edit_file` 更新CSV文件

### 测试完成后

测试完成后，`test_results.csv` 文件已包含所有测试结果，可以直接：
- ✅ 用Excel打开查看
- ✅ 用文本编辑器打开查看
- ✅ 复制到其他位置备份

**不需要**：
- ❌ 运行Python脚本
- ❌ 生成Markdown文件
- ❌ 手动复制到桌面
- ❌ 使用代码更新

### 为什么使用 edit_file？

1. **直接编辑**: Filesystem MCP 的 `edit_file` 工具就是专门用来编辑文件的
2. **简单直观**: 不需要写代码，直接指定要替换的文本
3. **实时保存**: 编辑后自动保存
4. **支持批量**: 可以一次更新多行
5. **符合MCP设计**: 这正是 MCP 工具的设计目的
