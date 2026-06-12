#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
干系人协调 Agent

生成 RACI 矩阵、干系人沟通计划、项目状态报告模板
适配医疗信息化项目多角色协同场景（医务科/信息科/临床科室/院领导/供应商）
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..base import BaseAgent, AgentResult, AgentState


class StakeholderCoordinatorAgent(BaseAgent):
    """干系人分析、RACI矩阵、沟通计划生成"""

    name = "stakeholder_coordinator"
    description = "Generate RACI matrices, stakeholder communication plans, and status report templates"
    version = "1.0.0"
    capabilities = [
        "stakeholder_analysis",
        "raci_matrix",
        "communication_planning",
        "status_reporting",
    ]

    # 医疗项目默认干系人角色定义
    MEDICAL_STAKEHOLDERS = [
        {"id": "SH-01", "role": "院领导/分管副院长", "dept": "院办",
         "concern": "项目ROI、医院评级、合规达标", "influence": "高", "interest": "高",
         "comm_freq": "月度汇报", "comm_channel": "书面报告+当面汇报"},
        {"id": "SH-02", "role": "医务科主任", "dept": "医务科",
         "concern": "诊疗流程合规、医师工作效率", "influence": "高", "interest": "高",
         "comm_freq": "双周会", "comm_channel": "会议+邮件"},
        {"id": "SH-03", "role": "信息科主任", "dept": "信息科",
         "concern": "系统稳定性、运维成本、数据安全", "influence": "高", "interest": "高",
         "comm_freq": "周会", "comm_channel": "会议+即时通讯"},
        {"id": "SH-04", "role": "临床科室主任", "dept": "各临床科室",
         "concern": "临床工作流适配、数据准确性", "influence": "中", "interest": "中",
         "comm_freq": "双周会", "comm_channel": "科室走访+邮件"},
        {"id": "SH-05", "role": "护士长", "dept": "护理部",
         "concern": "护理操作效率、医嘱执行准确", "influence": "中", "interest": "中",
         "comm_freq": "双周会", "comm_channel": "走访+培训反馈"},
        {"id": "SH-06", "role": "财务科负责人", "dept": "财务科",
         "concern": "收费准确率、医保结算、对账", "influence": "高", "interest": "中",
         "comm_freq": "月度会", "comm_channel": "会议+数据报告"},
        {"id": "SH-07", "role": "药学部主任", "dept": "药学部",
         "concern": "药品管理、处方审核流程", "influence": "中", "interest": "中",
         "comm_freq": "月度会", "comm_channel": "会议"},
        {"id": "SH-08", "role": "医保办负责人", "dept": "医保办",
         "concern": "医保接口合规、费用审核", "influence": "高", "interest": "中",
         "comm_freq": "关键节点", "comm_channel": "专题会议"},
        {"id": "SH-09", "role": "项目经理(乙方)", "dept": "交付团队",
         "concern": "按时按质交付、成本控制、回款", "influence": "高", "interest": "高",
         "comm_freq": "日报", "comm_channel": "项目管理工具+即时通讯"},
        {"id": "SH-10", "role": "技术负责人(乙方)", "dept": "研发团队",
         "concern": "技术方案可行性、架构扩展性", "influence": "高", "interest": "高",
         "comm_freq": "周会", "comm_channel": "技术评审+即时通讯"},
        {"id": "SH-11", "role": "第三方接口供应商", "dept": "外部",
         "concern": "接口规范、联调进度", "influence": "中", "interest": "低",
         "comm_freq": "按需", "comm_channel": "邮件+联调会议"},
        {"id": "SH-12", "role": "等保测评机构", "dept": "外部",
         "concern": "安全合规标准达标", "influence": "中", "interest": "低",
         "comm_freq": "关键节点", "comm_channel": "正式函件+测评会议"},
    ]

    SYSTEM_PROMPT = """你是医疗信息化项目干系人管理专家，精通医院组织架构和多方协调。

职责：
1. 分析项目干系人及其关注点
2. 生成 RACI 责任分配矩阵
3. 制定分层次沟通计划（日报/周报/月报/里程碑汇报）
4. 输出标准化的项目状态报告模板

输出格式：严格JSON。"""

    async def _do_execute(self, input_data: Dict[str, Any]) -> AgentResult:
        product_name = input_data.get("product_name", "未命名项目")
        description = input_data.get("description", "")
        prd_content = input_data.get("prd_content", "")
        industry = input_data.get("industry", "medical")
        custom_stakeholders = input_data.get("stakeholders", [])

        step1 = self._create_step("analyze_stakeholders", "分析干系人")
        stakeholders = self._analyze_stakeholders(product_name, description, custom_stakeholders, industry)
        self._complete_step(step1, f"识别{len(stakeholders)}个干系人")

        step2 = self._create_step("build_raci", "构建RACI矩阵")
        raci = self._build_raci_matrix(product_name, description, stakeholders, prd_content)
        self._complete_step(step2, f"RACI {len(raci['activities'])}项活动 x {len(raci['roles'])}个角色")

        step3 = self._create_step("comm_plan", "制定沟通计划")
        comm_plan = self._build_comm_plan(stakeholders, product_name)
        self._complete_step(step3, f"沟通计划 {len(comm_plan['meetings'])}类会议")

        step4 = self._create_step("status_template", "生成状态报告模板")
        status_template = self._generate_status_template(product_name, stakeholders)
        self._complete_step(step4, f"模板{len(status_template['sections'])}个部分")


        return AgentResult(
            success=True,
            output=self._to_markdown(product_name, stakeholders, raci, comm_plan, status_template),
            data={
                "product_name": product_name,
                "stakeholders": stakeholders,
                "raci": raci,
                "communication_plan": comm_plan,
                "status_template": status_template,
                "industry": industry,
            },
            execution_time=self.elapsed_seconds,
            metadata={
                "agent_name": self.name,
                "version": self.version,
                "steps_completed": len(self.steps),
            }
        )

    def _analyze_stakeholders(self, product_name: str, description: str,
                              custom: List[Dict], industry: str) -> List[Dict]:
        stakeholders = list(self.MEDICAL_STAKEHOLDERS)

        if custom:
            for cs in custom:
                stakeholders.append({
                    "id": f"SH-{len(stakeholders)+1:02d}",
                    "role": cs.get("role", ""),
                    "dept": cs.get("dept", ""),
                    "concern": cs.get("concern", ""),
                    "influence": cs.get("influence", "中"),
                    "interest": cs.get("interest", "中"),
                    "comm_freq": cs.get("comm_freq", "按需"),
                    "comm_channel": cs.get("comm_channel", "会议"),
                })

        if industry != "medical":
            stakeholders = [s for s in stakeholders if s["dept"] != "外部" or s["id"] in ("SH-09", "SH-10")]

        return stakeholders

    def _build_raci_matrix(self, product_name: str, description: str,
                           stakeholders: List[Dict], prd_content: str) -> Dict[str, Any]:
        activities = [
            {"id": "A01", "name": "项目章程审批", "phase": "启动"},
            {"id": "A02", "name": "需求调研与确认", "phase": "需求"},
            {"id": "A03", "name": "需求规格说明书签字", "phase": "需求"},
            {"id": "A04", "name": "系统架构设计评审", "phase": "设计"},
            {"id": "A05", "name": "数据库设计评审", "phase": "设计"},
            {"id": "A06", "name": "安全方案审批", "phase": "设计"},
            {"id": "A07", "name": "核心功能开发", "phase": "开发"},
            {"id": "A08", "name": "接口联调", "phase": "开发"},
            {"id": "A09", "name": "功能测试(SIT)", "phase": "测试"},
            {"id": "A10", "name": "用户验收测试(UAT)", "phase": "测试"},
            {"id": "A11", "name": "等保测评", "phase": "测试"},
            {"id": "A12", "name": "互联互通测评", "phase": "测试"},
            {"id": "A13", "name": "数据迁移", "phase": "部署"},
            {"id": "A14", "name": "生产环境部署", "phase": "部署"},
            {"id": "A15", "name": "用户培训", "phase": "培训"},
            {"id": "A16", "name": "上线切换", "phase": "部署"},
            {"id": "A17", "name": "项目验收", "phase": "验收"},
            {"id": "A18", "name": "运维交接", "phase": "运维"},
        ]

        role_ids = [s["id"] for s in stakeholders]
        role_names = {s["id"]: s["role"] for s in stakeholders}

        assignments = {}
        for act in activities:
            assignments[act["id"]] = {}
            for sid in role_ids:
                assignments[act["id"]][sid] = ""

        raci_map = {
            "A01": {"SH-01": "A", "SH-02": "C", "SH-03": "C", "SH-09": "R"},
            "A02": {"SH-02": "R", "SH-03": "C", "SH-04": "C", "SH-09": "A"},
            "A03": {"SH-01": "A", "SH-02": "R", "SH-03": "C", "SH-09": "R"},
            "A04": {"SH-03": "A", "SH-09": "R", "SH-10": "R"},
            "A05": {"SH-03": "A", "SH-09": "R", "SH-10": "R"},
            "A06": {"SH-01": "A", "SH-03": "R", "SH-12": "C"},
            "A07": {"SH-09": "A", "SH-10": "R"},
            "A08": {"SH-03": "A", "SH-09": "R", "SH-10": "R", "SH-11": "C"},
            "A09": {"SH-03": "C", "SH-09": "A", "SH-10": "R"},
            "A10": {"SH-02": "A", "SH-03": "C", "SH-04": "R", "SH-09": "R"},
            "A11": {"SH-03": "C", "SH-09": "A", "SH-10": "R", "SH-12": "C"},
            "A12": {"SH-03": "C", "SH-09": "A", "SH-10": "R"},
            "A13": {"SH-03": "A", "SH-09": "R", "SH-10": "R"},
            "A14": {"SH-03": "A", "SH-09": "R", "SH-10": "R"},
            "A15": {"SH-02": "R", "SH-03": "C", "SH-04": "C", "SH-05": "C", "SH-09": "A"},
            "A16": {"SH-01": "I", "SH-02": "I", "SH-03": "A", "SH-09": "R", "SH-10": "R"},
            "A17": {"SH-01": "A", "SH-02": "C", "SH-03": "C", "SH-09": "R"},
            "A18": {"SH-03": "A", "SH-09": "R", "SH-10": "R"},
        }

        for act_id, mapping in raci_map.items():
            for sid, value in mapping.items():
                if sid in assignments.get(act_id, {}):
                    assignments[act_id][sid] = value

        return {
            "activities": [{"id": a["id"], "name": a["name"], "phase": a["phase"]} for a in activities],
            "roles": [{"id": s["id"], "name": s["role"], "dept": s["dept"]} for s in stakeholders],
            "assignments": assignments,
            "total_activities": len(activities),
            "total_roles": len(role_ids),
        }

    def _build_comm_plan(self, stakeholders: List[Dict], product_name: str) -> Dict[str, Any]:
        meetings = [
            {
                "id": "MTG-01", "name": "每日站会",
                "participants": ["项目经理(乙方)", "技术负责人(乙方)", "开发团队"],
                "frequency": "每日 09:30",
                "duration": "15分钟",
                "format": "站立会议/即时通讯",
                "output": "当日任务看板更新",
                "agenda": ["昨日完成", "今日计划", "阻塞问题"],
            },
            {
                "id": "MTG-02", "name": "项目周会",
                "participants": ["项目经理(乙方)", "技术负责人(乙方)", "信息科主任"],
                "frequency": "每周五 14:00",
                "duration": "60分钟",
                "format": "会议+屏幕共享",
                "output": "周报、风险更新、下周计划",
                "agenda": ["本周进度回顾", "风险与问题讨论", "下周计划确认", "资源协调"],
            },
            {
                "id": "MTG-03", "name": "双周需求评审会",
                "participants": ["医务科主任", "临床科室主任", "护士长", "项目经理(乙方)", "产品经理"],
                "frequency": "每两周周三 14:00",
                "duration": "90分钟",
                "format": "现场会议",
                "output": "需求确认记录、变更评估",
                "agenda": ["需求进度更新", "需求变更讨论", "UAT反馈讨论"],
            },
            {
                "id": "MTG-04", "name": "月度项目汇报",
                "participants": ["院领导/分管副院长", "医务科主任", "信息科主任", "项目经理(乙方)"],
                "frequency": "每月最后一个工作日",
                "duration": "30分钟",
                "format": "正式汇报+书面报告",
                "output": "月度项目报告、决策事项清单",
                "agenda": ["月度成果", "风险与问题", "下月计划", "需要决策事项"],
            },
            {
                "id": "MTG-05", "name": "里程碑评审会",
                "participants": ["院领导/分管副院长", "信息科主任", "项目经理(乙方)", "技术负责人(乙方)"],
                "frequency": "每个里程碑节点",
                "duration": "90分钟",
                "format": "正式评审会议",
                "output": "里程碑签收单、下一阶段计划",
                "agenda": ["里程碑成果展示", "遗留问题清单", "下一阶段计划审批"],
            },
            {
                "id": "MTG-06", "name": "接口联调协调会",
                "participants": ["信息科主任", "技术负责人(乙方)", "第三方接口供应商"],
                "frequency": "联调期间每周",
                "duration": "45分钟",
                "format": "视频会议+联调日志",
                "output": "联调进度报告、接口问题清单",
                "agenda": ["联调进度", "接口问题讨论", "责任方确认", "解决时间承诺"],
            },
        ]

        reports = [
            {"name": "日报", "audience": "项目经理", "content": "今日完成/明日计划/阻塞问题/风险预警",
             "template": "每日18:00前通过项目管理工具自动汇总"},
            {"name": "周报", "audience": "信息科+乙方管理层", "content": "进度摘要/本周完成/下周计划/风险更新/资源需求",
             "template": "每周五17:00前邮件发出"},
            {"name": "月报", "audience": "院领导+乙方高层", "content": "月度成果/里程碑进度/预算执行/重点风险/下月计划",
             "template": "每月末提交正式PDF报告"},
            {"name": "风险专报", "audience": "项目总监", "content": "新增风险/升级风险/应对进展/趋势分析",
             "template": "极高风险触发时即时发送"},
        ]

        return {
            "meetings": meetings,
            "reports": reports,
            "escalation_path": [
                "L1: 项目经理 — 日常协调决策",
                "L2: 项目总监 — 跨部门协调、资源冲突",
                "L3: 项目指导委员会 — 重大变更、预算超支、合同争议",
            ],
        }

    def _generate_status_template(self, product_name: str, stakeholders: List[Dict]) -> Dict[str, Any]:
        today = datetime.now().strftime("%Y-%m-%d")
        return {
            "sections": [
                {"name": "项目概览", "fields": ["项目名称", "报告周期", "项目经理", "整体状态(绿/黄/红)", "本期里程碑"]},
                {"name": "进度摘要", "fields": ["计划完成%", "实际完成%", "偏差说明", "关键成就", "延期项及原因"]},
                {"name": "风险管理", "fields": ["新增风险数", "关闭风险数", "TOP3 风险及应对", "风险趋势(改善/持平/恶化)"]},
                {"name": "资源与成本", "fields": ["实际人天", "计划人天", "预算执行率", "资源缺口/冲突"]},
                {"name": "下期计划", "fields": ["下期目标", "关键任务", "里程碑预告", "需要协调事项"]},
                {"name": "决策事项", "fields": ["需要领导决策的事项", "方案选项", "建议方案", "决策截止时间"]},
            ],
            "generated_at": today,
            "product_name": product_name,
        }

    def _to_markdown(self, product_name: str, stakeholders: List[Dict], raci: Dict[str, Any],
                     comm_plan: Dict[str, Any], status_template: Dict[str, Any]) -> str:
        md = [
            f"# {product_name} 干系人管理与沟通计划",
            f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 一、干系人登记册",
            "| 编号 | 角色 | 部门 | 关注点 | 影响力 | 参与度 | 沟通频率 |",
            "|------|------|------|--------|--------|--------|----------|",
        ]
        for s in stakeholders:
            md.append(f"| {s['id']} | {s['role']} | {s['dept']} | {s['concern']} | {s['influence']} | {s['interest']} | {s['comm_freq']} |")

        md.extend([
            "",
            "## 二、RACI 责任矩阵",
            "> R=负责(执行) A=审批(拍板) C=咨询(征求意见) I=知会(知晓即可)",
            "",
            "| 活动 | " + " | ".join(f"{s['role'][:4]}" for s in stakeholders[:8]) + " |",
            "|------|" + "|".join(["------"] * min(9, len(stakeholders[:8]) + 1)) + "|",
        ])
        for act in raci["activities"]:
            row = [act["name"]]
            for s in stakeholders[:8]:
                val = raci["assignments"].get(act["id"], {}).get(s["id"], "") or "-"
                row.append(val)
            md.append("| " + " | ".join(row) + " |")

        md.extend([
            "",
            "## 三、会议节奏",
        ])
        for m in comm_plan["meetings"]:
            md.append(f"### {m['name']}（{m['frequency']}，{m['duration']}）")
            md.append(f"- 参与人：{', '.join(m['participants'][:5])}")
            md.append(f"- 产出：{m['output']}")
            md.append("")

        md.extend([
            "## 四、报告体系",
            "| 报告 | 受众 | 核心内容 |",
            "|------|------|----------|",
        ])
        for r in comm_plan["reports"]:
            md.append(f"| {r['name']} | {r['audience']} | {r['content']} |")

        md.extend([
            "",
            "## 五、问题升级路径",
        ])
        for path in comm_plan["escalation_path"]:
            md.append(f"- {path}")

        return "\n".join(md)
