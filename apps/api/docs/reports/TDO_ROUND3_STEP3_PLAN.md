# TDO Round 3 Step 3: 优化方案定义

> **阶段**: 测试驱动优化 - 方案定义  
> **日期**: 2026-04-11  
> **目标**: 修复工作流输入映射和步骤名称显示问题

---

## 🎯 优化目标

### P1-002: 修复工作流输入映射
**问题**: 工作流步骤执行时，技能输入验证失败

### P2-002: 修复步骤名称显示
**问题**: 步骤结果显示为 `None` 而不是实际名称

---

## 📋 技术方案

### 方案A: 修复预定义工作流的输入映射

**问题分析**:
当前 `product-design` 工作流定义:
```python
WorkflowStep(
    skill_id="business-model",
    step_name="商业模式",
    inputs_mapping={
        "productDescription": "$.steps.需求分析.output.productOneLiner"
    }
)
```

**问题**:
- `business-model` 技能需要 `market` 参数 (required)
- 但 `inputs_mapping` 中没有提供

**修复方案**:
```python
WorkflowStep(
    skill_id="business-model",
    step_name="商业模式",
    inputs_mapping={
        "productDescription": "$.steps.需求分析.output.productOneLiner",
        "market": "$.initial.targetUsers",  # 添加缺失的参数
        "competitors": ""  # 可选参数
    }
)
```

---

### 方案B: 修复步骤名称传递

**问题分析**:
在 `execute_workflow` 中创建 `WorkflowStepResult`:
```python
step_result = WorkflowStepResult(
    step_name=step.skill_id,  # ❌ 这里用了 skill_id 而不是 step_name
    ...
)
```

**修复方案**:
```python
step_result = WorkflowStepResult(
    step_name=step.step_name,  # ✅ 使用 step.step_name
    ...
)
```

---

### 方案C: 增强输入验证调试

**添加调试日志**:
```python
# 在执行技能前添加日志
print(f"[DEBUG] Executing skill {step.skill_id}")
print(f"[DEBUG] Inputs: {step_inputs}")
```

---

## 🎨 选择的方案

### 必选 (P1)
- ✅ 方案A: 修复工作流输入映射
- ✅ 方案B: 修复步骤名称传递

### 可选 (P2)
- 💡 方案C: 添加调试日志

---

## 📝 实施计划

### 修改文件
1. `app/services/workflow_engine.py`
   - 修复 `STANDARD_WORKFLOWS` 中的输入映射
   - 修复 `execute_workflow` 中的 `step_name` 传递

### 修改详情

#### 修改1: 修复 product-design 工作流
```python
# 找到 product-design 的定义
"product-design": WorkflowDefinition(
    ...
    steps=[
        WorkflowStep(...),  # 需求分析 - 不需要修改
        WorkflowStep(        # 商业模式 - 需要修改
            skill_id="business-model",
            step_name="商业模式",
            inputs_mapping={
                "productDescription": "$.steps.需求分析.output.productOneLiner",
                "market": "$.initial.targetUsers",
                "competitors": ""
            }
        ),
        ...
    ]
)
```

#### 修改2: 修复步骤名称传递
```python
# 在 execute_workflow 方法中
step_result = WorkflowStepResult(
    step_name=step.step_name,  # 使用 step.step_name 而不是 step.skill_id
    skill_id=step.skill_id,
    ...
)
```

---

## ✅ 验收标准

- [ ] `product-design` 工作流可以成功完成
- [ ] 所有工作流步骤显示正确的步骤名称
- [ ] 完整场景测试通过
- [ ] 工作流执行时间合理 (<5s)

---

## 🧪 测试用例

### 测试1: 工作流成功执行
```python
result = await engine.execute_workflow(
    'product-design',
    initial_inputs={
        'idea': 'Test product',
        'targetUsers': 'Test users',
        'industry': 'medical'
    }
)
assert result['completed'] == True
```

### 测试2: 步骤名称正确显示
```python
for step in result['results']:
    assert step['step_name'] is not None
    assert step['step_name'] != ''
```

---

*方案定义完成，准备进入Step 4: 执行修复*
