#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 评估框架

LLM-as-a-Judge 模式，自动评估 Agent 输出质量
支持回归测试、评分记录、历史对比
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from .llm_client import create_default_client


@dataclass
class EvaluationMetric:
    """评估指标"""
    name: str
    description: str
    weight: float = 1.0  # 权重（用于加权总分）
    max_score: float = 10.0


@dataclass
class EvaluationResult:
    """评估结果"""
    id: str
    agent_name: str
    task_type: str
    scores: Dict[str, float]  # 各维度评分
    total_score: float
    feedback: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "task_type": self.task_type,
            "scores": self.scores,
            "total_score": self.total_score,
            "feedback": self.feedback,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


# 预定义评估指标
PRD_METRICS = [
    EvaluationMetric(
        name="completeness",
        description="PRD 结构完整性（是否包含必要的章节：背景、用户故事、功能需求、非功能需求等）",
        weight=1.2,
        max_score=10.0,
    ),
    EvaluationMetric(
        name="clarity",
        description="表达清晰度（语言是否简洁明确，避免歧义）",
        weight=1.0,
        max_score=10.0,
    ),
    EvaluationMetric(
        name="actionability",
        description="可执行性（需求是否可验证、可测试，是否有明确的验收标准）",
        weight=1.2,
        max_score=10.0,
    ),
    EvaluationMetric(
        name="consistency",
        description="一致性（术语使用是否统一，前后逻辑是否自洽）",
        weight=0.8,
        max_score=10.0,
    ),
    EvaluationMetric(
        name="industry_awareness",
        description="行业感知（是否正确体现行业特性，如医疗合规、SaaS多租户等）",
        weight=1.0,
        max_score=10.0,
    ),
]

REQUIREMENT_METRICS = [
    EvaluationMetric(
        name="user_story_quality",
        description="用户故事质量（是否符合'作为...我想要...以便...'格式，是否可验收）",
        weight=1.2,
        max_score=10.0,
    ),
    EvaluationMetric(
        name="pain_point_accuracy",
        description="痛点识别准确性（是否准确把握了用户真实痛点）",
        weight=1.0,
        max_score=10.0,
    ),
    EvaluationMetric(
        name="feature_completeness",
        description="功能覆盖度（是否覆盖了核心功能和边界场景）",
        weight=1.0,
        max_score=10.0,
    ),
]


