#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRD 生成命令行工具

使用方法:
    python scripts/generate_prd.py "产品名称" "需求描述"
    python scripts/generate_prd.py --interactive

示例:
    python scripts/generate_prd.py "病理切片借阅平台" "需要一个病理切片借阅功能，患者可以在线申请借阅自己的病理切片"
"""

import os
import sys
import argparse
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

from app.services.prd_generator import prd_generator_service


def print_header():
    """打印标题"""
    print("=" * 60)
    print("  Jarvis PM - PRD 生成工具")
    print("=" * 60)
    print()


def print_result(result: dict):
    """打印生成结果"""
    print()
    print("-" * 60)
    print("生成结果:")
    print("-" * 60)

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
    print()

    if result.get("obsidian_path"):
        print(f"📁 Obsidian: {result['obsidian_path']}")

    if result.get("local_path"):
        print(f"💾 本地文件: {result['local_path']}")

    print()
    print("=" * 60)
    print("PRD 内容预览 (前500字符):")
    print("=" * 60)
    content = result.get("content", "")
    print(content[:500] + "..." if len(content) > 500 else content)


async def interactive_mode():
    """交互模式"""
    print_header()
    print("交互模式 - 请回答以下问题:\n")

    product_name = input("1. 产品名称: ").strip()
    if not product_name:
        print("错误: 产品名称不能为空")
        return

    print("\n2. 需求描述 (支持多行，输入空行结束):")
    description_lines = []
    while True:
        line = input()
        if not line and description_lines:
            break
        description_lines.append(line)
    description = "\n".join(description_lines)

    if not description:
        print("错误: 需求描述不能为空")
        return

    target_users = input("\n3. 目标用户 (可选，直接回车跳过): ").strip() or None

    print("\n4. 核心功能 (可选，输入空行结束):")
    key_features = []
    while True:
        feature = input("   - ").strip()
        if not feature:
            break
        key_features.append(feature)

    industry = input("\n5. 行业类型 (medical/general，直接回车自动检测): ").strip() or None

    print("\n" + "=" * 60)
    print("开始生成PRD...")
    print("=" * 60)

    result = await prd_generator_service.generate_prd(
        product_name=product_name,
        description=description,
        target_users=target_users,
        key_features=key_features if key_features else None,
        industry=industry,
        save_to_obsidian=True,
        save_local=True
    )

    print_result(result)


async def quick_mode(product_name: str, description: str, **kwargs):
    """快速模式"""
    print_header()
    print(f"产品名称: {product_name}")
    print(f"需求描述: {description[:100]}...")
    print()
    print("开始生成PRD...")
    print()

    result = await prd_generator_service.generate_prd(
        product_name=product_name,
        description=description,
        save_to_obsidian=True,
        save_local=True,
        **kwargs
    )

    print_result(result)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Jarvis PM - PRD 生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互模式
  python scripts/generate_prd.py --interactive

  # 快速生成
  python scripts/generate_prd.py "病理切片借阅平台" "需要一个病理切片借阅功能..."

  # 指定行业
  python scripts/generate_prd.py "病理切片借阅平台" "需求描述..." --industry medical
        """
    )

    parser.add_argument("product_name", nargs="?", help="产品名称")
    parser.add_argument("description", nargs="?", help="需求描述")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    parser.add_argument("--industry", help="行业类型 (medical/general)")
    parser.add_argument("--template", help="模板ID")
    parser.add_argument("--no-obsidian", action="store_true", help="不保存到Obsidian")
    parser.add_argument("--no-local", action="store_true", help="不保存到本地")

    args = parser.parse_args()

    if args.interactive:
        asyncio.run(interactive_mode())
    elif args.product_name and args.description:
        asyncio.run(quick_mode(
            product_name=args.product_name,
            description=args.description,
            industry=args.industry,
            template_id=args.template,
            save_to_obsidian=not args.no_obsidian,
            save_local=not args.no_local
        ))
    else:
        parser.print_help()
        print("\n错误: 请提供产品名称和需求描述，或使用 --interactive 进入交互模式")
        sys.exit(1)


if __name__ == "__main__":
    main()
