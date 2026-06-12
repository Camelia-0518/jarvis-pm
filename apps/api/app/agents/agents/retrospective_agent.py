#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复盘分析 Agent

从项目数据中自动提取经验教训，生成复盘报告和改进建议。
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
from typing import Dict, Any, List
from datetime import datetime

from ..base import BaseAgent, AgentResult, AgentState


class RetrospectiveAgent(BaseAgent):
    """AI-powered project retrospective analysis"""

    name = "retrospective_analyzer"
    description = "Analyze completed project data to extract lessons learned and improvement suggestions"
    version = "1.0.0"
    capabilities = [
        "retrospective_analysis",
        "lesson_extraction",
        "methodology_generation",
        "improvement_planning",
    ]

    SYSTEM_PROMPT = """你是一位资深项目复盘专家，拥有 10+ 年医疗信息化项目管理经验。

职责：
1. 分析项目数据（PRD、交付计划、风险记录），提取经验教训
2. 识别项目中做得好的模式和应避免的反模式
3. 生成具体的改进建议和行动项
4. 评估建议的可行性和影响程度

输出原则：
- 每一条教训必须有项目数据支撑
- 行动项必须具体可执行（含负责人建议和时限）
- 按影响程度排序（高→中→低）
- 区分"可固化为模板的模式"和"一次性教训"

输出格式：严格JSON。"""

    async def _do_execute(self, input_data: Dict[str, Any]) -> AgentResult:
        project_name = input_data.get("project_name", "未命名项目")
        prd_content = input_data.get("prd_content", "")
        delivery_data = input_data.get("delivery_data", {})
        what_went_well = input_data.get("what_went_well", "")
        what_went_wrong = input_data.get("what_went_wrong", "")
        surprises = input_data.get("surprises", "")

        step1 = self._create_step("analyze_patterns", "分析成功模式")
        patterns = self._extract_patterns(what_went_well, what_went_wrong)
        self._complete_step(step1, f"识别{len(patterns.get('good_patterns', []))}个成功模式")

        step2 = self._create_step("extract_lessons", "提取经验教训")
        lessons = self._extract_lessons(project_name, prd_content, delivery_data,
                                        what_went_well, what_went_wrong, surprises)
        self._complete_step(step2, f"提取{len(lessons)}条教训")

        step3 = self._create_step("generate_actions", "生成改进建议")
        actions = self._generate_action_items(lessons)
        self._complete_step(step3, f"生成{len(actions)}个行动项")

        step4 = self._create_step("summarize", "生成复盘摘要")
        summary = self._summarize(project_name, patterns, lessons, actions)
        self._complete_step(step4, "摘要生成完成")

        return AgentResult(
            success=True,
            output=summary,
            data={
                "project_name": project_name,
                "patterns": patterns,
                "lessons": lessons,
                "action_items": actions,
                "summary": summary,
            },
            execution_time=self.elapsed_seconds,
            metadata={
                "agent_name": self.name,
                "version": self.version,
            }
        )

    def _extract_patterns(self, what_went_well: str, what_went_wrong: str) -> Dict[str, Any]:
        good = []
        bad = []

        if what_went_well:
            for line in what_went_well.strip().split("\n"):
                line = line.strip().lstrip("- *•")
                if line and len(line) > 5:
                    good.append(line)

        if what_went_wrong:
            for line in what_went_wrong.strip().split("\n"):
                line = line.strip().lstrip("- *•")
                if line and len(line) > 5:
                    bad.append(line)

        return {
            "good_patterns": good,
            "anti_patterns": bad,
            "total": len(good) + len(bad),
        }

    def _extract_lessons(
        self,
        project_name: str,
        prd_content: str,
        delivery_data: Dict,
        what_went_well: str,
        what_went_wrong: str,
        surprises: str,
    ) -> List[Dict[str, Any]]:
        lessons = []
        lid = 1

        # Rule-based extraction from what went well
        if what_went_well:
            lessons.append({
                "id": f"L-{lid:03d}",
                "category": "success_pattern",
                "lesson": "项目中识别的成功实践",
                "detail": what_went_well[:200],
                "action_item": "固化为标准操作流程(SOP)",
                "impact": "高",
                "owner": "项目经理",
            })
            lid += 1

        # Rule-based extraction from what went wrong
        if what_went_wrong:
            lessons.append({
                "id": f"L-{lid:03d}",
                "category": "improvement_area",
                "lesson": "需要改进的领域",
                "detail": what_went_wrong[:200],
                "action_item": "在下一项目中制定预防措施",
                "impact": "高",
                "owner": "项目经理",
            })
            lid += 1

        # Extract from delivery data
        wbs = delivery_data.get("wbs", {})
        risks = delivery_data.get("risks", {})
        resources = delivery_data.get("resources", {})

        if wbs:
            total_tasks = wbs.get("total_tasks", 0)
            total_effort = wbs.get("total_effort_days", 0)
            if total_tasks > 20:
                lessons.append({
                    "id": f"L-{lid:03d}",
                    "category": "planning",
                    "lesson": f"大型项目({total_tasks}任务)需更细粒度里程碑",
                    "detail": f"共{total_tasks}个任务，{total_effort}人天，建议按阶段设置检查点",
                    "action_item": "将里程碑从阶段级细化到迭代级（每2周一个检查点）",
                    "impact": "中",
                    "owner": "交付经理",
                })
                lid += 1

        if risks:
            risk_list = risks if isinstance(risks, list) else risks.get("risks", risks.get("items", []))
            if isinstance(risk_list, list) and len(risk_list) > 0:
                high_risks = [r for r in risk_list if isinstance(r, dict) and r.get("risk_level") in ("极高", "高")]
                if high_risks:
                    lessons.append({
                        "id": f"L-{lid:03d}",
                        "category": "risk_management",
                        "lesson": f"高风险项({len(high_risks)}个)需专项跟踪",
                        "detail": f"TOP风险: {high_risks[0].get('risk', '未知')[:100]}",
                        "action_item": "建立高风险日报机制，每日跟踪应对进展",
                        "impact": "高",
                        "owner": "风险管理员",
                    })
                    lid += 1

        if resources:
            planned_days = resources.get("total_person_days", 0)
            actual_days = resources.get("actual_person_days", 0)
            if actual_days > planned_days * 1.3:
                lessons.append({
                    "id": f"L-{lid:03d}",
                    "category": "resource",
                    "lesson": "实际工作量超过计划30%+，需优化估算模型",
                    "detail": f"计划{planned_days}人天 → 实际{actual_days}人天",
                    "action_item": "将风险缓冲从20%提升至30%，并引入历史数据校准",
                    "impact": "中",
                    "owner": "资源经理",
                })
                lid += 1

        if surprises:
            lessons.append({
                "id": f"L-{lid:03d}",
                "category": "surprise",
                "lesson": "意料之外的情况",
                "detail": surprises[:200],
                "action_item": "纳入风险知识库，作为后续项目的标准检查项",
                "impact": "中",
                "owner": "项目经理",
            })
            lid += 1

        return lessons

    def _generate_action_items(self, lessons: List[Dict]) -> List[Dict[str, Any]]:
        actions = []
        for i, lesson in enumerate(lessons, 1):
            actions.append({
                "id": f"ACT-{i:03d}",
                "title": lesson.get("action_item", "未指定"),
                "source_lesson": lesson.get("id", ""),
                "owner": lesson.get("owner", "项目经理"),
                "impact": lesson.get("impact", "中"),
                "status": "pending",
                "deadline": "下一项目启动前",
            })
        return sorted(actions, key=lambda a: {"高": 0, "中": 1, "低": 2}.get(a["impact"], 1))

    def _summarize(self, project_name: str, patterns: Dict, lessons: List[Dict],
                   actions: List[Dict]) -> str:
        lines = [
            f"# {project_name} 项目复盘报告",
            f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 一、成功模式",
        ]
        for p in patterns.get("good_patterns", [])[:5]:
            lines.append(f"- {p}")

        lines.extend(["", "## 二、改进领域"])
        for p in patterns.get("anti_patterns", [])[:5]:
            lines.append(f"- {p}")

        lines.extend(["", "## 三、经验教训", "| 编号 | 类别 | 教训 | 影响 | 负责人 |", "|------|------|------|------|--------|"])
        for l in lessons:
            lines.append(f"| {l['id']} | {l['category']} | {l['lesson'][:40]} | {l['impact']} | {l['owner']} |")

        lines.extend(["", "## 四、改进行动项", "| 编号 | 行动 | 负责人 | 影响 | 截止时间 |", "|------|------|--------|------|----------|"])
        for a in actions[:10]:
            lines.append(f"| {a['id']} | {a['title'][:40]} | {a['owner']} | {a['impact']} | {a['deadline']} |")

        return "\n".join(lines)
