#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端集成测试

测试完整工作流、组件集成和医疗场景
"""

import os
import sys
import asyncio
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, '..'))

from app.agents.progress import ProgressTracker, StepStatus, WorkflowProgress
from app.agents.persistence import WorkflowState, WorkflowPersistence, get_persistence, reset_persistence
from app.agents.strategy import StrategyLayer, WorkflowContext, ProgressTracker as StrategyProgressTracker
from app.agents.templates import TemplateSystem, IndustryType, get_template_system
from app.websocket.manager import WebSocketManager
from app.websocket.events import EventEmitter


# ==================== Mock Agent ====================

class MockAgent:
    """Mock Agent 用于测试"""

    def __init__(self, name: str, delay: float = 0.1):
        self.name = name
        self.delay = delay
        self.execute = AsyncMock()

    async def run(self, input_data: Dict) -> Dict:
        await asyncio.sleep(self.delay)
        return {
            "agent": self.name,
            "input": input_data,
            "output": f"Mock result from {self.name}",
            "timestamp": datetime.now().isoformat()
        }


# ==================== 完整工作流测试 ====================

class TestFullWorkflow:
    """测试完整工作流"""

    @pytest.fixture
    def progress_tracker(self):
        """创建进度追踪器"""
        return ProgressTracker()

    @pytest.fixture
    def template_system(self):
        """创建模板系统"""
        return TemplateSystem()

    def test_full_prd_workflow(self, progress_tracker):
        """测试PRD生成完整流程"""
        # 初始化工作流
        workflow_id = progress_tracker.initialize_workflow(
            user_input="帮我设计一个病理切片借阅平台",
            template_name="prd_only"
        )

        assert workflow_id is not None
        workflow = progress_tracker.get_workflow(workflow_id)
        assert workflow is not None
        assert len(workflow.steps) == 4  # PRD模板有4个步骤

        # 模拟执行每个步骤
        for i, step in enumerate(workflow.steps):
            # 开始步骤
            progress_tracker.start_step(workflow_id, step.id)
            assert step.status == StepStatus.RUNNING

            # 更新进度
            progress_tracker.update_step_progress(workflow_id, step.id, 50, f"执行中...{i+1}/4")
            assert step.progress == 50

            # 完成步骤
            progress_tracker.complete_step(workflow_id, step.id, f"步骤{i+1}完成")
            assert step.status == StepStatus.COMPLETED
            assert step.progress == 100

        # 完成工作流
        progress_tracker.complete_workflow(workflow_id, "PRD生成完成")
        workflow = progress_tracker.get_workflow(workflow_id)
        assert workflow.status == StepStatus.COMPLETED
        assert workflow.overall_progress == 100

    def test_compliance_workflow(self, progress_tracker):
        """测试合规模板流程"""
        workflow_id = progress_tracker.initialize_workflow(
            user_input="检查病理切片借阅平台的合规性",
            template_name="compliance_only"
        )

        workflow = progress_tracker.get_workflow(workflow_id)
        assert len(workflow.steps) == 3  # 合规模板有3个步骤

        step_names = [step.name for step in workflow.steps]
        assert "需求分析" in step_names
        assert "合规检查" in step_names
        assert "风险评估" in step_names

    def test_checkpoint_workflow(self, progress_tracker):
        """测试检查点交互流程"""
        workflow_id = progress_tracker.initialize_workflow(
            user_input="设计医疗系统",
            template_name="full_workflow"
        )

        # 执行到检查点
        workflow = progress_tracker.get_workflow(workflow_id)
        step = workflow.steps[0]

        progress_tracker.start_step(workflow_id, step.id)
        progress_tracker.update_step_progress(workflow_id, step.id, 80)

        # 设置检查点等待
        progress_tracker.wait_for_checkpoint(workflow_id, step.id, "请确认需求分析结果")
        assert step.status == StepStatus.WAITING
        assert "请确认需求分析结果" in step.detail

        # 继续执行
        progress_tracker.start_step(workflow_id, step.id)
        progress_tracker.complete_step(workflow_id, step.id, "已确认")
        assert step.status == StepStatus.COMPLETED


# ==================== 组件集成测试 ====================

class TestComponentIntegration:
    """测试组件集成"""

    @pytest.fixture
    def websocket_manager(self):
        """创建WebSocket管理器"""
        return WebSocketManager()

    @pytest.fixture
    def progress_tracker(self):
        """创建进度追踪器"""
        return ProgressTracker()

    @pytest.mark.asyncio
    async def test_progress_with_websocket(self, progress_tracker):
        """测试进度追踪与WebSocket集成"""
        workflow_id = "test-workflow-123"

        # 创建事件发射器
        emitter = EventEmitter(workflow_id)

        # 模拟WebSocket连接 - 需要patch全局websocket_manager
        mock_websocket = AsyncMock()
        from app.websocket.manager import websocket_manager as global_ws_manager
        original_connections = global_ws_manager.active_connections
        global_ws_manager.active_connections = {workflow_id: [mock_websocket]}

        try:
            # 发射进度事件
            await emitter.emit_progress("需求分析", 50, "正在分析需求...")

            # 验证消息已发送
            mock_websocket.send_text.assert_called_once()
            sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert sent_message["type"] == "progress"
            assert sent_message["step"] == "需求分析"
            assert sent_message["progress"] == 50
        finally:
            # 恢复原始状态
            global_ws_manager.active_connections = original_connections

    def test_checkpoint_with_strategy(self):
        """测试检查点与Strategy Layer集成"""
        strategy = StrategyLayer()

        # 创建工作流上下文
        workflow_id = "test-checkpoint-workflow"
        context = WorkflowContext(
            workflow_id=workflow_id,
            user_input="测试检查点功能"
        )
        strategy._workflows[workflow_id] = context

        # 验证工作流已注册
        retrieved = strategy.get_workflow(workflow_id)
        assert retrieved is not None
        assert retrieved.user_input == "测试检查点功能"

    def test_template_with_planner(self):
        """测试模板与Task Planner集成"""
        template_system = TemplateSystem()

        # 匹配医疗模板
        template = template_system.match_template("病理切片借阅平台")
        assert template is not None
        assert template.industry == IndustryType.MEDICAL

        # 应用到计划
        original_plan = {
            "workflow_name": "病理切片借阅PRD",
            "steps": [
                {"id": "step_1", "agent_name": "prd_generator"}
            ]
        }

        enhanced_plan = template_system.apply_template_to_plan(template, original_plan)

        # 验证增强内容
        assert "compliance_requirements" in enhanced_plan
        assert "mandatory_checks" in enhanced_plan
        assert "agent_prompts" in enhanced_plan

        # 验证合规要求
        compliance_reqs = enhanced_plan["compliance_requirements"]
        assert len(compliance_reqs) == 5

    def test_recovery_with_persistence(self, tmp_path):
        """测试故障恢复与持久化集成"""
        # 重置持久化实例
        reset_persistence()

        storage_dir = str(tmp_path / "workflows")
        persistence = get_persistence(storage_dir)

        # 创建工作流状态
        workflow = WorkflowState(
            workflow_id="recovery-test-001",
            status="running",
            current_step="step_2",
            user_input="测试恢复功能",
            step_results={
                "step_1": {"status": "completed", "result": "步骤1完成"},
                "step_2": {"status": "running", "progress": 50}
            }
        )

        # 保存工作流
        assert persistence.save(workflow) is True

        # 模拟故障后重新加载
        reset_persistence()
        persistence2 = get_persistence(storage_dir)

        loaded = persistence2.load("recovery-test-001")
        assert loaded is not None
        assert loaded.status == "running"
        assert loaded.current_step == "step_2"
        assert "step_1" in loaded.step_results
        assert loaded.step_results["step_1"]["status"] == "completed"

        # 验证可以恢复执行
        completed_steps = loaded.get_completed_steps()
        assert "step_1" in completed_steps


# ==================== 医疗场景测试 ====================

class TestMedicalScenarios:
    """测试医疗行业特定场景"""

    @pytest.fixture
    def template_system(self):
        """创建模板系统"""
        return TemplateSystem()

    @pytest.fixture
    def progress_tracker(self):
        """创建进度追踪器"""
        return ProgressTracker()

    def test_medical_slide_lending(self, template_system):
        """测试病理切片借阅平台场景"""
        # 检测行业
        industry = template_system.detect_industry("病理切片借阅平台")
        assert industry == IndustryType.MEDICAL

        # 匹配模板
        template = template_system.match_template("病理切片借阅平台")
        assert template is not None
        assert template.id == "medical_slide_lending"

        # 验证合规要求
        assert len(template.compliance_requirements) == 5

        req_names = [r.name for r in template.compliance_requirements]
        assert "等保三级合规" in req_names
        assert "患者隐私保护" in req_names
        assert "医疗数据安全" in req_names

        # 验证强制检查项
        assert len(template.mandatory_checks) == 5
        assert "等保三级合规检查" in template.mandatory_checks
        assert "患者隐私保护检查" in template.mandatory_checks

        # 验证Agent提示词
        assert "prd_generator" in template.agent_prompts
        prd_prompt = template.agent_prompts["prd_generator"]
        assert "等保三级合规" in prd_prompt
        assert "患者隐私保护" in prd_prompt

    def test_medical_admin_system(self, template_system):
        """测试医疗管理后台场景"""
        # 检测行业
        industry = template_system.detect_industry("医院管理后台系统")
        assert industry == IndustryType.MEDICAL

        # 匹配模板
        template = template_system.match_template("医院管理后台系统")
        assert template is not None
        assert template.id == "medical_admin_system"

        # 验证合规要求
        assert len(template.compliance_requirements) == 4

        req_names = [r.name for r in template.compliance_requirements]
        assert "权限管理" in req_names
        assert "操作审计" in req_names

        # 验证工作流增强
        assert "mandatory_agents" in template.workflow_enhancements
        assert "compliance_checker" in template.workflow_enhancements["mandatory_agents"]

    def test_medical_compliance_checklist(self, template_system):
        """测试医疗合规检查清单"""
        template = template_system.get_template("medical_slide_lending")

        # 获取完整检查清单
        checklist = template_system.get_compliance_checklist(template)
        assert len(checklist) == 5

        # 验证清单结构
        first_item = checklist[0]
        assert "name" in first_item
        assert "description" in first_item
        assert "category" in first_item
        assert "priority" in first_item
        assert "checklist" in first_item

        # 按类别筛选
        security_reqs = template_system.get_compliance_checklist(template, category="security")
        assert len(security_reqs) >= 2

        privacy_reqs = template_system.get_compliance_checklist(template, category="privacy")
        assert len(privacy_reqs) >= 1

    def test_medical_prd_generation_workflow(self, progress_tracker):
        """测试医疗PRD生成工作流"""
        workflow_id = progress_tracker.initialize_workflow(
            user_input="设计病理切片借阅平台",
            template_name="full_workflow"
        )

        workflow = progress_tracker.get_workflow(workflow_id)

        # 验证工作流包含合规检查步骤
        step_names = [step.name for step in workflow.steps]
        assert "合规检查" in step_names

        # 模拟执行到合规检查步骤
        compliance_step = None
        for step in workflow.steps:
            if step.name == "合规检查":
                compliance_step = step
                break

        assert compliance_step is not None
        assert compliance_step.agent_name == "compliance-checker"

        # 执行合规检查步骤
        progress_tracker.start_step(workflow_id, compliance_step.id)
        progress_tracker.update_step_progress(
            workflow_id,
            compliance_step.id,
            50,
            "检查等保三级合规要求..."
        )
        progress_tracker.complete_step(
            workflow_id,
            compliance_step.id,
            "合规检查通过：等保三级、患者隐私保护、数据安全均符合要求"
        )

        assert compliance_step.status == StepStatus.COMPLETED
        assert "等保三级" in compliance_step.result_summary


# ==================== 并发和性能测试 ====================

class TestConcurrency:
    """测试并发性能"""

    @pytest.mark.asyncio
    async def test_multiple_workflows(self):
        """测试多工作流并发执行"""
        tracker = ProgressTracker()

        # 创建多个工作流
        workflow_ids = []
        for i in range(5):
            wf_id = tracker.initialize_workflow(
                user_input=f"测试工作流 {i+1}",
                template_name="prd_only"
            )
            workflow_ids.append(wf_id)

        assert len(workflow_ids) == 5

        # 并发执行所有工作流的第一步
        async def execute_first_step(wf_id):
            workflow = tracker.get_workflow(wf_id)
            step = workflow.steps[0]
            tracker.start_step(wf_id, step.id)
            await asyncio.sleep(0.01)  # 模拟执行时间
            tracker.complete_step(wf_id, step.id, "完成")
            return wf_id

        tasks = [execute_first_step(wf_id) for wf_id in workflow_ids]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5

        # 验证所有工作流的第一步都已完成
        for wf_id in workflow_ids:
            workflow = tracker.get_workflow(wf_id)
            assert workflow.steps[0].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_high_frequency_updates(self):
        """测试高频进度更新"""
        tracker = ProgressTracker()

        workflow_id = tracker.initialize_workflow(
            user_input="高频更新测试",
            template_name="prd_only"
        )

        workflow = tracker.get_workflow(workflow_id)
        step = workflow.steps[0]
        tracker.start_step(workflow_id, step.id)

        # 高频更新进度
        update_count = 100
        for i in range(update_count):
            tracker.update_step_progress(
                workflow_id,
                step.id,
                int((i + 1) / update_count * 100),
                f"进度 {i+1}/{update_count}"
            )

        assert step.progress == 100


# ==================== 错误处理测试 ====================

class TestErrorHandling:
    """测试错误处理"""

    @pytest.fixture
    def progress_tracker(self):
        """创建进度追踪器"""
        return ProgressTracker()

    def test_workflow_not_found(self):
        """测试工作流不存在错误"""
        tracker = ProgressTracker()

        with pytest.raises(KeyError):
            tracker.start_step("non-existent-workflow", "step-1")

    def test_step_not_found(self, progress_tracker):
        """测试步骤不存在错误"""
        workflow_id = progress_tracker.initialize_workflow(
            user_input="测试",
            template_name="prd_only"
        )

        with pytest.raises(ValueError):
            progress_tracker.start_step(workflow_id, "non-existent-step")

    def test_invalid_progress_value(self, progress_tracker):
        """测试无效进度值错误"""
        workflow_id = progress_tracker.initialize_workflow(
            user_input="测试",
            template_name="prd_only"
        )

        workflow = progress_tracker.get_workflow(workflow_id)
        step = workflow.steps[0]

        with pytest.raises(ValueError):
            progress_tracker.update_step_progress(workflow_id, step.id, 150)

    def test_step_failure_recovery(self, progress_tracker):
        """测试步骤失败和恢复"""
        workflow_id = progress_tracker.initialize_workflow(
            user_input="测试失败恢复",
            template_name="prd_only"
        )

        workflow = progress_tracker.get_workflow(workflow_id)
        step = workflow.steps[0]

        # 开始步骤
        progress_tracker.start_step(workflow_id, step.id)

        # 标记步骤失败
        progress_tracker.fail_step(workflow_id, step.id, "执行超时")

        assert step.status == StepStatus.FAILED
        assert workflow.status == StepStatus.FAILED
        assert "执行超时" in step.result_summary


# ==================== 主函数 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
