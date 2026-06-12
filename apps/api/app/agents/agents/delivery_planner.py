#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交付计划生成 Agent

从 PRD 自动生成 WBS、里程碑计划、资源估算、甘特图数据
适用于 HIS/EMR/互联互通等医疗数字化项目
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseAgent, AgentResult, AgentState


class DeliveryPlannerAgent(BaseAgent):
    """从需求文档自动生成项目交付计划"""

    name = "delivery_planner"
    description = "Generate project delivery plans with WBS, milestones, resource estimation, and Gantt data"
    version = "1.0.0"
    capabilities = [
        "delivery_planning",
        "wbs_generation",
        "milestone_planning",
        "resource_estimation",
        "gantt_generation",
    ]

    SYSTEM_PROMPT = """你是一位资深医疗信息化项目交付经理，拥有10+年HIS/EMR/互联互通项目交付经验。

职责：
1. 将产品需求转化为可执行的 WBS（工作分解结构）
2. 制定里程碑计划，包含关键节点和交付物
3. 估算资源需求（人力、时间、预算）
4. 识别阶段依赖关系和关键路径
5. 输出甘特图结构数据

输出原则：
- 所有估算必须有依据，不能凭空编造
- 医疗项目特殊阶段必须标注（如：等保测评、互联互通测评、医保接口联调）
- 风险缓冲按20%计算
- 明确标注一期/二期范围

输出格式：严格JSON，不要任何额外文字。"""

    async def _do_execute(self, input_data: Dict[str, Any]) -> AgentResult:
        product_name = input_data.get("product_name", "未命名项目")
        description = input_data.get("description", "")
        prd_content = input_data.get("prd_content", "")
        industry = input_data.get("industry", "medical")
        team_size = input_data.get("team_size") or 5
        start_date = input_data.get("start_date") or datetime.now().strftime("%Y-%m-%d")

        step1 = self._create_step("parse_requirements", "解析需求范围")
        scope = self._parse_scope(prd_content, description, product_name)
        self._complete_step(step1, f"识别{len(scope.get('modules', []))}个功能模块")

        step2 = self._create_step("generate_wbs", "生成WBS分解")
        wbs = self._generate_wbs(product_name, description, scope, industry)
        self._complete_step(step2, f"WBS {len(wbs.get('tasks', []))}个任务")

        step3 = self._create_step("generate_milestones", "生成里程碑计划")
        milestones = self._generate_milestones(product_name, wbs, industry, start_date)
        self._complete_step(step3, f"里程碑 {len(milestones.get('phases', []))}个阶段")

        step4 = self._create_step("estimate_resources", "估算资源需求")
        resources = self._estimate_resources(wbs, milestones, team_size)
        self._complete_step(step4, f"预估{resources.get('total_person_days', 0)}人天")

        step5 = self._create_step("build_gantt", "构建甘特图数据")
        gantt = self._build_gantt_data(wbs, milestones, start_date)
        self._complete_step(step5, f"甘特图 {len(gantt.get('items', []))}条任务条")

        return AgentResult(
            success=True,
            output=self._to_markdown(product_name, wbs, milestones, resources),
            data={
                "product_name": product_name,
                "wbs": wbs,
                "milestones": milestones,
                "resources": resources,
                "gantt": gantt,
                "industry": industry,
                "start_date": start_date,
            },
            execution_time=self.elapsed_seconds,
            metadata={
                "agent_name": self.name,
                "version": self.version,
                "steps_completed": len(self.steps),
            }
        )

    def _parse_scope(self, prd_content: str, description: str, product_name: str) -> Dict[str, Any]:
        scope_text = (prd_content or "") + "\n" + description
        modules = []
        for m in re.finditer(r'(?:模块|系统|平台)[：:]\s*(.+?)(?:\n|$)', scope_text):
            modules.append(m.group(1).strip())
        if not modules:
            modules = ["核心业务模块", "管理后台", "接口集成", "数据迁移", "培训与上线"]
        phases = {"一期": [], "二期": []}
        for line in scope_text.split("\n"):
            if "一期" in line:
                phases["一期"].append(line.strip())
            if "二期" in line:
                phases["二期"].append(line.strip())
        return {"modules": modules, "phases": phases, "product_name": product_name}

    def _generate_wbs(self, product_name: str, description: str, scope: Dict[str, Any], industry: str) -> Dict[str, Any]:
        tasks = []
        tid = 1

        phase_definitions = [
            ("1", "项目启动", [
                "项目章程编写与审批",
                "组建项目团队并明确角色职责",
                "召开项目启动会（kick-off）",
                "确定沟通机制与周报模板",
            ]),
            ("2", "需求分析", [
                "业务需求调研与访谈（临床/管理/运维）",
                "需求规格说明书(SRS)编写",
                "需求评审与签字确认",
                "UI/UX原型设计与评审",
            ]),
            ("3", "系统设计", [
                "系统架构设计（含灾备方案）",
                "数据库设计与评审",
                "接口规范定义（HL7/FHIR/WebService）",
                "安全方案设计（等保三级要求）",
            ]),
            ("4", "开发实施", [
                "迭代1：核心功能开发",
                "迭代2：扩展功能开发",
                "迭代3：集成与联调",
                "代码评审与单元测试",
                "接口联调（HIS/EMR/LIS/PACS）",
            ]),
            ("5", "测试验证", [
                "功能测试（SIT）",
                "集成测试",
                "性能与压力测试",
                "用户验收测试（UAT）",
                "等保测评与安全测试",
            ]),
            ("6", "部署上线", [
                "生产环境部署",
                "数据迁移与校验",
                "灰度发布与回滚预案",
                "正式上线切换",
                "上线后48小时值守",
            ]),
            ("7", "培训与交接", [
                "管理员培训",
                "操作员培训",
                "培训考核与发证",
                "运维文档移交",
                "项目验收与签收",
            ]),
            ("8", "运维保障", [
                "上线后1个月陪跑",
                "问题跟踪与修复",
                "月度运维报告",
                "知识库沉淀",
            ]),
        ]

        if industry == "medical":
            phase_definitions.insert(5, ("5A", "互联互通测评", [
                "互联互通标准化成熟度测评准备",
                "数据集标准化（CDA/HL7）",
                "共享文档生成与验证",
                "测评申报材料准备",
                "现场查验配合",
            ]))
            phase_definitions.insert(6, ("5B", "医保对接", [
                "医保接口开发（国家医保平台）",
                "医保目录对照",
                "医保结算联调",
                "医保基金监管接口",
            ]))

        for phase_id, phase_name, phase_tasks in phase_definitions:
            for i, task_name in enumerate(phase_tasks, 1):
                task_id = f"WBS-{tid:03d}"
                effort_days = max(2, min(15, len(task_name) * 2 + (3 if '联调' in task_name or '测试' in task_name else 0)))
                tasks.append({
                    "id": task_id,
                    "phase_id": phase_id,
                    "phase_name": phase_name,
                    "name": task_name,
                    "effort_days": effort_days,
                    "dependencies": [tasks[-1]["id"]] if tasks and i == 1 and tid > 1 else [],
                    "role": self._assign_role(task_name),
                    "priority": "P0" if any(k in task_name for k in ["上线", "迁移", "测评", "验收"]) else "P1",
                    "phase": "一期" if phase_id in ("1", "2", "3", "4", "5") else "二期",
                })
                tid += 1

        total_effort = sum(t["effort_days"] for t in tasks)
        return {"tasks": tasks, "total_tasks": len(tasks), "total_effort_days": total_effort}

    def _generate_milestones(self, product_name: str, wbs: Dict[str, Any], industry: str, start_date: str) -> Dict[str, Any]:
        from datetime import datetime as dt, timedelta
        try:
            base = dt.strptime(start_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            base = dt.now()
        weeks = 0

        phases = []
        current_day = 0
        for phase_id, phase_name in [
            ("1", "项目启动"), ("2", "需求分析"), ("3", "系统设计"),
            ("4", "开发实施"), ("5A", "互联互通测评"), ("5", "测试验证"),
            ("5B", "医保对接"), ("6", "部署上线"), ("7", "培训与交接"), ("8", "运维保障"),
        ]:
            phase_tasks = [t for t in wbs["tasks"] if t["phase_id"] == phase_id]
            if not phase_tasks:
                continue
            phase_days = sum(t["effort_days"] for t in phase_tasks)
            phase_weeks = max(1, round(phase_days / 5))
            start_d = base + timedelta(days=current_day)
            end_d = start_d + timedelta(weeks=phase_weeks) - timedelta(days=1)
            deliverables = [t["name"] for t in phase_tasks[:3]]
            phases.append({
                "phase_id": phase_id,
                "name": phase_name,
                "start": start_d.strftime("%Y-%m-%d"),
                "end": end_d.strftime("%Y-%m-%d"),
                "duration_weeks": phase_weeks,
                "deliverables": deliverables,
                "milestone": f"{phase_name}完成" if phase_id not in ("5A", "5B") else f"{phase_name}通过",
                "checkpoint": phase_name in ("需求分析", "系统设计", "测试验证", "部署上线"),
            })
            current_day += phase_weeks * 7

        return {
            "phases": phases,
            "total_weeks": current_day // 7,
            "start_date": start_date,
            "end_date": (base + timedelta(days=current_day)).strftime("%Y-%m-%d"),
        }

    def _estimate_resources(self, wbs: Dict[str, Any], milestones: Dict[str, Any], team_size: int) -> Dict[str, Any]:
        total_effort = wbs.get("total_effort_days", 0)
        buffer = int(total_effort * 0.2)
        total_with_buffer = total_effort + buffer

        roles_needed = {}
        for task in wbs["tasks"]:
            role = task.get("role", "开发工程师")
            roles_needed[role] = roles_needed.get(role, 0) + 1

        return {
            "total_person_days": total_effort,
            "buffer_person_days": buffer,
            "total_with_buffer": total_with_buffer,
            "team_size": team_size,
            "estimated_calendar_days": max(1, total_with_buffer // team_size),
            "roles": [{"role": r, "count": max(1, c // 3)} for r, c in roles_needed.items()],
            "recommendation": f"建议团队规模 {team_size} 人，含风险缓冲 {buffer} 人天（20%），预计 {max(1, total_with_buffer // team_size)} 个工作日",
        }

    def _build_gantt_data(self, wbs: Dict[str, Any], milestones: Dict[str, Any], start_date: str) -> Dict[str, Any]:
        from datetime import datetime as dt, timedelta
        try:
            base = dt.strptime(start_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            base = dt.now()
        items = []
        current_offset = 0

        for task in wbs["tasks"]:
            duration = max(1, task["effort_days"] // 5) or 1
            items.append({
                "id": task["id"],
                "name": task["name"],
                "phase": task["phase_name"],
                "start_offset_days": current_offset,
                "duration_weeks": duration,
                "dependencies": task.get("dependencies", []),
                "priority": task.get("priority", "P1"),
                "role": task.get("role", ""),
                "phase_label": task.get("phase", ""),
            })
            current_offset += duration * 7

        return {"items": items, "total_days": current_offset, "start_date": start_date}

    def _assign_role(self, task_name: str) -> str:
        if any(k in task_name for k in ["架构", "设计", "方案"]):
            return "架构师"
        if any(k in task_name for k in ["前端", "UI", "原型", "界面"]):
            return "前端工程师"
        if any(k in task_name for k in ["后端", "接口", "数据库", "服务"]):
            return "后端工程师"
        if any(k in task_name for k in ["测试", "验收", "UAT", "SIT"]):
            return "测试工程师"
        if any(k in task_name for k in ["部署", "运维", "上线", "环境"]):
            return "运维工程师"
        if any(k in task_name for k in ["培训", "文档", "知识"]):
            return "培训师"
        if any(k in task_name for k in ["管理", "沟通", "章程", "启动"]):
            return "项目经理"
        return "开发工程师"

    def _to_markdown(self, product_name: str, wbs: Dict[str, Any], milestones: Dict[str, Any], resources: Dict[str, Any]) -> str:
        md = [
            f"# {product_name} 项目交付计划",
            "",
            f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 一、项目概览",
            f"- 总任务数：{wbs['total_tasks']}",
            f"- 总工作量：{resources['total_person_days']} 人天（含20%风险缓冲：{resources['total_with_buffer']} 人天）",
            f"- 建议团队：{resources['team_size']} 人",
            f"- 预计周期：{milestones['total_weeks']} 周",
            f"- 计划起止：{milestones['start_date']} ~ {milestones['end_date']}",
            "",
            "## 二、里程碑计划",
        ]
        for p in milestones["phases"]:
            checkpoint = " [评审点]" if p.get("checkpoint") else ""
            md.append(f"- **{p['name']}** ({p['start']} ~ {p['end']}, {p['duration_weeks']}周){checkpoint}")
            md.append(f"  - 里程碑：{p['milestone']}")
            md.append(f"  - 交付物：{'、'.join(p['deliverables'][:3])}")

        md.extend([
            "",
            "## 三、WBS 工作分解",
            "| 编号 | 任务 | 阶段 | 工期(天) | 角色 | 优先级 |",
            "|------|------|------|----------|------|--------|",
        ])
        for t in wbs["tasks"]:
            md.append(f"| {t['id']} | {t['name']} | {t['phase_name']} | {t['effort_days']} | {t['role']} | {t['priority']} |")

        md.extend([
            "",
            "## 四、资源需求",
            f"### 人力配置",
        ])
        for r in resources["roles"]:
            md.append(f"- {r['role']}：{r['count']}人")
        md.append(f"\n### 风险缓冲\n{resources['recommendation']}")

        return "\n".join(md)
