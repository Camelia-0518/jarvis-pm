#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查点机制测试"""

import pytest
import asyncio
from app.agents.checkpoints import (
    CheckpointController, CheckpointWrapper,
    CheckpointAction, Checkpoint
)


@pytest.mark.asyncio
async def test_checkpoint_lifecycle():
    """测试检查点完整生命周期"""
    controller = CheckpointController()

    # 创建检查点
    checkpoint = controller.create_checkpoint(
        workflow_id="test-workflow",
        checkpoint_id="after_intent",
        step_id="intent",
        content={"task_type": "prd_generation", "confidence": 0.9}
    )

    assert checkpoint.status == "pending"
    assert checkpoint.workflow_id == "test-workflow"

    # 模拟用户继续
    async def user_resume():
        await asyncio.sleep(0.1)
        await controller.resume("test-workflow", checkpoint.id)

    # 启动用户模拟和等待
    await asyncio.gather(
        user_resume(),
        controller.wait_for_resolution(checkpoint.id)
    )

    assert checkpoint.status == "resolved"
    assert checkpoint.action == CheckpointAction.RESUME


@pytest.mark.asyncio
async def test_checkpoint_modify():
    """测试检查点修改功能"""
    controller = CheckpointController()

    checkpoint = controller.create_checkpoint(
        workflow_id="test-workflow",
        checkpoint_id="after_intent",
        step_id="intent",
        content={"task_type": "prd_generation", "confidence": 0.9}
    )

    # 模拟用户修改
    async def user_modify():
        await asyncio.sleep(0.1)
        await controller.modify_and_resume(
            "test-workflow",
            checkpoint.id,
            {"task_type": "requirement_analysis"}
        )

    result = await asyncio.gather(
        user_modify(),
        controller.wait_for_resolution(checkpoint.id)
    )

    resolution = result[1]
    assert resolution["action"] == "modify"
    assert resolution["modifications"]["task_type"] == "requirement_analysis"


@pytest.mark.asyncio
async def test_checkpoint_skip():
    """测试检查点跳过功能"""
    controller = CheckpointController()

    checkpoint = controller.create_checkpoint(
        workflow_id="test-workflow",
        checkpoint_id="after_competitor",
        step_id="competitor",
        content={"competitors": ["A", "B"]}
    )

    async def user_skip():
        await asyncio.sleep(0.1)
        await controller.skip("test-workflow", checkpoint.id)

    await asyncio.gather(
        user_skip(),
        controller.wait_for_resolution(checkpoint.id)
    )

    assert checkpoint.status == "skipped"
    assert checkpoint.action == CheckpointAction.SKIP


@pytest.mark.asyncio
async def test_checkpoint_retry():
    """测试检查点重试功能"""
    controller = CheckpointController()

    checkpoint = controller.create_checkpoint(
        workflow_id="test-workflow",
        checkpoint_id="after_requirement",
        step_id="requirement",
        content={"features": []}
    )

    async def user_retry():
        await asyncio.sleep(0.1)
        await controller.retry("test-workflow", checkpoint.id)

    result = await asyncio.gather(
        user_retry(),
        controller.wait_for_resolution(checkpoint.id)
    )

    resolution = result[1]
    assert resolution["action"] == "retry"


@pytest.mark.asyncio
async def test_checkpoint_timeout():
    """测试检查点超时自动继续"""
    controller = CheckpointController()

    checkpoint = controller.create_checkpoint(
        workflow_id="test-workflow",
        checkpoint_id="after_intent",
        step_id="intent",
        content={"task_type": "prd_generation"}
    )

    # 等待超时（设置较短的超时时间）
    result = await controller.wait_for_resolution(checkpoint.id, timeout=0.2)

    assert result["action"] == "resume"
    assert checkpoint.status == "resolved"


def test_checkpoint_config():
    """测试检查点配置"""
    controller = CheckpointController()

    # 测试启用的检查点
    assert controller.should_pause_at("after_intent") == True
    assert controller.should_pause_at("after_plan") == True

    # 测试禁用的检查点
    assert controller.should_pause_at("after_competitor") == False

    # 测试未知检查点
    assert controller.should_pause_at("unknown") == False


def test_get_workflow_checkpoints():
    """测试获取工作流检查点列表"""
    controller = CheckpointController()

    # 创建多个检查点
    cp1 = controller.create_checkpoint(
        workflow_id="wf-1",
        checkpoint_id="after_intent",
        step_id="intent",
        content={}
    )
    cp2 = controller.create_checkpoint(
        workflow_id="wf-1",
        checkpoint_id="after_plan",
        step_id="plan",
        content={}
    )
    controller.create_checkpoint(
        workflow_id="wf-2",
        checkpoint_id="after_intent",
        step_id="intent",
        content={}
    )

    wf1_checkpoints = controller.get_workflow_checkpoints("wf-1")
    assert len(wf1_checkpoints) == 2


def test_to_dict():
    """测试检查点转换为字典"""
    controller = CheckpointController()

    checkpoint = controller.create_checkpoint(
        workflow_id="test-workflow",
        checkpoint_id="after_intent",
        step_id="intent",
        content={"task_type": "prd_generation"}
    )

    data = controller.to_dict(checkpoint)

    assert "id" in data
    assert "title" in data
    assert "content" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_checkpoint_wrapper_resume():
    """测试检查点包装器 - 继续操作"""
    from unittest.mock import AsyncMock, MagicMock

    controller = CheckpointController()
    mock_emitter = MagicMock()
    mock_emitter.emit_checkpoint = AsyncMock()

    wrapper = CheckpointWrapper("test-workflow", mock_emitter)
    wrapper.controller = controller

    # 禁用检查点，直接继续
    async def test_check():
        result = await wrapper.check(
            checkpoint_id="after_competitor",  # 默认禁用
            step_id="competitor",
            content={"competitors": []}
        )
        assert result["action"] == "resume"

    await test_check()


@pytest.mark.asyncio
async def test_checkpoint_wrapper_enabled():
    """测试检查点包装器 - 启用的检查点"""
    controller = CheckpointController()
    wrapper = CheckpointWrapper("test-workflow", None)
    wrapper.controller = controller

    # 启用检查点
    controller.CHECKPOINTS_CONFIG["after_intent"]["enabled"] = True

    checkpoint = controller.create_checkpoint(
        workflow_id="test-workflow",
        checkpoint_id="after_intent",
        step_id="intent",
        content={"task_type": "prd"}
    )

    # 模拟用户继续
    async def user_resume():
        await asyncio.sleep(0.1)
        await controller.resume("test-workflow", checkpoint.id)

    result = await asyncio.gather(
        user_resume(),
        wrapper.check("after_intent", "intent", {"task_type": "prd"})
    )

    assert result[1]["action"] == "resume"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
