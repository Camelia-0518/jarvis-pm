#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理 Agent

自动识别项目风险，生成概率/影响矩阵 + 应对策略 + 预警机制
适配医疗信息化项目（HIS/EMR/互联互通）特殊风险场景
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
from typing import Dict, Any, List
from datetime import datetime

from ..base import BaseAgent, AgentResult, AgentState


class RiskManagerAgent(BaseAgent):
    """项目风险识别、评估与应对策略生成"""

    name = "risk_manager"
    description = "Identify, assess project risks and generate mitigation strategies with probability/impact matrix"
    version = "1.0.0"
    capabilities = [
        "risk_identification",
        "risk_assessment",
        "mitigation_planning",
        "early_warning",
    ]

    # 医疗信息化项目常见风险知识库
    MEDICAL_RISK_KB = [
        {"category": "需求风险", "risk": "临床科室需求频繁变更", "prob": 0.7, "impact": 0.8,
         "mitigation": "需求冻结期+变更控制委员会(CCB)审批流程；需求评审后签字确认"},
        {"category": "需求风险", "risk": "各科室业务流程差异大，难以统一建模", "prob": 0.8, "impact": 0.6,
         "mitigation": "分科室分批上线；抽象共性流程为平台能力，个性化做配置"},
        {"category": "技术风险", "risk": "与现有HIS/EMR系统接口不兼容", "prob": 0.6, "impact": 0.9,
         "mitigation": "提前获取接口文档；搭建联调沙箱环境；接口适配层设计"},
        {"category": "技术风险", "risk": "数据迁移中历史数据质量问题", "prob": 0.7, "impact": 0.8,
         "mitigation": "迁移前数据质量评估；制定数据清洗规则；分批迁移+回滚方案"},
        {"category": "技术风险", "risk": "系统性能不满足三甲医院并发要求", "prob": 0.5, "impact": 0.9,
         "mitigation": "提前进行性能测试；设计水平扩展方案；制定降级策略"},
        {"category": "合规风险", "risk": "等保三级测评不通过", "prob": 0.4, "impact": 0.95,
         "mitigation": "设计阶段引入安全评审；聘请等保测评机构提前预评；逐项整改跟踪"},
        {"category": "合规风险", "risk": "互联互通测评不符合标准", "prob": 0.4, "impact": 0.9,
         "mitigation": "对照测评标准逐项自查；数据集标准化前置；提前准备测评材料"},
        {"category": "合规风险", "risk": "患者隐私数据泄露", "prob": 0.3, "impact": 1.0,
         "mitigation": "数据脱敏+访问控制+审计日志；定期安全扫描；制定数据安全应急预案"},
        {"category": "干系人风险", "risk": "关键用户参与度不足", "prob": 0.6, "impact": 0.7,
         "mitigation": "明确用户参与机制（周会/月汇报）；委派专职业务代表；设用户反馈奖励"},
        {"category": "干系人风险", "risk": "院方领导层变更导致项目优先级调整", "prob": 0.4, "impact": 0.85,
         "mitigation": "多层级关系维护；项目价值定期汇报；合同条款保护"},
        {"category": "进度风险", "risk": "多方供应商协调困难导致延期", "prob": 0.7, "impact": 0.75,
         "mitigation": "制定接口联调计划明确各方责任；定期多方协调会议；合同中约定延期罚则"},
        {"category": "进度风险", "risk": "核心开发人员离职", "prob": 0.3, "impact": 0.8,
         "mitigation": "代码文档强制要求；关键模块双人备份；知识传承机制"},
        {"category": "资源风险", "risk": "硬件设备到货延迟", "prob": 0.4, "impact": 0.6,
         "mitigation": "提前下单并跟踪物流；准备备选供应商；使用云资源过渡"},
        {"category": "资源风险", "risk": "专家资源冲突（如DBA、安全专家）", "prob": 0.5, "impact": 0.5,
         "mitigation": "提前预约专家档期；培养内部备份能力；建立外部专家池"},
        {"category": "业务风险", "risk": "上线后业务中断影响诊疗", "prob": 0.2, "impact": 1.0,
         "mitigation": "灰度发布策略；完善回滚方案；选择非高峰时段上线；制定应急预案"},
        {"category": "业务风险", "risk": "用户抵触新系统影响使用率", "prob": 0.5, "impact": 0.7,
         "mitigation": "充分培训+考核；设置适应期双轨运行；快速响应早期反馈"},
    ]

    SYSTEM_PROMPT = """你是医疗信息化项目风险管理专家，专注于HIS/EMR/互联互通等项目的风险识别与应对。

输出要求：
1. 结合项目具体信息，识别定制化风险
2. 每个风险标注：类别、概率(0-1)、影响(0-1)、风险等级(=概率×影响)
3. 应对策略分三级：预防措施、应急方案、触发条件
4. 输出标准JSON格式

风险等级定义：
- 极高(>0.6)：需要立即制定专项应对方案，纳入日报跟踪
- 高(0.3-0.6)：需要制定应对措施，纳入周报跟踪
- 中(0.1-0.3)：列入风险清单，月度回顾
- 低(<0.1)：备案即可"""

    async def _do_execute(self, input_data: Dict[str, Any]) -> AgentResult:
        product_name = input_data.get("product_name", "未命名项目")
        description = input_data.get("description", "")
        prd_content = input_data.get("prd_content", "")
        industry = input_data.get("industry", "medical")
        project_phase = input_data.get("project_phase", "planning")
        team_info = input_data.get("team_info", {})

        step1 = self._create_step("load_knowledge", "加载医疗风险知识库")
        kb_risks = self.MEDICAL_RISK_KB.copy()
        self._complete_step(step1, f"加载{len(kb_risks)}条领域风险")

        step2 = self._create_step("identify_risks", "识别项目风险")
        all_risks = self._identify_risks(product_name, description, prd_content, kb_risks, industry)
        self._complete_step(step2, f"识别{len(all_risks)}个风险")

        step3 = self._create_step("assess_risks", "评估风险等级")
        assessed = self._assess_risks(all_risks, project_phase)
        self._complete_step(step3, f"极高{len([r for r in assessed if r['risk_level']=='极高'])}个，高{len([r for r in assessed if r['risk_level']=='高'])}个")

        step4 = self._create_step("build_matrix", "构建风险矩阵")
        matrix = self._build_risk_matrix(assessed)
        self._complete_step(step4, f"矩阵 {len(matrix['grid'])} 个网格")

        step5 = self._create_step("generate_plan", "生成应对计划")
        response_plan = self._generate_response_plan(assessed, project_phase)
        self._complete_step(step5, f"覆盖TOP {len(response_plan.get('top_risks', []))} 风险")


        return AgentResult(
            success=True,
            output=self._to_markdown(product_name, assessed, matrix, response_plan),
            data={
                "product_name": product_name,
                "risks": assessed,
                "matrix": matrix,
                "response_plan": response_plan,
                "industry": industry,
                "total_risks": len(assessed),
                "risk_score_avg": round(sum(r["risk_score"] for r in assessed) / max(len(assessed), 1), 2),
            },
            execution_time=self.elapsed_seconds,
            metadata={
                "agent_name": self.name,
                "version": self.version,
                "steps_completed": len(self.steps),
            }
        )

    def _identify_risks(self, product_name: str, description: str, prd_content: str,
                        kb_risks: List[Dict], industry: str) -> List[Dict]:
        all_text = (description + " " + (prd_content or "")[:2000]).lower()
        risks = []

        for kr in kb_risks:
            r = dict(kr)
            keyword_triggers = {
                "需求频繁变更": ["需求变更", "需求调整", "新需求"],
                "接口不兼容": ["接口", "集成", "对接", "互联互通"],
                "数据迁移": ["迁移", "历史数据", "数据导入"],
                "等保三级": ["等保", "安全", "合规"],
                "互联互通": ["互联互通", "测评", "标准化"],
                "患者隐私": ["隐私", "患者数据", "病历"],
                "关键用户": ["用户参与", "科室", "临床"],
                "供应商协调": ["供应商", "多方", "协调"],
                "核心人员离职": ["人员", "离职", "团队"],
                "设备到货": ["硬件", "服务器", "设备"],
                "业务中断": ["上线", "切换", "停机"],
                "用户抵触": ["培训", "适应", "使用率"],
            }
            for keyword, risk_key in keyword_triggers.items():
                if keyword in all_text and any(k in r["risk"] for k in risk_key):
                    r["prob"] = min(1.0, r["prob"] + 0.1)
                    r["impact"] = min(1.0, r["impact"] + 0.05)
            risks.append(r)

        risks.sort(key=lambda x: x["prob"] * x["impact"], reverse=True)
        return risks[:20]

    def _assess_risks(self, risks: List[Dict], phase: str) -> List[Dict]:
        phase_multipliers = {
            "planning": {"prob": 1.0, "impact": 0.8},
            "development": {"prob": 1.1, "impact": 1.0},
            "testing": {"prob": 0.9, "impact": 1.1},
            "deployment": {"prob": 0.8, "impact": 1.3},
            "operation": {"prob": 0.7, "impact": 1.0},
        }
        mult = phase_multipliers.get(phase, {"prob": 1.0, "impact": 1.0})

        result = []
        for r in risks:
            prob = round(min(1.0, r["prob"] * mult["prob"]), 2)
            impact = round(min(1.0, r["impact"] * mult["impact"]), 2)
            score = round(prob * impact, 2)
            if score > 0.6:
                level = "极高"
            elif score > 0.3:
                level = "高"
            elif score > 0.1:
                level = "中"
            else:
                level = "低"

            result.append({
                "id": f"RSK-{len(result)+1:03d}",
                "category": r["category"],
                "risk": r["risk"],
                "probability": prob,
                "impact": impact,
                "risk_score": score,
                "risk_level": level,
                "mitigation": r.get("mitigation", ""),
                "prevention": r.get("mitigation", "").split("；")[0] if r.get("mitigation") else "",
                "contingency": r.get("mitigation", "").split("；")[-1] if r.get("mitigation") and "；" in r["mitigation"] else "升级至项目指导委员会决策",
                "trigger": f"{r['risk']}发生概率显著上升或已出现苗头",
                "owner": self._assign_owner(r["category"]),
            })
        return result

    def _build_risk_matrix(self, risks: List[Dict]) -> Dict[str, Any]:
        grid = {}
        # Use simple labels matching frontend RiskMatrix key format ("低/低", "高/中" etc.)
        LEVEL_LABELS = [("低", (0, 0.3)), ("中", (0.3, 0.5)), ("高", (0.5, 1.0))]
        for p_label, p_range in LEVEL_LABELS:
            for i_label, i_range in LEVEL_LABELS:
                cell_key = f"{p_label}/{i_label}"
                cell_risks = [
                    r for r in risks
                    if p_range[0] <= r["probability"] < (p_range[1] if p_range[1] < 1 else 1.01)
                    and i_range[0] <= r["impact"] < (i_range[1] if i_range[1] < 1 else 1.01)
                ]
                grid[cell_key] = {"count": len(cell_risks), "risks": [r["id"] for r in cell_risks]}

        return {
            "grid": grid,
            "total_risks": len(risks),
            "summary": {
                "极高": len([r for r in risks if r["risk_level"] == "极高"]),
                "高": len([r for r in risks if r["risk_level"] == "高"]),
                "中": len([r for r in risks if r["risk_level"] == "中"]),
                "低": len([r for r in risks if r["risk_level"] == "低"]),
            }
        }

    def _generate_response_plan(self, risks: List[Dict], phase: str) -> Dict[str, Any]:
        top = sorted(risks, key=lambda x: x["risk_score"], reverse=True)[:5]
        return {
            "top_risks": [{
                "id": r["id"],
                "risk": r["risk"],
                "score": r["risk_score"],
                "level": r["risk_level"],
                "prevention": r["prevention"],
                "contingency": r["contingency"],
                "trigger": r["trigger"],
                "owner": r["owner"],
            } for r in top],
            "current_phase": phase,
            "review_cadence": "高风险以上每周回顾，极高每日跟踪",
        }

    def _assign_owner(self, category: str) -> str:
        mapping = {
            "需求风险": "产品经理",
            "技术风险": "技术负责人",
            "合规风险": "安全合规负责人",
            "干系人风险": "项目经理",
            "进度风险": "项目经理",
            "资源风险": "资源经理",
            "业务风险": "项目总监",
        }
        return mapping.get(category, "项目经理")

    def _to_markdown(self, product_name: str, risks: List[Dict], matrix: Dict[str, Any], plan: Dict[str, Any]) -> str:
        md = [
            f"# {product_name} 项目风险分析报告",
            f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> 风险总数：{len(risks)} | 平均风险值：{round(sum(r['risk_score'] for r in risks)/max(len(risks),1), 2)}",
            "",
            "## 一、风险矩阵概览",
        ]
        for level, count in matrix["summary"].items():
            bar = "█" * count
            md.append(f"- **{level}风险**：{count} 个 {bar}")

        md.extend([
            "",
            "## 二、TOP 5 重点风险",
            "| 编号 | 风险 | 等级 | 分值 | 预防措施 | 负责人 |",
            "|------|------|------|------|----------|--------|",
        ])
        for r in plan["top_risks"]:
            md.append(f"| {r['id']} | {r['risk']} | {r['level']} | {r['score']} | {r['prevention'][:50]}... | {r['owner']} |")

        md.extend([
            "",
            "## 三、完整风险清单",
            "| 编号 | 类别 | 风险描述 | 概率 | 影响 | 分值 | 等级 | 应对措施 |",
            "|------|------|----------|------|------|------|------|----------|",
        ])
        for r in risks:
            md.append(f"| {r['id']} | {r['category']} | {r['risk']} | {r['probability']} | {r['impact']} | {r['risk_score']} | **{r['risk_level']}** | {r['mitigation'][:60]}... |")

        return "\n".join(md)
