#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRD Generator 测试

测试PRD生成功能的完整流程
"""

import os
import sys
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

from app.services.prd_generator import PRDGeneratorService
from app.agents.templates import get_template_system, IndustryType


async def test_template_detection():
    """测试行业模板检测"""
    print("=" * 60)
    print("测试1: 行业模板检测")
    print("=" * 60)

    template_system = get_template_system()

    test_cases = [
        ("病理切片借阅平台，患者可以在线申请", IndustryType.MEDICAL),
        ("电商订单管理系统", IndustryType.ECOMMERCE),
        ("在线教育平台", IndustryType.EDUCATION),
        ("银行支付系统", IndustryType.FINANCE),
        ("普通工具软件", IndustryType.UNKNOWN),
    ]

    for text, expected in test_cases:
        detected = template_system.detect_industry(text)
        status = "✅" if detected == expected else "❌"
        print(f"{status} 输入: {text[:20]}... -> 检测: {detected.value}, 期望: {expected.value}")

    print()


async def test_template_matching():
    """测试模板匹配"""
    print("=" * 60)
    print("测试2: 模板匹配")
    print("=" * 60)

    template_system = get_template_system()

    # 测试医疗切片模板匹配
    text = "病理切片借阅平台，支持患者在线申请借阅玻片"
    template = template_system.match_template(text)

    if template:
        print(f"✅ 匹配到模板: {template.name}")
        print(f"   行业: {template.industry.value}")
        print(f"   合规要求数量: {len(template.compliance_requirements)}")

        # 显示合规要求
        print("\n   合规要求:")
        for req in template.compliance_requirements[:3]:
            print(f"   - {req.name} ({req.priority})")
    else:
        print("❌ 未匹配到模板")

    print()


async def test_prd_generation_medical():
    """测试医疗PRD生成"""
    print("=" * 60)
    print("测试3: 医疗PRD生成")
    print("=" * 60)

    service = PRDGeneratorService()

    result = await service.generate_prd(
        product_name="病理切片借阅平台",
        description="""
需要一个病理切片借阅平台，主要功能包括：
1. 患者可以在线申请借阅自己的病理切片
2. 支持玻片借阅和数字切片查看
3. 后台管理员审核借阅申请
4. 支持切片归还管理
5. 多院区数据同步

目标用户：患者、医院病理科工作人员、管理员
        """,
        target_users="患者、病理科工作人员、管理员",
        key_features=["在线申请", "审核管理", "切片归还", "数字切片查看"],
        industry="medical",
        save_to_obsidian=False,  # 测试时不保存
        save_local=True
    )

    if result["success"]:
        print(f"✅ PRD生成成功!")
        print(f"   执行时间: {result['execution_time']:.2f}秒")
        print(f"   内容长度: {result['metadata']['content_length']}字符")
        print(f"   行业类型: {result['metadata']['industry']}")
        print(f"   使用模板: {result['metadata']['template_used']}")
        print(f"   本地文件: {result['local_path']}")

        # 显示内容预览
        print("\n   内容预览 (前800字符):")
        print("   " + "-" * 50)
        content = result["content"]
        preview = content[:800] + "..." if len(content) > 800 else content
        for line in preview.split('\n')[:20]:
            print(f"   {line}")
    else:
        print(f"❌ PRD生成失败: {result.get('error')}")

    print()
    return result


async def test_prd_export():
    """测试PRD导出功能"""
    print("=" * 60)
    print("测试4: PRD导出功能")
    print("=" * 60)

    service = PRDGeneratorService()

    # 测试内容
    test_content = """# 测试产品PRD

## 1. 背景与目标

这是一个测试PRD文档。

## 2. 用户故事

- 作为用户，我想要功能A，以便提高效率

## 3. 功能规格

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 功能A | 描述A | P0 |
"""

    # 测试Markdown导出
    result_md = service.export_prd(test_content, format="markdown")
    print(f"✅ Markdown导出: {result_md['filename']}")

    # 测试JSON导出
    result_json = service.export_prd(test_content, format="json")
    print(f"✅ JSON导出: {result_json['filename']}")

    # 测试飞书导出
    result_feishu = service.export_prd(test_content, format="feishu")
    print(f"✅ 飞书格式导出: {result_feishu['filename']}")

    print()


async def test_quick_generate():
    """测试快速生成功能"""
    print("=" * 60)
    print("测试5: 快速生成（自动检测）")
    print("=" * 60)

    service = PRDGeneratorService()

    # 只提供描述，让系统自动检测
    result = await service.generate_prd(
        product_name="病案复印在线申请系统",
        description="患者可以在线申请病案复印，选择自取或快递配送，后台审核后处理",
        save_to_obsidian=False,
        save_local=True
    )

    if result["success"]:
        print(f"✅ 快速生成成功!")
        print(f"   自动检测行业: {result['metadata']['industry']}")
        print(f"   匹配模板: {result['metadata']['template_used'] or '无'}")
        print(f"   本地文件: {result['local_path']}")
    else:
        print(f"❌ 生成失败: {result.get('error')}")

    print()


async def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("#" * 60)
    print("# PRD Generator 功能测试")
    print("#" * 60)
    print("\n")

    try:
        await test_template_detection()
        await test_template_matching()
        await test_prd_generation_medical()
        await test_prd_export()
        await test_quick_generate()

        print("=" * 60)
        print("所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
