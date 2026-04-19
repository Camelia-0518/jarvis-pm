#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能模板系统测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.agents.templates import (
    TemplateSystem,
    IndustryType,
    ComplianceRequirement,
    IndustryTemplate,
    get_template_system
)


class TestIndustryDetection:
    """测试行业检测功能"""

    def test_detect_medical_industry(self):
        """测试医疗行业检测"""
        ts = TemplateSystem()

        # 测试中文关键词
        assert ts.detect_industry("病理切片借阅平台") == IndustryType.MEDICAL
        assert ts.detect_industry("医院管理系统") == IndustryType.MEDICAL
        assert ts.detect_industry("患者预约挂号") == IndustryType.MEDICAL
        assert ts.detect_industry("医生工作站") == IndustryType.MEDICAL

        # 测试英文关键词
        assert ts.detect_industry("medical platform") == IndustryType.MEDICAL
        assert ts.detect_industry("hospital management") == IndustryType.MEDICAL
        assert ts.detect_industry("patient diagnosis") == IndustryType.MEDICAL

    def test_detect_finance_industry(self):
        """测试金融行业检测"""
        ts = TemplateSystem()

        assert ts.detect_industry("银行支付系统") == IndustryType.FINANCE
        assert ts.detect_industry("投资理财平台") == IndustryType.FINANCE
        assert ts.detect_industry("payment gateway") == IndustryType.FINANCE

    def test_detect_education_industry(self):
        """测试教育行业检测"""
        ts = TemplateSystem()

        assert ts.detect_industry("在线教育平台") == IndustryType.EDUCATION
        assert ts.detect_industry("学生管理系统") == IndustryType.EDUCATION
        assert ts.detect_industry("learning management") == IndustryType.EDUCATION

    def test_detect_ecommerce_industry(self):
        """测试电商行业检测"""
        ts = TemplateSystem()

        assert ts.detect_industry("电商平台") == IndustryType.ECOMMERCE
        assert ts.detect_industry("购物车功能") == IndustryType.ECOMMERCE
        assert ts.detect_industry("online shopping") == IndustryType.ECOMMERCE

    def test_detect_unknown_industry(self):
        """测试未知行业检测"""
        ts = TemplateSystem()

        assert ts.detect_industry("通用工具") == IndustryType.UNKNOWN
        assert ts.detect_industry("random text") == IndustryType.UNKNOWN


class TestTemplateMatching:
    """测试模板匹配功能"""

    def test_match_medical_slide_lending_template(self):
        """测试病理切片借阅模板匹配"""
        ts = TemplateSystem()

        template = ts.match_template("病理切片借阅平台")
        assert template is not None
        assert template.id == "medical_slide_lending"
        assert template.industry == IndustryType.MEDICAL

    def test_match_medical_admin_template(self):
        """测试医疗管理后台模板匹配"""
        ts = TemplateSystem()

        template = ts.match_template("医院管理后台系统")
        assert template is not None
        assert template.industry == IndustryType.MEDICAL

    def test_no_match_for_unknown_industry(self):
        """测试未知行业无匹配"""
        ts = TemplateSystem()

        template = ts.match_template("通用工具软件")
        assert template is None

    def test_match_with_explicit_industry(self):
        """测试指定行业的模板匹配"""
        ts = TemplateSystem()

        template = ts.match_template("some text", IndustryType.MEDICAL)
        assert template is not None
        assert template.industry == IndustryType.MEDICAL


class TestComplianceRequirements:
    """测试合规要求功能"""

    def test_medical_slide_lending_compliance(self):
        """测试病理切片借阅合规要求"""
        ts = TemplateSystem()
        template = ts.get_template("medical_slide_lending")

        assert template is not None
        assert len(template.compliance_requirements) == 5

        # 检查关键合规项
        req_names = [r.name for r in template.compliance_requirements]
        assert "等保三级合规" in req_names
        assert "患者隐私保护" in req_names
        assert "医疗数据安全" in req_names

    def test_medical_admin_compliance(self):
        """测试医疗管理后台合规要求"""
        ts = TemplateSystem()
        template = ts.get_template("medical_admin_system")

        assert template is not None
        assert len(template.compliance_requirements) == 4

        req_names = [r.name for r in template.compliance_requirements]
        assert "权限管理" in req_names
        assert "操作审计" in req_names

    def test_compliance_checklist(self):
        """测试合规检查清单"""
        ts = TemplateSystem()
        template = ts.get_template("medical_slide_lending")

        checklist = ts.get_compliance_checklist(template)
        assert len(checklist) == 5

        # 检查清单结构
        first_item = checklist[0]
        assert "name" in first_item
        assert "description" in first_item
        assert "category" in first_item
        assert "priority" in first_item
        assert "checklist" in first_item

    def test_compliance_filter_by_category(self):
        """测试按类别筛选合规要求"""
        ts = TemplateSystem()
        template = ts.get_template("medical_slide_lending")

        security_reqs = ts.get_compliance_checklist(template, category="security")
        assert len(security_reqs) >= 2  # 至少2个安全类要求


