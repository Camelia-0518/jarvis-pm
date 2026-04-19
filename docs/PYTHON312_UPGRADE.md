# Python 3.12 升级指南

> 适用于 Windows 系统，用于安装 Kimi CLI

---

## 步骤1：下载 Python 3.12

### 方式A：官方安装包（推荐）

1. 访问 https://www.python.org/downloads/release/python-3120/
2. 下载 **Windows installer (64-bit)**
   - 文件名：`python-3.12.0-amd64.exe`
3. 运行安装程序
   - **重要**：勾选 "Add Python 3.12 to PATH"
   - 选择 "Install Now" 或自定义安装

### 方式B：Microsoft Store

```powershell
# 打开 PowerShell 作为管理员
winget install Python.Python.3.12
```

---

## 步骤2：验证安装

```powershell
# 打开新的 PowerShell 窗口
python3.12 --version
# 或
py -3.12 --version

# 预期输出：
# Python 3.12.0
```

---

## 步骤3：安装 Kimi CLI

```powershell
# 使用 Python 3.12 的 pip
python3.12 -m pip install kimi-cli

# 或
py -3.12 -m pip install kimi-cli
```

### 验证安装

```powershell
kimi --version

# 预期输出：
# kimi version 1.x.x
```

---

## 步骤4：配置 API Key

```powershell
# 设置你的 API Key
kimi config set api_key sk-kimi-bC5CRVbaxjfZwE37epUKMNFxTzpwgd3cQGmqXpKj5d04dqQPktfiuPDxD8VugoAV

# 验证配置
kimi config get api_key
```

---

## 步骤5：测试连接

```powershell
# 简单测试
kimi chat "Hello, please introduce yourself"

# 如果看到回复，说明配置成功
```

---

## 步骤6：配置虚拟环境（可选但推荐）

```powershell
# 创建 Python 3.12 虚拟环境
cd C:/Users/13400/.claude/projects/jarvis-pm/apps/api
python3.12 -m venv venv-312

# 激活虚拟环境
venv-312/Scripts/activate

# 安装依赖
pip install -r requirements.txt
pip install kimi-cli
```

---

## 故障排除

### 问题1：'python3.12' 不是内部或外部命令

**解决：**
```powershell
# 检查 Python 安装路径
where python

# 手动添加到 PATH
# 1. 找到 Python 3.12 安装目录（如 C:\Users\13400\AppData\Local\Programs\Python\Python312）
# 2. 添加到系统环境变量 PATH
# 3. 重启 PowerShell
```

### 问题2：kimi 命令找不到

**解决：**
```powershell
# 找到 pip 安装路径
python3.12 -m site

# 添加到 PATH
# 通常是：C:\Users\13400\AppData\Local\Programs\Python\Python312\Scripts
```

### 问题3：权限错误

**解决：**
```powershell
# 以管理员身份运行 PowerShell
# 然后重新安装
python3.12 -m pip install --user kimi-cli
```

---

## 下一步

完成以上步骤后，运行测试脚本：

```powershell
cd C:/Users/13400/.claude/projects/jarvis-pm
python test_kimi_cli.py
```

---

*升级完成后即可使用 Jarvis PM Agent 系统*
