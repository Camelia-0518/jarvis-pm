"""功能分级注册表

将所有 API 端点按成熟度分为 4 级，帮助前端区分生产态和演示态功能：

    PRODUCTION  — 完整实现，真实数据流，经测试验证
    EXPERIMENTAL — 可用但有限制/回退/脆弱解析
    DEMO        — 主要返回 mock/硬编码数据
    STUB        — 占位符，不具功能性

用法:
    from app.core.feature_tiers import FEATURE_TIERS, FeatureTier

    tier = FEATURE_TIERS.get("/tools/competitors", FeatureTier.EXPERIMENTAL)
"""

import enum


class FeatureTier(str, enum.Enum):
    PRODUCTION = "production"
    EXPERIMENTAL = "experimental"
    DEMO = "demo"
    STUB = "stub"


# =============================================================================
# 端点分级注册表 — 按路由前缀组织
# =============================================================================

FEATURE_TIERS: dict[str, FeatureTier] = {
    # ── Auth ──
    "/auth/register": FeatureTier.PRODUCTION,
    "/auth/login": FeatureTier.PRODUCTION,
    "/auth/refresh": FeatureTier.PRODUCTION,
    "/auth/me": FeatureTier.PRODUCTION,
    "/auth/change-password": FeatureTier.PRODUCTION,

    # ── Projects ──
    "/projects": FeatureTier.PRODUCTION,
    "/projects/": FeatureTier.PRODUCTION,

    # ── PRDs ──
    "/prds": FeatureTier.PRODUCTION,
    "/prds/": FeatureTier.PRODUCTION,

    # ── Reviews ──
    "/projects/{project_id}/reviews/checklist": FeatureTier.PRODUCTION,
    "/projects/{project_id}/reviews/history": FeatureTier.PRODUCTION,

    # ── Annotations ──
    "/prds/{prd_id}/annotations": FeatureTier.PRODUCTION,

    # ── Revision Tasks ──
    "/prds/{prd_id}/revision-tasks": FeatureTier.PRODUCTION,

    # ── Tools — 生产态 ──
    "/tools/review-materials": FeatureTier.PRODUCTION,
    "/tools/review-materials-stream": FeatureTier.PRODUCTION,

    # ── Tools — 实验态（有回退/候选模式/硬编码字段） ──
    "/tools/competitors": FeatureTier.EXPERIMENTAL,
    "/tools/competitors/confirm": FeatureTier.EXPERIMENTAL,
    "/tools/stakeholders": FeatureTier.EXPERIMENTAL,

    # ── Tools — 演示态（主要返回硬编码/模板数据） ──
    "/tools/user-research": FeatureTier.DEMO,
    "/tools/data-analysis": FeatureTier.DEMO,
    "/tools/prototype": FeatureTier.DEMO,

    # ── Tools — 占位 ──
    "/tools/stats": FeatureTier.STUB,

    # ── Code ──
    "/code/generate-prototype": FeatureTier.PRODUCTION,
    "/code/generate-api": FeatureTier.PRODUCTION,
    "/code/generate-components": FeatureTier.PRODUCTION,
    "/code/generate-prototype-ai": FeatureTier.EXPERIMENTAL,
    "/code/export": FeatureTier.STUB,

    # ── Competitors / Personas / Requirements ──
    "/competitors": FeatureTier.PRODUCTION,
    "/personas": FeatureTier.PRODUCTION,
    "/requirements": FeatureTier.PRODUCTION,

    # ── Templates ──
    "/templates": FeatureTier.PRODUCTION,


    # ── Delivery ──
    "/delivery": FeatureTier.PRODUCTION,

    # ── AI ──
    "/ai/chat": FeatureTier.PRODUCTION,
    "/ai/generate-prd": FeatureTier.PRODUCTION,

    # ── RAG / Memory ──
    "/rag": FeatureTier.PRODUCTION,

    # ── Skills ──
    "/skills": FeatureTier.PRODUCTION,
    "/skills/categories": FeatureTier.DEMO,

    # ── Evaluation ──
    "/evaluation/templates/ab-tests": FeatureTier.DEMO,
    "/evaluation": FeatureTier.PRODUCTION,

    # ── Feedback ──
    "/feedback": FeatureTier.PRODUCTION,

    # ── WebSocket ──
    "/ws/collaboration": FeatureTier.EXPERIMENTAL,
}


def get_tier(path: str) -> FeatureTier:
    """根据请求路径返回功能分级。

    按最长前缀匹配，未注册的路径默认视为 PRODUCTION。
    """
    best_match = FeatureTier.PRODUCTION
    best_len = 0
    for prefix, tier in FEATURE_TIERS.items():
        # 去除路径参数占位符进行匹配
        clean_prefix = prefix.replace("{project_id}", "").replace("{prd_id}", "").rstrip("/")
        if path.startswith(clean_prefix) and len(clean_prefix) > best_len:
            best_match = tier
            best_len = len(clean_prefix)
    return best_match


def get_tier_summary() -> dict:
    """返回分级统计摘要。"""
    counts = {t.value: 0 for t in FeatureTier}
    for tier in FEATURE_TIERS.values():
        counts[tier.value] += 1
    total = sum(counts.values())
    return {
        "total_endpoints": total,
        "by_tier": counts,
        "production_pct": round(counts["production"] / total * 100, 1) if total else 0,
    }
