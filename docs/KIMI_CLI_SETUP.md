# Kimi CLI 安装配置指南

> 适用于 Kimi Coding API Key 用户

---

## 为什么需要 Kimi CLI

你的 API Key 是 **Kimi Coding API** 专用 Key，只能通过官方 CLI 工具访问。

**架构：**
```
Jarvis PM → 调用 Kimi CLI → Kimi Coding API
            (本地进程)      (云端)
```

---

## 安装步骤

### 步骤1: 安装 Kimi CLI

```bash
# 使用 pip 安装
pip install kimi-cli

# 或使用 pip3
pip3 install kimi-cli

# 验证安装
kimi --version
```

**预期输出：**
```
kimi version 1.x.x
```

---

### 步骤2: 配置 API Key

```bash
# 设置 API Key
kimi config set api_key sk-kimi-bC5CRVbaxjfZwE37epUKMNFxTzpwgd3cQGmqXpKj5d04dqQPktfiuPDxD8VugoAV

# 验证配置
kimi config get api_key
```

---

### 步骤3: 测试连接

```bash
# 简单测试
kimi chat "Hello, can you help me write Python code?"

# 如果看到回复，说明配置成功
```

---

## 在 Jarvis PM 中使用

安装配置完成后，Jarvis PM 会自动通过 Kimi CLI 调用 API。

**无需额外配置**，系统会检测并使用本地 `kimi` 命令。

---

## 故障排除

### 问题1: 'kimi' 不是内部或外部命令

**解决：**
```bash
# 找到 Python Scripts 目录
python -c "import site; print(site.getsitepackages())"

# 添加到环境变量
# Windows: 将 Python Scripts 路径添加到 PATH
# 例如: C:\Users\13400\AppData\Local\Programs\Python\Python311\Scripts
```

### 问题2: API Key 无效

**检查：**
```bash
# 检查 Key 是否正确设置
kimi config get api_key

# 重新设置
kimi config set api_key your-key-here
```

### 问题3: 调用超时

**解决：**
- 检查网络连接
- 尝试使用代理（如果需要）

---

## 下一步

安装完成后，运行测试脚本验证：

```bash
cd C:/Users/13400/.claude/projects/jarvis-pm
python test_kimi_cli.py
```

---

*配置完成后即可开始使用 Jarvis PM Agent 系统*
