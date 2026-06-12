"""Delivery plan Pydantic schemas — validates AI agent output before database persistence.

Agent output is inherently unstable. These schemas sanitize rather than reject:
invalid fields are stripped, missing fields receive sensible defaults.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Atom structures (matches frontend TypeScript interfaces in api.ts)
# ---------------------------------------------------------------------------

class WbsTask(BaseModel):
    id: str = ""
    phase_id: str = ""
    phase_name: str = ""
    name: str = ""
    effort_days: float = 0.0
    dependencies: List[str] = Field(default_factory=list)
    role: str = ""
    priority: str = "medium"
    phase: str = ""

    model_config = {"extra": "ignore"}


class MilestonePhase(BaseModel):
    phase_id: str = ""
    name: str = ""
    start: str = ""
    end: str = ""
    duration_weeks: float = 0.0
    deliverables: List[str] = Field(default_factory=list)
    milestone: str = ""
    checkpoint: bool = False

    model_config = {"extra": "ignore"}


class GanttItem(BaseModel):
    id: str = ""
    name: str = ""
    phase: str = ""
    start_offset_days: float = 0.0
    duration_weeks: float = 0.0
    dependencies: List[str] = Field(default_factory=list)
    priority: str = "medium"
    role: str = ""
    phase_label: str = ""

    model_config = {"extra": "ignore"}


class RiskItem(BaseModel):
    id: str = ""
    category: str = ""
    risk: str = ""
    probability: float = 0.0
    impact: float = 0.0
    risk_score: float = 0.0
    risk_level: str = "低"
    prevention: str = ""
    contingency: str = ""
    trigger: str = ""
    owner: str = ""

    model_config = {"extra": "ignore"}


class StakeholderItem(BaseModel):
    id: str = ""
    role: str = ""
    dept: str = ""
    concern: str = ""
    influence: str = "中"
    interest: str = "中"
    comm_freq: str = "每两周"
    comm_channel: str = "邮件"

    model_config = {"extra": "ignore"}


class RaciActivity(BaseModel):
    id: str = ""
    name: str = ""
    phase: str = ""

    model_config = {"extra": "ignore"}


class RaciRole(BaseModel):
    id: str = ""
    name: str = ""
    dept: str = ""

    model_config = {"extra": "ignore"}


class RaciMatrix(BaseModel):
    activities: List[RaciActivity] = Field(default_factory=list)
    roles: List[RaciRole] = Field(default_factory=list)
    assignments: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    total_activities: int = 0
    total_roles: int = 0

    model_config = {"extra": "ignore"}


class MeetingItem(BaseModel):
    id: str = ""
    name: str = ""
    participants: List[str] = Field(default_factory=list)
    frequency: str = ""
    duration: str = ""
    format: str = ""
    output: str = ""
    agenda: List[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class ReportItem(BaseModel):
    name: str = ""
    audience: str = ""
    content: str = ""
    template: str = ""
    frequency: str = ""

    model_config = {"extra": "ignore"}


class CommunicationPlan(BaseModel):
    meetings: List[MeetingItem] = Field(default_factory=list)
    reports: List[ReportItem] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class StatusTemplateSection(BaseModel):
    name: str = ""
    fields: List[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


# ---------------------------------------------------------------------------
# Composite payload — validates the full plan_data dict before save
# ---------------------------------------------------------------------------

class DeliveryPlanPayload(BaseModel):
    """Validates the assembled plan_data before it hits the database.

    All fields are optional: when an agent produces garbage, we drop that
    section rather than polluting the DB with half-formed JSON.
    """

    wbs: Optional[Dict[str, Any]] = None
    milestones: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    gantt: Optional[Dict[str, Any]] = None
    risks: Optional[List[Dict[str, Any]]] = None
    risk_matrix: Optional[Dict[str, Any]] = None
    risk_response_plan: Optional[Dict[str, Any]] = None
    stakeholders: Optional[List[Dict[str, Any]]] = None
    raci: Optional[Dict[str, Any]] = None
    communication_plan: Optional[Dict[str, Any]] = None
    status_template: Optional[Dict[str, Any]] = None

    model_config = {"extra": "ignore"}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _try_validate_list(
    items: Any, model_cls: type[BaseModel], label: str
) -> tuple[List[dict], list[str]]:
    """Validate each item in a list, returning (sanitized list, warnings).

    Items that fail validation are dropped and recorded in warnings.
    An empty list is always returned when *items* is not a list.
    """
    if not isinstance(items, list):
        return [], [f"{label}: expected list, got {type(items).__name__}"]
    cleaned: List[dict] = []
    warnings: list[str] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            warnings.append(f"{label}[{i}]: dropped non-dict value ({type(item).__name__})")
            continue
        try:
            validated = model_cls(**item)
            cleaned.append(validated.model_dump())
        except Exception as exc:
            warnings.append(f"{label}[{i}]: validation failed — {exc}")
            continue
    return cleaned, warnings


def _try_validate_dict(
    data: Any, model_cls: type[BaseModel], label: str
) -> tuple[dict, list[str]]:
    """Validate a dict against a model, returning (sanitized dict, warnings)."""
    if not isinstance(data, dict):
        return {}, [f"{label}: expected dict, got {type(data).__name__}"]
    try:
        validated = model_cls(**data)
        return validated.model_dump(), []
    except Exception as exc:
        return {}, [f"{label}: validation failed — {exc}"]


def sanitize_delivery_payload(plan_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize agent-generated delivery data before database persistence.

    Returns a new dict with only valid fields.  Dropped or degraded
    sections are recorded in ``ai_generated.validation_warnings`` for
    debugging agent output quality.
    """
    all_warnings: list[str] = []

    # Top-level payload validation (drops unknown keys, keeps known ones)
    try:
        DeliveryPlanPayload(**plan_data)
    except Exception as exc:
        all_warnings.append(f"top-level payload: {exc}")

    def _validate_list_field(key: str, model_cls, label: str) -> None:
        cleaned, warnings = _try_validate_list(plan_data.get(key), model_cls, label)
        plan_data[key] = cleaned
        all_warnings.extend(warnings)

    def _validate_dict_field(key: str, model_cls, label: str) -> None:
        cleaned, warnings = _try_validate_dict(plan_data.get(key), model_cls, label)
        plan_data[key] = cleaned
        all_warnings.extend(warnings)

    def _validate_nested_list(parent_key: str, child_key: str, model_cls, label: str) -> None:
        parent = plan_data.get(parent_key)
        if isinstance(parent, dict):
            cleaned, warnings = _try_validate_list(parent.get(child_key), model_cls, label)
            parent[child_key] = cleaned
            all_warnings.extend(warnings)

    # Deep-validate list fields
    _validate_list_field("risks", RiskItem, "risks")
    _validate_list_field("stakeholders", StakeholderItem, "stakeholders")

    # Deep-validate dict fields
    _validate_dict_field("raci", RaciMatrix, "raci")
    _validate_dict_field("communication_plan", CommunicationPlan, "communication_plan")

    # Validate nested lists
    _validate_nested_list("wbs", "tasks", WbsTask, "wbs.tasks")
    _validate_nested_list("milestones", "phases", MilestonePhase, "milestones.phases")
    _validate_nested_list("gantt", "items", GanttItem, "gantt.items")
    _validate_nested_list("status_template", "sections", StatusTemplateSection, "status_template.sections")

    # Record warnings in ai_generated so they're persisted alongside the plan
    ai = plan_data.setdefault("ai_generated", {})
    existing = ai.get("validation_warnings", [])
    if isinstance(existing, list):
        all_warnings = list(existing) + all_warnings
    ai["validation_warnings"] = all_warnings

    return plan_data
