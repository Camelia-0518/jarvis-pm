# PRD 生成器使用指南

## 功能概述

Jarvis PM 的 PRD 生成器是一个端到端的产品需求文档生成工具，支持：

- **智能行业检测**：自动识别医疗、电商、金融等行业
- **医疗行业模板**：内置病理切片借阅、病案复印等医疗专用模板
- **合规检查**：自动生成等保三级、患者隐私保护等合规章节
- **Obsidian集成**：一键保存到 Obsidian 知识库
- **多格式导出**：支持 Markdown、JSON、飞书格式

## 快速开始

### 1. 命令行工具

```bash
# 交互模式
python scripts/generate_prd.py --interactive

# 快速生成
python scripts/generate_prd.py "病理切片借阅平台" "需要一个病理切片借阅功能，患者可以在线申请"

# 指定行业
python scripts/generate_prd.py "病理切片借阅平台" "需求描述..." --industry medical
```

### 2. API 接口

```bash
# 生成 PRD
curl -X POST http://localhost:8000/api/v1/prd-generator/generate \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "病理切片借阅平台",
    "description": "患者可以在线申请借阅病理切片...",
    "industry": "medical",
    "save_to_obsidian": true,
    "save_local": true
  }'

# 快速生成
curl -X POST http://localhost:8000/api/v1/prd-generator/quick-generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "需要一个病理切片借阅功能..."
  }'

# 获取模板列表
curl http://localhost:8000/api/v1/prd-generator/templates

# 导出PRD
curl -X POST http://localhost:8000/api/v1/prd-generator/export \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# PRD内容...",
    "format": "feishu"
  }'
```

### 3. Python 代码调用

```python
from app.services.prd_generator import prd_generator_service
import asyncio

async def main():
    result = await prd_generator_service.generate_prd(
        product_name="病理切片借阅平台",
        description="患者可以在线申请借阅病理切片...",
        industry="medical",  # 或自动检测
        save_to_obsidian=True,
        save_local=True
    )

    if result["success"]:
        print(f"PRD生成成功!")
        print(f"内容长度: {result['metadata']['content_length']}")
        print(f"Obsidian路径: {result.get('obsidian_path')}")
        print(f"本地路径: {result.get('local_path')}")
        print(result["content"])  # PRD内容

asyncio.run(main())
```

## 医疗行业模板

### 内置模板

| 模板ID | 名称 | 适用场景 |
|--------|------|----------|
| `medical_slide_lending` | 病理切片借阅平台 | 病理切片借阅、数字切片 |
| `medical_admin_system` | 医疗管理后台 | 医院管理后台、权限管理 |

### 合规章节

自动生成以下合规章节：

1. **等保三级合规**
   - 身份鉴别机制（双因素认证）
   - 访问控制策略（RBAC权限模型）
   - 安全审计功能（操作日志完整记录）
   - 数据完整性保护（传输和存储加密）
   - 数据备份恢复机制

2. **患者隐私保护**
   - 患者身份信息脱敏处理
   - 敏感操作二次确认
   - 数据最小化原则
   - 隐私政策明确告知
   - 患者授权机制

3. **数据安全**
   - 数据分类分级管理
   - 敏感数据加密存储（AES-256）
   - 数据传输TLS加密
   - 数据访问日志记录
   - 数据保留期限管理

4. **操作审计追踪**
   - 用户操作全程记录
   - 数据修改留痕
   - 审计日志不可篡改
   - 异常行为告警
   - 定期审计报告

5. **跨院区数据同步**
   - 院区间数据隔离
   - 跨院区授权机制
   - 数据同步冲突处理
   - 离线模式支持
   - 数据一致性校验

## 输出示例

### 输入

```json
{
  "product_name": "病理切片借阅平台",
  "description": "需要一个病理切片借阅功能，患者可以在线申请借阅自己的病理切片，支持玻片借阅和数字切片查看",
  "industry": "medical"
}
```

### 输出

