# Agent 系统实现计划 (Kimi CLI 方案)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建以 Kimi CLI 为核心的 Agent 执行系统，Python 3.12+ 环境

**Architecture:** 通过 subprocess 调用本地 kimi 命令，彻底解决编码问题

**Tech Stack:** FastAPI, Python 3.12+, Kimi CLI, Redis, PostgreSQL

---

## 准备工作

### Task 0: Python 3.12 环境准备

**需要用户先完成：**
1. 安装 Python 3.12 (见 docs/PYTHON312_UPGRADE.md)
2. 安装 Kimi CLI: `python3.12 -m pip install kimi-cli`
3. 配置 API Key: `kimi config set api_key YOUR_KEY`
4. 验证: `kimi chat "Hello"`

**验证脚本：**
```bash
cd C:/Users/13400/.claude/projects/jarvis-pm
python3.12 test_kimi_cli.py
```

---

## 第一阶段：Agent 核心框架 (编码问题彻底解决)

### Task 1: 创建 Agent 基础类 (UTF-8 编码)

**Files:**
- Create: `apps/api/app/agents/__init__.py`
- Create: `apps/api/app/agents/base.py` (带 UTF-8 处理)
- Test: `apps/api/tests/agents/test_base.py`

**关键编码处理：**
```python
# 文件顶部添加
# -*- coding: utf-8 -*-
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

# subprocess 调用时指定编码
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding='utf-8'  # 关键！
)
```

---

### Task 2: 实现 Kimi CLI 客户端

**Files:**
- Create: `apps/api/app/agents/llm_client.py` (已完成，见文件)

**核心实现：**
```python
class KimiCLIClient(LLMClient):
    async def chat(self, messages, **kwargs):
        prompt = self._format_messages(messages)
        
        result = subprocess.run(
            ["kimi", "chat", "--no-stream", prompt],
            capture_output=True,
            text=True,
            encoding='utf-8',  # 彻底解决编码
            timeout=self.timeout
        )
        
        return result.stdout.strip()
```

---

### Task 3-9: 其他任务

与原文档相同，但所有文件都添加 UTF-8 编码声明。

---

## 编码问题彻底解决清单

每个 Python 文件必须包含：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件描述
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Windows 特殊处理
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

subprocess 调用必须：
```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding='utf-8'  # 必须指定
)
```

---

## 执行顺序

1. **用户先升级 Python 3.12** (自己完成)
2. **用户安装 Kimi CLI** (自己完成)
3. **我实现 Task 1-9** (Agent 系统)

确认 Python 3.12 和 Kimi CLI 就绪后，回复 "开始执行"，我立即开始 Task 1。