class TestTemplateApplication:
    """测试模板应用功能"""

    def test_apply_template_to_plan(self):
        """测试将模板应用到计划"""
        ts = TemplateSystem()
        template = ts.get_template("medical_slide_lending")

        original_plan = {
            "workflow_name": "测试流程",
            "steps": [
                {"id": "step_1", "agent_name": "test_agent"}
            ]
        }

        enhanced_plan = ts.apply_template_to_plan(template, original_plan)

        # 验证增强内容
        assert "compliance_requirements" in enhanced_plan
        assert "mandatory_checks" in enhanced_plan
        assert "workflow_enhancements" in enhanced_plan
        assert "agent_prompts" in enhanced_plan
        assert "template_info" in enhanced_plan

        # 验证原始内容保留
        assert enhanced_plan["workflow_name"] == "测试流程"
        assert len(enhanced_plan["steps"]) == 1

    def test_enhance_agent_prompt(self):
        """测试增强Agent提示词"""
        ts = TemplateSystem()
        template = ts.get_template("medical_slide_lending")

        base_prompt = "你是一个PRD生成专家。"
        enhanced = ts.enhance_agent_prompt(template, "prd_generator", base_prompt)

        # 验证提示词增强
        assert "行业特定要求" in enhanced
        assert "医疗行业PRD专家" in enhanced
        assert base_prompt in enhanced

    def test_no_enhancement_for_unknown_agent(self):
        """测试未知Agent不增强"""
        ts = TemplateSystem()
        template = ts.get_template("medical_slide_lending")

        base_prompt = "基础提示词"
        enhanced = ts.enhance_agent_prompt(template, "unknown_agent", base_prompt)

        assert enhanced == base_prompt


class TestTemplateManagement:
    """测试模板管理功能"""

    def test_list_templates(self):
        """测试列出所有模板"""
        ts = TemplateSystem()

        templates = ts.list_templates()
        assert len(templates) == 2  # 内置2个模板

        # 检查模板结构
        first = templates[0]
        assert "id" in first
        assert "name" in first
        assert "industry" in first
        assert "description" in first

    def test_list_templates_by_industry(self):
        """测试按行业筛选模板"""
        ts = TemplateSystem()

        medical_templates = ts.list_templates(industry=IndustryType.MEDICAL)
        assert len(medical_templates) == 2

        finance_templates = ts.list_templates(industry=IndustryType.FINANCE)
        assert len(finance_templates) == 0

    def test_get_template(self):
        """测试获取指定模板"""
        ts = TemplateSystem()

        template = ts.get_template("medical_slide_lending")
        assert template is not None
        assert template.id == "medical_slide_lending"

        # 测试获取不存在的模板
        assert ts.get_template("non_existent") is None

    def test_register_custom_template(self):
        """测试注册自定义模板"""
        ts = TemplateSystem()

        custom_template = IndustryTemplate(
            id="custom_template",
            name="自定义模板",
            industry=IndustryType.SAAS,
            description="测试自定义模板",
            keywords=["test"],
            compliance_requirements=[],
            workflow_enhancements={},
            agent_prompts={},
            mandatory_checks=[]
        )

        ts.register_custom_template(custom_template)

        # 验证注册成功
        retrieved = ts.get_template("custom_template")
        assert retrieved is not None
        assert retrieved.name == "自定义模板"

        # 验证列表包含自定义模板
        templates = ts.list_templates()
        assert len(templates) == 3  # 2个内置 + 1个自定义


class TestGlobalInstance:
    """测试全局实例"""

    def test_get_template_system_singleton(self):
        """测试全局单例"""
        ts1 = get_template_system()
        ts2 = get_template_system()

        assert ts1 is ts2


class TestMedicalSpecificFeatures:
    """测试医疗行业特定功能"""

    def test_medical_slide_lending_keywords(self):
        """测试病理切片借阅关键词"""
        ts = TemplateSystem()
        template = ts.get_template("medical_slide_lending")

        expected_keywords = ["切片", "病理", "玻片", "借阅", "归还", "数字切片"]
        for kw in expected_keywords:
            assert kw in template.keywords

    def test_medical_slide_lending_mandatory_checks(self):
        """测试病理切片借阅强制检查项"""
        ts = TemplateSystem()
        template = ts.get_template("medical_slide_lending")

        assert len(template.mandatory_checks) == 5
        assert "等保三级合规检查" in template.mandatory_checks
        assert "患者隐私保护检查" in template.mandatory_checks

    def test_medical_slide_lending_agent_prompts(self):
        """测试病理切片借阅Agent提示词"""
        ts = TemplateSystem()
        template = ts.get_template("medical_slide_lending")

        assert "prd_generator" in template.agent_prompts
        assert "compliance_checker" in template.agent_prompts

        # 验证PRD生成器提示词内容
        prd_prompt = template.agent_prompts["prd_generator"]
        assert "等保三级合规" in prd_prompt
        assert "患者隐私保护" in prd_prompt
        assert "病案复印平台经验" in prd_prompt

    def test_medical_admin_workflow_enhancements(self):
        """测试医疗管理后台工作流增强"""
        ts = TemplateSystem()
        template = ts.get_template("medical_admin_system")

        enhancements = template.workflow_enhancements
        assert "mandatory_agents" in enhancements
        assert "compliance_checker" in enhancements["mandatory_agents"]
        assert "additional_context" in enhancements


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
