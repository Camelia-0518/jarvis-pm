#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intent Classifier Agent
"""

import logging
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import re
from typing import Dict, Any, Optional
from datetime import datetime

from ..base import BaseAgent, AgentResult, AgentState

logger = logging.getLogger(__name__)


class IntentClassifier(BaseAgent):
    """Intent classification agent"""

    name = "intent_classifier"
    description = "Analyze user input and identify intent"
    version = "1.0.0"
    capabilities = ["intent_classification", "entity_extraction"]

    TASK_TYPES = {
        "requirement_analysis": {
            "keywords": ["需求", "分析", "调研"],
            "next_agents": ["requirement_analyzer"]
        },
        "competitor_analysis": {
            "keywords": ["竞品", "对标", "对比"],
            "next_agents": ["competitor_analyst"]
        },
        "prd_generation": {
            "keywords": ["PRD", "文档"],
            "next_agents": ["prd_generator"]
        },
        "compliance_check": {
            "keywords": ["合规", "检查"],
            "next_agents": ["compliance_checker"]
        },
        "review_preparation": {
            "keywords": ["评审", "准备"],
            "next_agents": ["review_preparer"]
        },
        "full_workflow": {
            "keywords": ["全流程", "完整"],
            "next_agents": ["requirement_analyzer", "competitor_analyst", "prd_generator"]
        }
    }

    SYSTEM_PROMPT = """You are an intent classification expert."""

    async def _do_execute(self, input_data: Dict[str, Any]) -> AgentResult:
        user_input = input_data.get("user_input", "")
        if not user_input:
            raise ValueError("user_input is required")

        step1 = self._create_step("rule_match", "Rule matching")
        rule_result = self._rule_based_classify(user_input)
        self._complete_step(step1, f"Rule match: {rule_result['task_type']}")

        step2 = self._create_step("llm_analysis", "LLM analysis")
        llm_result = await self._llm_classify(user_input)
        self._complete_step(step2, f"LLM confidence: {llm_result.get('confidence', 0)}")

        step3 = self._create_step("merge", "Merge results")
        final_result = self._merge_results(rule_result, llm_result)
        self._complete_step(step3, f"Final type: {final_result['task_type']}")


        return AgentResult(
            success=True,
            output=f"Intent: {final_result['task_type']} (confidence: {final_result['confidence']:.2f})",
            data=final_result,
            execution_time=self.elapsed_seconds
        )

    def _rule_based_classify(self, user_input: str) -> Dict[str, Any]:
        user_input_lower = user_input.lower()
        best_match = None
        max_score = 0

        for task_type, config in self.TASK_TYPES.items():
            score = sum(1 for kw in config["keywords"] if kw in user_input_lower)
            if score > max_score:
                max_score = score
                best_match = {
                    "task_type": task_type,
                    "confidence": min(score / len(config["keywords"]) * 0.8 + 0.2, 0.9),
                    "suggested_agents": config["next_agents"]
                }

        return best_match or {
            "task_type": "unknown",
            "confidence": 0.0,
            "suggested_agents": ["requirement_analyzer"]
        }

    async def _llm_classify(self, user_input: str) -> Dict[str, Any]:
        prompt = f"Analyze user input and classify intent: {user_input}"
        try:
            response = await self._call_llm(prompt=prompt, system_prompt=self.SYSTEM_PROMPT)
            return json.loads(response)
        except Exception:
            logger.warning("LLM intent classification failed, falling back to unknown", exc_info=True)
            return {"task_type": "unknown", "confidence": 0.5, "entities": {}}

    def _merge_results(self, rule_result: Dict, llm_result: Dict) -> Dict[str, Any]:
        if llm_result.get("confidence", 0) > 0.8:
            return {**llm_result, "method": "llm"}
        if rule_result["confidence"] > 0.7:
            return {**rule_result, "method": "rule"}
        return {
            "task_type": llm_result.get("task_type", rule_result["task_type"]),
            "confidence": (llm_result.get("confidence", 0) + rule_result["confidence"]) / 2,
            "method": "hybrid"
        }

    def extract_product_name(self, user_input: str) -> Optional[str]:
        patterns = [r'["""\'](.+?)["""\']', r'(.+?)(?:平台|系统)']
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                return match.group(1).strip()
        return None