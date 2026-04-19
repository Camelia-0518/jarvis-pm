#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试故障恢复与断点续传功能
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

import pytest
from app.agents.persistence import (
    WorkflowState,
    WorkflowPersistence,
    get_persistence,
    reset_persistence
)
from app.agents.recovery import (
    RecoveryManager,
    RecoveryInfo,
    get_recovery_manager,
    reset_recovery_manager
)


class TestWorkflowPersistence:
    """测试工作流持久化功能"""

    @pytest.fixture
    def temp_storage(self):
        """创建临时存储目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
        reset_persistence()

    @pytest.fixture
    def persistence(self, temp_storage):
        """创建持久化实例"""
        return WorkflowPersistence(temp_storage)

    def test_workflow_state_creation(self):
        """测试工作流状态创建"""
        state = WorkflowState(
            workflow_id="test-123",
            status="running",
            user_input="测试输入"
        )

        assert state.workflow_id == "test-123"
        assert state.status == "running"
        assert state.user_input == "测试输入"
        assert state.step_results == {}
        assert state.current_step is None

    def test_workflow_state_to_dict(self):
        """测试工作流状态转换为字典"""
        state = WorkflowState(
            workflow_id="test-123",
            status="running",
            user_input="测试输入"
        )

        data = state.to_dict()
        assert data["workflow_id"] == "test-123"
        assert data["status"] == "running"
        assert data["user_input"] == "测试输入"

    def test_workflow_state_from_dict(self):
        """测试从字典创建工作流状态"""
        data = {
            "workflow_id": "test-123",
            "status": "completed",
            "current_step": "step_2",
            "step_results": {"step_1": {"status": "completed"}},
            "user_input": "测试",
            "intent_result": None,
            "plan": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "error": None
        }

        state = WorkflowState.from_dict(data)
        assert state.workflow_id == "test-123"
        assert state.status == "completed"
        assert state.current_step == "step_2"

    def test_get_completed_steps(self):
        """测试获取已完成步骤"""
        state = WorkflowState(
            workflow_id="test-123",
            step_results={
                "step_1": {"status": "completed"},
                "step_2": {"result": "some data"},
                "step_3": {"status": "failed", "error": "error"}
            }
        )

        completed = state.get_completed_steps()
        assert "step_1" in completed
        assert "step_2" in completed
        assert "step_3" not in completed

    def test_is_step_completed(self):
        """测试检查步骤是否完成"""
        state = WorkflowState(
            workflow_id="test-123",
            step_results={
                "step_1": {"status": "completed"},
                "step_2": {"result": "data"},
                "step_3": {"status": "failed"}
            }
        )

        assert state.is_step_completed("step_1") is True
        assert state.is_step_completed("step_2") is True
        assert state.is_step_completed("step_3") is False
        assert state.is_step_completed("step_4") is False

    def test_save_and_load(self, persistence):
        """测试保存和加载工作流"""
        state = WorkflowState(
            workflow_id="test-save-123",
            status="running",
            user_input="测试保存",
            current_step="step_1",
            step_results={"step_1": {"status": "completed"}}
        )

        # 保存
        result = persistence.save(state)
        assert result is True

        # 加载
        loaded = persistence.load("test-save-123")
        assert loaded is not None
        assert loaded.workflow_id == "test-save-123"
        assert loaded.status == "running"
        assert loaded.user_input == "测试保存"
        assert loaded.step_results["step_1"]["status"] == "completed"

    def test_load_nonexistent(self, persistence):
        """测试加载不存在的工作流"""
        loaded = persistence.load("nonexistent-id")
        assert loaded is None

    def test_update_step(self, persistence):
        """测试更新步骤"""
        # 先创建工作流
        state = WorkflowState(
            workflow_id="test-update-123",
            status="running"
        )
        persistence.save(state)

        # 更新步骤
        result = persistence.update_step(
            "test-update-123",
            "step_1",
            {"status": "completed", "data": "result"}
        )
        assert result is True

        # 验证更新
        loaded = persistence.load("test-update-123")
        assert loaded.current_step == "step_1"
        assert loaded.step_results["step_1"]["status"] == "completed"

    def test_update_workflow_status(self, persistence):
        """测试更新工作流状态"""
        state = WorkflowState(
            workflow_id="test-status-123",
            status="running"
        )
        persistence.save(state)

        # 更新状态
        result = persistence.update_workflow_status(
            "test-status-123",
            "failed",
            "Something went wrong"
        )
        assert result is True

        # 验证
        loaded = persistence.load("test-status-123")
        assert loaded.status == "failed"
        assert loaded.error == "Something went wrong"

    def test_list_active(self, persistence):
        """测试列出活跃工作流"""
        # 创建多个工作流
        for i in range(3):
            state = WorkflowState(
                workflow_id=f"active-{i}",
                status="running" if i < 2 else "completed"
            )
            persistence.save(state)

        active = persistence.list_active()
        assert len(active) == 2
        assert all(s.status in {"running", "pending"} for s in active)

    def test_cleanup_old(self, persistence):
        """测试清理过期工作流"""
        # 创建一个过期的工作流
        old_state = WorkflowState(
            workflow_id="old-workflow",
            status="completed"
        )
        # 手动修改时间为过去
        old_state.updated_at = (datetime.now() - timedelta(hours=48)).isoformat()
        persistence.save(old_state)

        # 创建一个新的工作流
        new_state = WorkflowState(
            workflow_id="new-workflow",
            status="completed"
        )
        persistence.save(new_state)

        # 清理超过24小时的
        cleaned = persistence.cleanup_old(max_age_hours=24)
        assert cleaned == 1

        # 验证旧工作流已被删除
        assert persistence.load("old-workflow") is None
        assert persistence.load("new-workflow") is not None

    def test_delete(self, persistence):
        """测试删除工作流"""
        state = WorkflowState(
            workflow_id="to-delete",
            status="completed"
        )
        persistence.save(state)

        # 删除
        result = persistence.delete("to-delete")
        assert result is True

        # 验证
        assert persistence.load("to-delete") is None


class TestRecoveryManager:
    """测试故障恢复管理器"""

    @pytest.fixture
    def temp_storage(self):
        """创建临时存储目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
        reset_persistence()
        reset_recovery_manager()

    @pytest.fixture
    def recovery_manager(self, temp_storage):
        """创建恢复管理器实例"""
        persistence = WorkflowPersistence(temp_storage)
        return RecoveryManager(persistence)

    @pytest.mark.asyncio
    async def test_start_workflow(self, recovery_manager):
        """测试启动工作流"""
        success, message = await recovery_manager.start_workflow(
            "workflow-1",
            "测试输入"
        )

        assert success is True
        assert "started" in message.lower() or "启动" in message

        # 验证工作流已创建
        info = recovery_manager.get_recovery_info("workflow-1")
        assert info is not None
        assert info.status == "running"

    @pytest.mark.asyncio
    async def test_start_existing_workflow(self, recovery_manager):
        """测试启动已存在的工作流"""
        # 先启动一个工作流
        await recovery_manager.start_workflow("workflow-2", "测试")

        # 再次启动应该失败
        success, message = await recovery_manager.start_workflow(
            "workflow-2",
            "另一个输入"
        )

        assert success is False
        assert "already running" in message.lower() or "already" in message.lower()

    def test_get_recovery_info(self, recovery_manager):
        """测试获取恢复信息"""
        # 先创建工作流
        state = WorkflowState(
            workflow_id="recovery-test",
            status="failed",
            current_step="step_2",
            step_results={
                "step_1": {"status": "completed"},
                "step_2": {"status": "failed", "error": "error"}
            },
            user_input="测试恢复",
            error="Something failed"
        )
        recovery_manager.persistence.save(state)

        # 获取恢复信息
        info = recovery_manager.get_recovery_info("recovery-test")
        assert info is not None
        assert info.workflow_id == "recovery-test"
        assert info.status == "failed"
        assert info.current_step == "step_2"
        assert "step_1" in info.completed_steps
        assert info.error == "Something failed"

    def test_can_skip_step(self, recovery_manager):
        """测试步骤跳过判断"""
        # 已完成的步骤
        assert recovery_manager._can_skip_step("step_1", {"status": "completed"}) is True

        # 有结果无错误的步骤
        assert recovery_manager._can_skip_step("step_1", {"result": "data"}) is True

        # 有completed_at的步骤
        assert recovery_manager._can_skip_step("step_1", {"completed_at": "2024-01-01"}) is True

        # 失败的步骤
        assert recovery_manager._can_skip_step("step_1", {"status": "failed"}) is False

        # 有错误的步骤
        assert recovery_manager._can_skip_step("step_1", {"error": "error"}) is False

        # 非字典结果
        assert recovery_manager._can_skip_step("step_1", "some string") is False

    def test_get_skippable_steps(self, recovery_manager):
        """测试获取可跳过步骤"""
        state = WorkflowState(
            workflow_id="skip-test",
            step_results={
                "step_1": {"status": "completed"},
                "step_2": {"result": "data"},
                "step_3": {"status": "failed"},
                "step_4": {"status": "completed"}
            }
        )
        recovery_manager.persistence.save(state)

        skippable = recovery_manager.get_skippable_steps("skip-test")
        assert "step_1" in skippable
        assert "step_2" in skippable
        assert "step_3" not in skippable
        assert "step_4" in skippable

    def test_get_resume_index(self, recovery_manager):
        """测试获取恢复索引"""
        state = WorkflowState(
            workflow_id="resume-test",
            step_results={
                "step_0": {"status": "completed"},
                "step_1": {"status": "completed"}
            }
        )

        plan_steps = [
            {"id": "step_0"},
            {"id": "step_1"},
            {"id": "step_2"},
            {"id": "step_3"}
        ]

        index = recovery_manager._get_resume_index(state, plan_steps)
        assert index == 2  # 应该从 step_2 开始

    def test_get_resume_index_all_completed(self, recovery_manager):
        """测试所有步骤已完成的情况"""
        state = WorkflowState(
            workflow_id="all-completed",
            step_results={
                "step_0": {"status": "completed"},
                "step_1": {"status": "completed"}
            }
        )

        plan_steps = [
            {"id": "step_0"},
            {"id": "step_1"}
        ]

        index = recovery_manager._get_resume_index(state, plan_steps)
        assert index == -1  # 不需要恢复

    @pytest.mark.asyncio
    async def test_mark_step_completed(self, recovery_manager):
        """测试标记步骤完成"""
        # 创建工作流
        state = WorkflowState(workflow_id="mark-test", status="running")
        recovery_manager.persistence.save(state)

        # 标记步骤完成
        result = await recovery_manager.mark_step_completed(
            "mark-test",
            "step_1",
            {"data": "result"}
        )
        assert result is True

        # 验证
        loaded = recovery_manager.persistence.load("mark-test")
        assert loaded.step_results["step_1"]["status"] == "completed"
        assert "completed_at" in loaded.step_results["step_1"]

    @pytest.mark.asyncio
    async def test_mark_step_failed(self, recovery_manager):
        """测试标记步骤失败"""
        # 创建工作流
        state = WorkflowState(workflow_id="fail-test", status="running")
        recovery_manager.persistence.save(state)

        # 标记步骤失败
        result = await recovery_manager.mark_step_failed(
            "fail-test",
            "step_1",
            "Something went wrong"
        )
        assert result is True

        # 验证
        loaded = recovery_manager.persistence.load("fail-test")
        assert loaded.step_results["step_1"]["status"] == "failed"
        assert loaded.step_results["step_1"]["error"] == "Something went wrong"

    def test_list_recoverable_workflows(self, recovery_manager):
        """测试列出可恢复工作流"""
        # 创建不同状态的工作流
        for status in ["failed", "running", "executing", "completed", "pending"]:
            state = WorkflowState(
                workflow_id=f"wf-{status}",
                status=status
            )
            recovery_manager.persistence.save(state)

        recoverable = recovery_manager.list_recoverable_workflows()
        assert len(recoverable) == 3  # failed, running, executing

        ids = [w["workflow_id"] for w in recoverable]
        assert "wf-failed" in ids
        assert "wf-running" in ids
        assert "wf-executing" in ids

    def test_get_workflow_summary(self, recovery_manager):
        """测试获取工作流摘要"""
        state = WorkflowState(
            workflow_id="summary-test",
            status="running",
            current_step="step_2",
            step_results={
                "step_1": {"status": "completed"},
                "step_2": {"status": "running"}
            },
            plan={
                "plan": {
                    "steps": [
                        {"id": "step_1"},
                        {"id": "step_2"},
                        {"id": "step_3"},
                        {"id": "step_4"}
                    ]
                }
            }
        )
        recovery_manager.persistence.save(state)

        summary = recovery_manager.get_workflow_summary("summary-test")
        assert summary is not None
        assert summary["workflow_id"] == "summary-test"
        assert summary["status"] == "running"
        assert summary["total_steps"] == 2
        assert summary["completed_steps"] == 1
        assert summary["progress_percentage"] == 25  # 1/4

    def test_calculate_progress(self, recovery_manager):
        """测试进度计算"""
        state = WorkflowState(
            workflow_id="progress-test",
            step_results={
                "step_1": {"status": "completed"},
                "step_2": {"status": "completed"},
                "step_3": {"status": "running"}
            },
            plan={
                "plan": {
                    "steps": [
                        {"id": "step_1"},
                        {"id": "step_2"},
                        {"id": "step_3"},
                        {"id": "step_4"}
                    ]
                }
            }
        )

        progress = recovery_manager._calculate_progress(state)
        assert progress == 50  # 2/4

    def test_recovery_info_to_dict(self, recovery_manager):
        """测试恢复信息转换为字典"""
        state = WorkflowState(
            workflow_id="info-test",
            status="failed",
            current_step="step_2",
            step_results={
                "step_1": {"status": "completed"},
                "step_2": {"status": "failed"}
            },
            user_input="测试",
            error="Error occurred"
        )

        info = RecoveryInfo(state)
        data = info.to_dict()

        assert data["workflow_id"] == "info-test"
        assert data["status"] == "failed"
        assert data["current_step"] == "step_2"
        assert data["completed_steps"] == ["step_1"]
        assert data["failed_steps"] == ["step_2"]
        assert data["can_resume"] is True
        assert data["step_count"] == 2


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def temp_storage(self):
        """创建临时存储目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
        reset_persistence()
        reset_recovery_manager()

    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(self, temp_storage):
        """测试完整工作流生命周期"""
        persistence = WorkflowPersistence(temp_storage)
        recovery = RecoveryManager(persistence)

        # 1. 启动工作流
        success, _ = await recovery.start_workflow("lifecycle-test", "测试输入")
        assert success is True

        # 2. 模拟执行步骤
        await recovery.mark_step_completed("lifecycle-test", "intent_classification", {"intent": "test"})
        await recovery.mark_step_completed("lifecycle-test", "planning", {"plan": {"steps": []}})

        # 3. 模拟失败
        await recovery.mark_step_failed("lifecycle-test", "execution", "Execution error")
        persistence.update_workflow_status("lifecycle-test", "failed", "Execution error")

        # 4. 获取恢复信息
        info = recovery.get_recovery_info("lifecycle-test")
        assert info.status == "failed"
        assert "intent_classification" in info.completed_steps
        assert "planning" in info.completed_steps
        assert "execution" in info.failed_steps

        # 5. 列出可恢复工作流
        recoverable = recovery.list_recoverable_workflows()
        assert any(w["workflow_id"] == "lifecycle-test" for w in recoverable)

        # 6. 获取摘要
        summary = recovery.get_workflow_summary("lifecycle-test")
        assert summary["completed_steps"] == 2

    def test_persistence_file_format(self, temp_storage):
        """测试持久化文件格式"""
        persistence = WorkflowPersistence(temp_storage)

        state = WorkflowState(
            workflow_id="format-test",
            status="running",
            user_input="测试",
            step_results={"step_1": {"status": "completed"}}
        )
        persistence.save(state)

        # 直接读取文件验证格式
        file_path = Path(temp_storage) / "format-test.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["workflow_id"] == "format-test"
        assert data["status"] == "running"
        assert "created_at" in data
        assert "updated_at" in data
        assert "step_results" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
