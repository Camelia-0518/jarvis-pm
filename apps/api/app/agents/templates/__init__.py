#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能模板系统

自动检测行业类型并应用专用模板
"""

# Import from parent templates.py module
import sys
from pathlib import Path

# Add parent directory to path for direct import
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Now import from the templates.py in parent directory
import importlib.util
spec = importlib.util.spec_from_file_location("templates_module", parent_dir / "templates.py")
templates_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(templates_module)

# Export all public classes
TemplateSystem = templates_module.TemplateSystem
IndustryTemplate = templates_module.IndustryTemplate
ComplianceRequirement = templates_module.ComplianceRequirement
IndustryType = templates_module.IndustryType
get_template_system = templates_module.get_template_system

__all__ = [
    "TemplateSystem",
    "IndustryTemplate",
    "ComplianceRequirement",
    "IndustryType",
    "get_template_system"
]