class LLMJudge:
    """
    LLM-as-a-Judge 评估器

    使用 LLM 对 Agent 输出进行多维度评分
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or create_default_client()
        self._history: List[EvaluationResult] = []

    async def evaluate(
        self,
        agent_name: str,
        task_type: str,
        output: str,
        reference: Optional[str] = None,
        metrics: Optional[List[EvaluationMetric]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        评估 Agent 输出质量

        Args:
            agent_name: Agent 名称
            task_type: 任务类型（prd / requirement / review 等）
            output: Agent 输出内容
            reference: 参考标准（可选，如人工编写的优质示例）
            metrics: 评估指标列表（可选，默认根据 task_type 选择）
            context: 额外上下文（如输入需求、行业类型等）

        Returns:
            EvaluationResult: 评估结果
        """
        if metrics is None:
            metrics = self._get_default_metrics(task_type)

        # 构建评估提示词
        prompt = self._build_evaluation_prompt(
            task_type=task_type,
            output=output,
            reference=reference,
            metrics=metrics,
            context=context,
        )

        # 调用 LLM 进行评估
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # 低温度确保评分稳定性
            max_tokens=2000,
        )

        # 解析评分结果
        scores, feedback = self._parse_evaluation_response(response, metrics)

        # 计算加权总分
        total_score = self._calculate_weighted_score(scores, metrics)

        result = EvaluationResult(
            id=str(uuid4()),
            agent_name=agent_name,
            task_type=task_type,
            scores=scores,
            total_score=total_score,
            feedback=feedback,
            timestamp=datetime.now(),
            metadata={
                "output_length": len(output),
                "reference_length": len(reference) if reference else 0,
                "context": context,
            },
        )

        self._history.append(result)
        return result

    def _get_default_metrics(self, task_type: str) -> List[EvaluationMetric]:
        """获取默认评估指标"""
        if task_type == "prd":
            return PRD_METRICS
        elif task_type == "requirement":
            return REQUIREMENT_METRICS
        else:
            return PRD_METRICS  # 默认使用 PRD 指标

    def _build_evaluation_prompt(
        self,
        task_type: str,
        output: str,
        reference: Optional[str],
        metrics: List[EvaluationMetric],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """构建评估提示词"""
        metrics_desc = "\n".join([
            f"{i+1}. {m.name}（权重{m.weight}，满分{m.max_score}）: {m.description}"
            for i, m in enumerate(metrics)
        ])

        reference_section = ""
        if reference:
            reference_section = f"\n### 参考标准（人工优质示例）\n{reference[:2000]}\n"

        context_section = ""
        if context:
            context_section = f"\n### 上下文信息\n{json.dumps(context, ensure_ascii=False, indent=2)}\n"

        return f"""你是一位资深产品经理评审专家。请对以下 AI 生成的{task_type}文档进行专业评估。

### 评估维度
{metrics_desc}

### AI 生成内容
{output[:3000]}
{reference_section}
{context_section}

请按以下格式输出评估结果：

```json
{{
  "scores": {{
{chr(10).join([f'    "{m.name}": <0-{int(m.max_score)}之间的数字>,' for m in metrics])}
  }},
  "feedback": "总体评价和改进建议（200字以内）"
}}
```

要求：
1. 评分客观公正，不要全部给满分
2. 如果内容有明显缺陷，请明确指出
3. feedback 要具体、可操作
"""

    def _parse_evaluation_response(
        self,
        response: str,
        metrics: List[EvaluationMetric],
    ) -> tuple[Dict[str, float], str]:
        """解析评估响应"""
        scores: Dict[str, float] = {}
        feedback = ""

        # 尝试提取 JSON
        try:
            # 查找 ```json 块
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                # 尝试直接解析整个响应
                json_str = response.strip()

            data = json.loads(json_str)
            raw_scores = data.get("scores", {})
            feedback = data.get("feedback", "")

            for metric in metrics:
                score = raw_scores.get(metric.name, 0.0)
                # 限制在有效范围内
                score = max(0.0, min(float(score), metric.max_score))
                scores[metric.name] = round(score, 1)

        except Exception:
            # 解析失败，使用默认值
            for metric in metrics:
                scores[metric.name] = 5.0
            feedback = "评估解析失败，请检查输出格式。"

        return scores, feedback

    def _calculate_weighted_score(
        self,
        scores: Dict[str, float],
        metrics: List[EvaluationMetric],
    ) -> float:
        """计算加权总分"""
        total_weight = 0.0
        weighted_sum = 0.0

        for metric in metrics:
            score = scores.get(metric.name, 0.0)
            normalized_score = score / metric.max_score * 10  # 归一化到 10 分制
            weighted_sum += normalized_score * metric.weight
            total_weight += metric.weight

        if total_weight == 0:
            return 0.0

        return round(weighted_sum / total_weight, 1)

    def get_history(self, agent_name: Optional[str] = None, task_type: Optional[str] = None) -> List[EvaluationResult]:
        """获取评估历史"""
        results = self._history
        if agent_name:
            results = [r for r in results if r.agent_name == agent_name]
        if task_type:
            results = [r for r in results if r.task_type == task_type]
        return results

    def get_average_score(self, agent_name: Optional[str] = None, task_type: Optional[str] = None) -> float:
        """获取平均评分"""
        results = self.get_history(agent_name, task_type)
        if not results:
            return 0.0
        return round(sum(r.total_score for r in results) / len(results), 1)

    def compare_with_history(self, result: EvaluationResult, last_n: int = 5) -> Dict[str, Any]:
        """
        与历史评估对比

        Args:
            result: 当前评估结果
            last_n: 对比最近 N 次

        Returns:
            对比分析
        """
        history = self.get_history(result.agent_name, result.task_type)
        if len(history) <= 1:
            return {"trend": "insufficient_data", "comparison": None}

        recent = history[-last_n:-1]  # 不包括当前这次
        avg_total = sum(r.total_score for r in recent) / len(recent)

        # 计算各维度平均分
        metric_avgs: Dict[str, float] = {}
        for metric_name in result.scores.keys():
            scores = [r.scores.get(metric_name, 0.0) for r in recent if metric_name in r.scores]
            if scores:
                metric_avgs[metric_name] = round(sum(scores) / len(scores), 1)

        return {
            "trend": "improved" if result.total_score > avg_total else "declined" if result.total_score < avg_total else "stable",
            "current_score": result.total_score,
            "historical_average": round(avg_total, 1),
            "difference": round(result.total_score - avg_total, 1),
            "metric_comparison": {
                name: {
                    "current": result.scores.get(name, 0.0),
                    "average": metric_avgs.get(name, 0.0),
                }
                for name in result.scores.keys()
            },
        }

    def save_to_file(self, filepath: str):
        """保存评估历史到文件"""
        data = [r.to_dict() for r in self._history]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath: str):
        """从文件加载评估历史"""
        if not os.path.exists(filepath):
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._history = []
        for item in data:
            result = EvaluationResult(
                id=item.get("id", str(uuid4())),
                agent_name=item["agent_name"],
                task_type=item["task_type"],
                scores=item["scores"],
                total_score=item["total_score"],
                feedback=item["feedback"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                metadata=item.get("metadata", {}),
            )
            self._history.append(result)


class RegressionTester:
    """
    回归测试器

    对 Agent 进行批量回归测试，检测质量退化
    """

    def __init__(self, evaluator: LLMJudge):
        self.evaluator = evaluator

    async def run_regression_test(
        self,
        test_cases: List[Dict[str, Any]],
        score_threshold: float = 6.0,
    ) -> Dict[str, Any]:
        """
        运行回归测试

        Args:
            test_cases: 测试用例列表，每个用例包含：
                - agent_name: Agent 名称
                - task_type: 任务类型
                - output: Agent 输出
                - reference: 参考标准（可选）
                - context: 上下文（可选）
            score_threshold: 及格分数线

        Returns:
            测试结果汇总
        """
        results = []
        passed = 0
        failed = 0

        for case in test_cases:
            result = await self.evaluator.evaluate(
                agent_name=case["agent_name"],
                task_type=case["task_type"],
                output=case["output"],
                reference=case.get("reference"),
                context=case.get("context"),
            )

            results.append(result.to_dict())
            if result.total_score >= score_threshold:
                passed += 1
            else:
                failed += 1

        total = len(test_cases)
        pass_rate = passed / total if total > 0 else 0.0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate * 100, 1),
            "threshold": score_threshold,
            "average_score": self.evaluator.get_average_score(),
            "results": results,
        }