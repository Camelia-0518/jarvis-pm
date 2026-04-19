# TDO Step 3: 优化方案定义

> **阶段**: 测试驱动优化 - 方案定义  
> **日期**: 2026-04-11  
> **目标问题**: P1-001 WorkflowExecutionResult类型不匹配

---

## 🎯 优化目标

**问题**: `WorkflowEngine.execute_workflow()` 返回 `WorkflowExecutionResult` 对象，但用户代码期望返回字典

**目标**: 让工作流引擎返回的结果可以直接使用 `.get()` 方法

---

## 📋 技术方案

### 方案A: 返回字典 (推荐) ✅

**修改位置**: `app/services/workflow_engine.py`

**修改内容**:
```python
# 修改前
async def execute_workflow(...) -> WorkflowExecutionResult:
    ...
    return WorkflowExecutionResult(...)

# 修改后
async def execute_workflow(...) -> Dict[str, Any]:
    ...
    result = WorkflowExecutionResult(...)
    return result.to_dict()  # 返回字典
```

**优点**:
- 符合用户期望
- 与现有API保持一致
- 简单直接

**缺点**:
- 失去类型提示
- 但可以通过类型注解解决

---

### 方案B: WorkflowExecutionResult继承dict

**修改内容**:
```python
# 修改前
@dataclass
class WorkflowExecutionResult:
    workflow: str
    completed: bool
    ...

# 修改后
class WorkflowExecutionResult(dict):
    def __init__(self, workflow: str, completed: bool, ...):
        super().__init__(...)
        self.workflow = workflow
        self.completed = completed
        ...
```

**优点**:
- 保持类型提示
- 可以直接使用 .get()

**缺点**:
- 修改较大
- 可能影响其他代码

---

## 🎨 选择的方案: 方案A

**原因**:
1. 与 `SkillProcessor.execute_skill()` 返回格式一致（都是dict）
2. 改动最小，风险最低
3. 用户无需了解内部数据类

---

## 📝 实施计划

### 修改文件
- `app/services/workflow_engine.py`
  - 修改 `execute_workflow()` 返回类型
  - 修改 `execute_workflow_stream()` 返回类型
  - 确保调用 `to_dict()`

### 回归测试
- 重新运行工作流引擎测试
- 验证返回类型正确

---

## ✅ 验收标准

- [ ] `execute_workflow()` 返回字典类型
- [ ] 返回的字典可以使用 `.get()` 方法
- [ ] 包含所有必需字段
- [ ] 测试通过

---

*方案定义完成，准备进入Step 4: 并行优化*
