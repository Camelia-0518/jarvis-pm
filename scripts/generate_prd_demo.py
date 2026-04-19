#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRD 生成演示脚本

演示 PRD 生成功能，无需配置 API Key
"""

import os
import sys
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

from app.services.prd_generator_demo import prd_generator_demo_service


def print_header():
    """打印标题"""
    print("=" * 70)
    print("  Jarvis PM - PRD 生成演示")
    print("=" * 70)
    print()
    print("  本演示展示 PRD 生成功能的标准输出格式")
    print("  实际使用时请配置 KIMI_API_KEY 以生成真实内容")
    print()


def print_result(result: dict):
    """打印生成结果"""
    print()
    print("-" * 70)
    print("生成结果:")
    print("-" * 70)

    if not result.get("success"):
        print(f"❌ 生成失败: {result.get('error', '未知错误')}")
        return

    metadata = result.get("metadata", {})
    print(f"✅ 生成成功!")
    print(f"   产品名称: {metadata.get('product_name', 'N/A')}")
    print(f"   行业类型: {metadata.get('industry', 'N/A')}")
    print(f"   使用模板: {metadata.get('template_used', '默认')}")
    print(f"   内容长度: {metadata.get('content_length', 0)} 字符")
    print(f"   执行时间: {metadata.get('execution_time', 0):.2f} 秒")
    print(f"   生成模式: {metadata.get('mode', 'unknown')}")
    print()

    if result.get("obsidian_path"):
        print(f"📁 Obsidian: {result['obsidian_path']}")

    if result.get("local_path"):
        print(f"💾 本地文件: {result['local_path']}")

    if result.get("note"):
        print()
        print(f"💡 {result['note']}")

    print()
    print("=" * 70)
    print("PRD 内容预览 (前1000字符):")
    print("=" * 70)
    content = result.get("content", "")
    preview = content[:1000] + "..." if len(content) > 1000 else content
    print(preview)


async def demo_medical_slide_lending():
    """演示：病理切片借阅平台"""
    print("\n" + "=" * 70)
    print("演示1: 病理切片借阅平台 (医疗行业)")
    print("=" * 70)

    result = await prd_generator_demo_service.generate_prd(
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
        key_features=["在线申请", "审核管理", "切片归还", "数字切片查看", "多院区同步"],
        industry="medical",
        save_to_obsidian=True,
        save_local=True
    )

    print_result(result)
    return result


async def demo_medical_record_copy():
    """演示：病案复印系统"""
    print("\n" + "=" * 70)
    print("演示2: 病案复印在线申请系统 (医疗行业)")
    print("=" * 70)

    result = await prd_generator_demo_service.generate_prd(
        product_name="病案复印在线申请系统",
        description="患者可以在线申请病案复印，选择自取或快递配送，后台审核后处理。支持多院区病案查询和复印申请。",
        save_to_obsidian=True,
        save_local=True
    )

    print_result(result)
    return result


async def demo_general_product():
    """演示：通用产品"""
    print("\n" + "=" * 70)
    print("演示3: 通用产品 (非医疗行业)")
    print("=" * 70)

    result = await prd_generator_demo_service.generate_prd(
        product_name="智能任务管理工具",
        description="一款面向个人和小团队的任务管理工具，支持任务创建、分配、跟踪和统计报表功能。",
        target_users="个人用户、小团队",
        key_features=["任务管理", "团队协作", "统计报表", "提醒通知"],
        save_to_obsidian=True,
        save_local=True
    )

    print_result(result)
    return result


async def demo_export():
    """演示：导出功能"""
    print("\n" + "=" * 70)
    print("演示4: PRD 导出功能")
    print("=" * 70)

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

    formats = ["markdown", "json", "feishu"]

    for fmt in formats:
        result = prd_generator_demo_service.export_prd(test_content, format=fmt)
        if result["success"]:
            print(f"✅ {fmt.upper()} 导出: {result['filename']}")
        else:
            print(f"❌ {fmt.upper()} 导出失败: {result.get('error')}")


async def main():
    """主函数"""
    print_header()

    try:
        # 运行演示
        await demo_medical_slide_lending()
        await demo_medical_record_copy()
        await demo_general_product()
        await demo_export()

        print("\n" + "=" * 70)
        print("所有演示完成!")
        print("=" * 70)
        print()
        print("使用说明:")
        print("1. 配置 KIMI_API_KEY 环境变量以启用真实 AI 生成")
        print("2. 使用 scripts/generate_prd.py 进行真实 PRD 生成")
        print("3. 查看 PRD_GENERATOR_README.md 获取完整文档")
        print()

    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