```markdown
---
generated_at: 2026-04-10 15:30:00
agent: prd_generator v1.0.0
---

# 病理切片借阅平台 - 产品需求文档 (PRD)

## 1. 背景与目标

### 1.1 产品背景
随着医疗信息化的发展，患者对病理切片的借阅需求日益增长...

### 1.2 业务目标
- 提供便捷的在线切片借阅服务
- 减少患者线下排队等待时间
- 提高病理科工作效率

### 1.3 成功指标
- 借阅申请线上化率 > 80%
- 平均处理时间 < 2个工作日
- 患者满意度 > 4.5/5

## 2. 用户故事

### 2.1 患者
- 作为患者，我想要在线申请借阅切片，以便节省时间
- 作为患者，我想要查看申请进度，以便了解处理状态

### 2.2 病理科工作人员
- 作为病理科人员，我想要审核借阅申请，以便确保合规
- 作为病理科人员，我想要管理切片库存，以便追踪去向

## 3. 业务流程

### 3.1 切片借阅流程
```
患者申请 -> 系统初审 -> 人工审核 -> 切片准备 -> 通知取片 -> 确认归还
```

## 4. 功能规格

### 4.1 患者端
| 功能模块 | 功能点 | 优先级 |
|---------|--------|--------|
| 申请管理 | 提交借阅申请 | P0 |
| 申请管理 | 上传证明材料 | P0 |
| 进度查询 | 查看申请状态 | P0 |
| 数字切片 | 在线查看切片 | P1 |

### 4.2 管理端
| 功能模块 | 功能点 | 优先级 |
|---------|--------|--------|
| 审核管理 | 申请审核 | P0 |
| 切片管理 | 库存管理 | P0 |
| 归还管理 | 归还确认 | P1 |

## 5. 数据需求

### 5.1 数据模型
- 申请单：申请ID、患者信息、切片信息、申请时间、状态
- 切片：切片ID、病理号、存储位置、状态
- 审核记录：记录ID、申请ID、审核人、审核结果、时间

## 6. 合规要求

### 6.1 等保三级合规
- [ ] 身份鉴别机制（双因素认证）
- [ ] 访问控制策略（RBAC权限模型）
- [ ] 安全审计功能（操作日志完整记录）
- [ ] 数据完整性保护（传输和存储加密）

### 6.2 患者隐私保护
- [ ] 患者身份信息脱敏处理
- [ ] 敏感操作二次确认
- [ ] 数据最小化原则

## 7. 数据埋点

| 事件 | 触发时机 | 属性 |
|------|---------|------|
| 申请提交 | 患者提交申请 | 申请类型、患者ID |
| 审核完成 | 审核人完成审核 | 审核结果、耗时 |

## 8. 里程碑

| 阶段 | 时间 | 交付物 |
|------|------|--------|
| Phase 1 | 第1-2周 | 申请功能上线 |
| Phase 2 | 第3-4周 | 审核功能上线 |
| Phase 3 | 第5-6周 | 数字切片功能 |
```

## 文件存储位置

### Obsidian
```
Documents/Obsidian/MyVault/04-项目层/Agent生成/医疗项目/
├── {产品名}_PRD_{日期}.md
```

### 本地文件
```
~/.jarvis/prd_outputs/
├── {产品名}_PRD_{日期时间}.md
```

## 配置说明

### 环境变量

```bash
# AI 服务配置
KIMI_API_KEY=your_kimi_api_key
DEFAULT_AI_PROVIDER=kimi

# Obsidian 路径（可选）
OBSIDIAN_VAULT_PATH=C:/Users/13400/Documents/Obsidian/MyVault
```

### 自定义模板

```python
from app.agents.templates import IndustryTemplate, ComplianceRequirement, IndustryType

template = IndustryTemplate(
    id="my_custom_template",
    name="自定义模板",
    industry=IndustryType.MEDICAL,
    description="描述",
    keywords=["关键词1", "关键词2"],
    compliance_requirements=[
        ComplianceRequirement(
            name="合规项",
            description="描述",
            category="security",
            priority="critical",
            checklist=["检查点1", "检查点2"]
        )
    ],
    workflow_enhancements={},
    agent_prompts={},
    mandatory_checks=[]
)

template_system.register_custom_template(template)
```

## 测试

```bash
# 运行测试
python tests/test_prd_generator.py

# 测试输出位置
tests/outputs/
```

## 故障排查

### 常见问题

1. **API 调用失败**
   - 检查 `KIMI_API_KEY` 是否配置
   - 检查网络连接

2. **Obsidian 保存失败**
   - 检查 Obsidian Vault 路径是否正确
   - 确保有写入权限

3. **模板匹配失败**
   - 确保描述中包含行业关键词
   - 手动指定 `industry` 参数

## 更新日志

### v1.0.0 (2026-04-10)
- ✅ PRD 生成功能（核心）
- ✅ 医疗行业模板
- ✅ Obsidian 集成
- ✅ 本地存储
- ✅ Markdown/JSON/飞书导出
